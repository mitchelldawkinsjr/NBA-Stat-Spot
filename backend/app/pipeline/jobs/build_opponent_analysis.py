"""Precompute opponent analysis for slate players into player_opponent_analysis."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import or_
from sqlalchemy.orm import Session

from ...models.games import Game
from ...models.player_game_log_cache import PlayerGameLogCache
from ...models.player_game_stats import PlayerGameStat
from ...models.player_opponent_analysis import PlayerOpponentAnalysis
from ...models.players import Player
from ...models.teams import Team
from ...services.analytics_constants import FORMULA_VERSION
from ...services.best_picks_service import _normalize_position
from ...services.box_score_validator import BoxScoreValidator
from ...services.context_collector import ContextCollector
from ...utils.season import get_current_season
from ..context import PipelineContext


def _team_abbr_map(db: Session) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for t in db.query(Team).all():
        if t.abbreviation and t.id is not None:
            out[str(t.abbreviation).upper()] = int(t.id)
    return out


def _team_id_to_abbr(db: Session) -> Dict[int, str]:
    out: Dict[int, str] = {}
    for t in db.query(Team).all():
        if t.id is not None and t.abbreviation:
            out[int(t.id)] = str(t.abbreviation).upper()
    return out


def _h2h_from_logs(
    logs: List[Dict[str, Any]],
    opponent_abbr: Optional[str],
    limit: int = 10,
) -> Dict[str, Any]:
    if not logs or not opponent_abbr:
        return {
            "h2h_avg_pts": None,
            "h2h_avg_reb": None,
            "h2h_avg_ast": None,
            "h2h_games_played": 0,
        }
    abbr = opponent_abbr.lower()
    matchup_games: List[Dict[str, Any]] = []
    for g in logs:
        matchup = (g.get("matchup") or "").lower()
        if abbr and abbr in matchup:
            matchup_games.append(g)
            if len(matchup_games) >= limit:
                break
    if not matchup_games:
        return {
            "h2h_avg_pts": None,
            "h2h_avg_reb": None,
            "h2h_avg_ast": None,
            "h2h_games_played": 0,
        }
    pts = [float(g.get("pts", 0) or 0) for g in matchup_games]
    reb = [float(g.get("reb", 0) or 0) for g in matchup_games]
    ast = [float(g.get("ast", 0) or 0) for g in matchup_games]
    n = len(matchup_games)
    return {
        "h2h_avg_pts": sum(pts) / n if pts else None,
        "h2h_avg_reb": sum(reb) / n if reb else None,
        "h2h_avg_ast": sum(ast) / n if ast else None,
        "h2h_games_played": n,
    }


def _rest_from_logs(logs: List[Dict[str, Any]], game_date: date) -> Optional[int]:
    prior = [
        str(g.get("game_date") or "")[:10]
        for g in logs
        if g.get("game_date") and str(g.get("game_date"))[:10] < game_date.isoformat()
    ]
    if not prior:
        return None
    last = datetime.strptime(max(prior), "%Y-%m-%d").date()
    return max(0, (game_date - last).days - 1)


def _logs_by_player(db: Session, player_ids: List[int], season: str) -> Dict[int, List[Dict[str, Any]]]:
    """Game logs from the pipeline cache (matchup + shooting). No external API."""
    if not player_ids:
        return {}
    grouped: Dict[int, List[Dict[str, Any]]] = {}
    rows = (
        db.query(PlayerGameLogCache)
        .filter(
            PlayerGameLogCache.player_id.in_(player_ids),
            PlayerGameLogCache.season == season,
        )
        .all()
    )
    for row in rows:
        grouped.setdefault(int(row.player_id), []).append(row.to_dict())
    for logs in grouped.values():
        logs.sort(key=lambda g: str(g.get("game_date") or ""), reverse=True)
    return grouped


def _season_avgs(logs: List[Dict[str, Any]]) -> Dict[str, float]:
    if not logs:
        return {}
    n = len(logs)
    return {
        "pts": sum(float(g.get("pts", 0) or 0) for g in logs) / n,
        "reb": sum(float(g.get("reb", 0) or 0) for g in logs) / n,
        "ast": sum(float(g.get("ast", 0) or 0) for g in logs) / n,
        "3pm": sum(float(g.get("tpm", 0) or 0) for g in logs) / n,
    }


def _slate_pairs(
    db: Session,
    *,
    slate_date: date,
    season: str,
    abbr_to_id: Dict[str, int],
) -> List[Tuple[int, int, bool, date]]:
    """Return (player_id, opponent_team_id, is_home, game_date) for slate + recent fallback."""
    pairs: List[Tuple[int, int, bool, date]] = []
    seen: Set[Tuple[int, int]] = set()

    games = db.query(Game).filter(Game.game_date == slate_date, Game.season == season).all()
    for g in games:
        home_id = abbr_to_id.get((g.home_team_abbr or "").upper())
        away_id = abbr_to_id.get((g.away_team_abbr or "").upper())
        if not home_id or not away_id:
            continue
        home_players = (
            db.query(Player.id)
            .filter(Player.team_id == home_id, Player.is_active.is_(True))
            .all()
        )
        away_players = (
            db.query(Player.id)
            .filter(Player.team_id == away_id, Player.is_active.is_(True))
            .all()
        )
        for (pid,) in home_players:
            key = (int(pid), int(away_id))
            if key not in seen:
                seen.add(key)
                pairs.append((int(pid), int(away_id), True, slate_date))
        for (pid,) in away_players:
            key = (int(pid), int(home_id))
            if key not in seen:
                seen.add(key)
                pairs.append((int(pid), int(home_id), False, slate_date))

    # Fallback: each active player's most recent logged opponent this season
    recent = (
        db.query(PlayerGameStat.player_id, PlayerGameStat.opponent_team_id, PlayerGameStat.is_home, PlayerGameStat.game_date)
        .filter(
            PlayerGameStat.season == season,
            PlayerGameStat.opponent_team_id.isnot(None),
            or_(
                PlayerGameStat.validation_status.is_(None),
                PlayerGameStat.validation_status != BoxScoreValidator.STATUS_INVALID,
            ),
        )
        .order_by(PlayerGameStat.game_date.desc())
        .all()
    )
    latest_for_player: Dict[int, Tuple[int, bool, date]] = {}
    for pid, opp_id, is_home, gdate in recent:
        if pid is None or opp_id is None or gdate is None:
            continue
        if int(pid) in latest_for_player:
            continue
        latest_for_player[int(pid)] = (int(opp_id), bool(is_home), gdate)

    for pid, (opp_id, is_home, gdate) in latest_for_player.items():
        key = (pid, opp_id)
        if key not in seen:
            seen.add(key)
            pairs.append((pid, opp_id, is_home, gdate))

    return pairs


def _upsert_row(
    db: Session,
    *,
    player_id: int,
    season: str,
    opponent_team_id: int,
    payload: Dict[str, Any],
    pipeline_run_id: Optional[int],
) -> None:
    row = (
        db.query(PlayerOpponentAnalysis)
        .filter_by(
            player_id=player_id,
            opponent_team_id=opponent_team_id,
            season=season,
        )
        .first()
    )
    if not row:
        row = PlayerOpponentAnalysis(
            player_id=player_id,
            opponent_team_id=opponent_team_id,
            season=season,
        )
        db.add(row)

    for key, value in payload.items():
        setattr(row, key, value)
    row.formula_version = FORMULA_VERSION
    row.computed_at = datetime.utcnow()
    row.pipeline_run_id = pipeline_run_id


def run(ctx: PipelineContext, db: Session) -> Dict[str, Any]:
    season = ctx.season or get_current_season()
    from ..utils.slate_date import resolve_slate_date

    slate_date = resolve_slate_date(db, target_date=ctx.target_date, season=season)
    run_id = ctx.run_id

    # Materialize ranks once (agent-time only — never on HTTP).
    def_ranks = (
        ContextCollector.get_cached_defensive_ranks(season)
        or ContextCollector._calculate_defensive_ranks(season)
        or {}
    )
    off_ranks = (
        ContextCollector.get_cached_offensive_ranks(season)
        or ContextCollector._calculate_offensive_ranks(season)
        or {}
    )
    pos_ranks = (
        ContextCollector.get_cached_position_ranks(season)
        or ContextCollector._calculate_position_defensive_ranks(season)
        or {}
    )
    def_avgs = ContextCollector.get_defensive_averages(season) or {}

    abbr_to_id = _team_abbr_map(db)
    id_to_abbr = _team_id_to_abbr(db)
    pairs = _slate_pairs(db, slate_date=slate_date, season=season, abbr_to_id=abbr_to_id)

    # If schedule empty, still cover prop-evaluation players for the slate date.
    if not pairs:
        from ...models.player_prop_evaluations import PlayerPropEvaluation

        prop_pids = [
            r[0]
            for r in db.query(PlayerPropEvaluation.player_id)
            .filter(PlayerPropEvaluation.game_date == slate_date)
            .distinct()
            .all()
        ]
        for pid in prop_pids:
            player = db.query(Player).filter(Player.id == int(pid)).first()
            if not player or not player.team_id:
                continue
            # Infer opponent from today's games involving player's team
            team = db.query(Team).filter(Team.id == player.team_id).first()
            if not team or not team.abbreviation:
                continue
            abbr = team.abbreviation.upper()
            game = (
                db.query(Game)
                .filter(
                    Game.game_date == slate_date,
                    or_(
                        Game.home_team_abbr == abbr,
                        Game.away_team_abbr == abbr,
                    ),
                )
                .first()
            )
            if not game:
                continue
            if (game.home_team_abbr or "").upper() == abbr:
                opp_abbr = (game.away_team_abbr or "").upper()
                is_home = True
            else:
                opp_abbr = (game.home_team_abbr or "").upper()
                is_home = False
            opp_id = abbr_to_id.get(opp_abbr)
            if opp_id:
                pairs.append((int(pid), int(opp_id), is_home, slate_date))

    players_by_id: Dict[int, Player] = {
        int(p.id): p
        for p in db.query(Player).filter(Player.id.in_([pid for pid, *_ in pairs] or [-1])).all()
    }

    team_perf_cache: Dict[int, Dict[str, Any]] = {}

    def _team_perf(tid: int) -> Dict[str, Any]:
        if tid not in team_perf_cache:
            try:
                team_perf_cache[tid] = ContextCollector.get_team_performance(tid, season=season) or {}
            except Exception:
                team_perf_cache[tid] = {}
        return team_perf_cache[tid]

    written = 0
    skipped = 0
    log_cache = _logs_by_player(db, [pid for pid, *_ in pairs], season)

    for player_id, opponent_team_id, is_home, game_date in pairs:
        player = players_by_id.get(player_id)
        position = _normalize_position(player.position if player else None)
        opp_abbr = id_to_abbr.get(opponent_team_id)

        logs = log_cache.get(player_id) or []

        h2h = _h2h_from_logs(logs, opp_abbr)

        opp_def = def_ranks.get(int(opponent_team_id)) or {}
        opp_off = off_ranks.get(int(opponent_team_id)) or {}
        opp_pos = {}
        if position:
            opp_pos = (pos_ranks.get(position) or {}).get(int(opponent_team_id)) or {}

        matchup_adv: Dict[str, Optional[float]] = {
            "pts": None,
            "reb": None,
            "ast": None,
            "3pm": None,
        }
        avgs = _season_avgs(logs)
        opp_avgs = def_avgs.get(int(opponent_team_id)) or {}
        if len(logs) >= 5 and opp_avgs:
            for key, out_key in (("pts", "pts"), ("reb", "reb"), ("ast", "ast"), ("3pm", "3pm")):
                if key in avgs and key in opp_avgs:
                    matchup_adv[out_key] = round(avgs[key] - float(opp_avgs[key]), 2)

        rest_days = _rest_from_logs(logs, game_date)
        injury: Dict[str, Any] = {}

        player_team_id = player.team_id if player else None
        team_perf = _team_perf(int(player_team_id)) if player_team_id else {}
        opp_perf = _team_perf(int(opponent_team_id))

        payload = {
            "opponent_team_abbr": opp_abbr,
            "game_date": game_date,
            "is_home_game": is_home,
            "h2h_avg_pts": h2h.get("h2h_avg_pts"),
            "h2h_avg_reb": h2h.get("h2h_avg_reb"),
            "h2h_avg_ast": h2h.get("h2h_avg_ast"),
            "h2h_games_played": int(h2h.get("h2h_games_played") or 0),
            "def_rank_pts": opp_def.get("pts") or opp_perf.get("def_rank_pts"),
            "def_rank_reb": opp_def.get("reb") or opp_perf.get("def_rank_reb"),
            "def_rank_ast": opp_def.get("ast") or opp_perf.get("def_rank_ast"),
            "def_rank_3pm": opp_def.get("3pm") or opp_perf.get("def_rank_3pm"),
            "off_rank_pts": opp_off.get("pts") or opp_perf.get("off_rank_pts"),
            "off_rank_reb": opp_off.get("reb") or opp_perf.get("off_rank_reb"),
            "off_rank_ast": opp_off.get("ast") or opp_perf.get("off_rank_ast"),
            "off_rank_3pm": opp_off.get("3pm") or opp_perf.get("off_rank_3pm"),
            "position": position,
            "pos_def_rank_pts": opp_pos.get("pts"),
            "pos_def_rank_reb": opp_pos.get("reb"),
            "pos_def_rank_ast": opp_pos.get("ast"),
            "pos_def_rank_3pm": opp_pos.get("3pm"),
            "matchup_adv_pts": matchup_adv.get("pts"),
            "matchup_adv_reb": matchup_adv.get("reb"),
            "matchup_adv_ast": matchup_adv.get("ast"),
            "matchup_adv_3pm": matchup_adv.get("3pm"),
            "opponent_win_rate": opp_perf.get("win_rate"),
            "opponent_conference_rank": opp_perf.get("conference_rank"),
            "team_win_rate": team_perf.get("win_rate"),
            "team_conference_rank": team_perf.get("conference_rank"),
            "team_recent_form": team_perf.get("recent_form"),
            "rest_days": rest_days,
            "is_injured": bool(injury.get("is_injured", False)),
            "injury_status": injury.get("injury_status"),
            "injury_description": injury.get("injury_description"),
        }

        try:
            _upsert_row(
                db,
                player_id=player_id,
                season=season,
                opponent_team_id=opponent_team_id,
                payload=payload,
                pipeline_run_id=run_id,
            )
            written += 1
        except Exception:
            skipped += 1

        if written % 50 == 0:
            db.flush()

    db.flush()
    return {
        "rows_written": written,
        "rows_skipped": skipped,
        "pairs": len(pairs),
        "game_date": slate_date.isoformat(),
        "season": season,
        "formula_version": FORMULA_VERSION,
        "has_def_ranks": bool(def_ranks),
        "has_off_ranks": bool(off_ranks),
    }

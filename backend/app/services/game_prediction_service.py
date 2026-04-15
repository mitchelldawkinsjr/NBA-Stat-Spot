"""
Game Prediction Service - Evaluates today's NBA games and predicts likely winner.
Uses team-level metrics (def/off ranks, pace, PPG), matchup advantages, and LLM for explanations.

Cache (24h TTL):
  - game_predictions:{date}  → list of predictions for that date (from ESPN scoreboard + def/off ranks + team stats)
  - game_prediction_detail:v3:{game_id}  → full detail for one game (short TTL when incomplete)
Warm: /admin/warm-dashboard calls get_todays_predictions(). Clear: POST /admin/cache/clear/game-predictions.

Data sources: ESPN scoreboard (games), ContextCollector def/off ranks, TeamStatsService (ppg/pace from NBA API or
league defaults 112.5/100.0). When pace is default we overlay ContextCollector._calculate_pace_ranks() so predictions
use computed possessions when available.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, Tuple
from datetime import date, datetime
import re as _re
import threading
import time
import structlog
from ..utils.season import get_current_season
from .context_collector import ContextCollector, wait_until_ranks_ready
from .team_stats_service import TeamStatsService
from .cache_service import get_cache_service
from .nba_api_service import NBADataService
from .llm.prompt_builder import (
    GAME_OUTLOOK_SYSTEM_PROMPT,
    GAME_SUMMARY_SYSTEM_PROMPT,
    build_game_summary_prompt,
    build_game_outlook_prompt,
)

logger = structlog.get_logger()

# Home court advantage as win probability boost (e.g. 0.52 -> 52% base for home)
HOME_COURT_ADVANTAGE = 0.04


def _normalize_team_abbr(abbr: Optional[str]) -> str:
    """Normalize ESPN/NBA abbreviation variants to canonical NBA-style abbreviations."""
    if not abbr:
        return ""
    u = abbr.strip().upper()
    alias_to_nba = {
        "SA": "SAS",
        "NO": "NOP",
        "GS": "GSW",
        "NY": "NYK",
    }
    return alias_to_nba.get(u, u)


def _get_teams_by_abbr() -> Dict[str, Dict[str, Any]]:
    """Return map of uppercase abbreviation -> {id, full_name, abbreviation}."""
    cache = get_cache_service()
    cache_key = "nba:teams_by_abbr:1h"
    cached = cache.get(cache_key)
    if isinstance(cached, dict) and cached:
        return cached
    teams = NBADataService.fetch_all_teams() or []
    out: Dict[str, Dict[str, Any]] = {}
    for t in teams:
        abbr = (t.get("abbreviation") or "").strip().upper()
        if abbr:
            out[abbr] = {"id": t.get("id"), "full_name": t.get("full_name"), "abbreviation": abbr}
    cache.set(cache_key, out, ttl=3600)
    return out


def _resolve_team(teams_by_abbr: Dict[str, Dict[str, Any]], espn_abbr: str) -> Optional[Dict[str, Any]]:
    """
    Map ESPN scoreboard abbreviation to NBA static team row.
    ESPN uses SA (Spurs), NO (Pelicans), GS (Warriors), NY (Knicks); NBA API uses SAS, NOP, GSW, NYK.
    """
    if not espn_abbr:
        return None
    u = _normalize_team_abbr(espn_abbr)
    if u in teams_by_abbr:
        return teams_by_abbr[u]
    # Common short forms not present on nba_api team list
    tid = NBADataService.ESPN_ABBR_TO_NBA_ID.get(u)
    if tid is not None:
        for info in teams_by_abbr.values():
            if info.get("id") == tid:
                return info
    return None


def _wait_for_ranks(season: str, max_wait_ms: int = 8000) -> Tuple[Dict, Dict, Dict, Dict]:
    """Poll rank caches until all four are non-empty or timeout; returns best-effort dicts."""
    start = time.perf_counter()
    def_ranks: Dict = {}
    off_ranks: Dict = {}
    pace_ranks: Dict = {}
    pos_ranks: Dict = {}
    triggered = False
    while (time.perf_counter() - start) * 1000 < max_wait_ms:
        def_ranks = ContextCollector.get_cached_defensive_ranks(season)
        off_ranks = ContextCollector.get_cached_offensive_ranks(season)
        pace_ranks = ContextCollector.get_cached_pace_ranks(season)
        pos_ranks = ContextCollector.get_cached_position_ranks(season)
        if def_ranks and off_ranks and pace_ranks and pos_ranks:
            return def_ranks, off_ranks, pace_ranks, pos_ranks
        if not triggered:
            ContextCollector._trigger_background_rank_refresh(season)
            triggered = True
        time.sleep(0.2)
    logger.warning(
        "Rank cache poll timeout; returning partial rank dicts",
        season=season,
        has_def=bool(def_ranks),
        has_off=bool(off_ranks),
        has_pace=bool(pace_ranks),
        has_pos=bool(pos_ranks),
    )
    return def_ranks or {}, off_ranks or {}, pace_ranks or {}, pos_ranks or {}


def _win_probability_from_ranks(
    home_off_pts: Optional[int],
    home_def_pts: Optional[int],
    away_off_pts: Optional[int],
    away_def_pts: Optional[int],
    home_ppg: float,
    away_ppg: float,
) -> float:
    """
    Heuristic win probability for home team (0-1).
    Uses offensive/defensive ranks and PPG. Lower def rank = better D; higher off rank = worse (rank 1 = best).
    """
    n = 30.0
    # Strength: good offense (low off rank = good, so use (31 - off_rank)/30) and good defense (low def rank = good)
    home_off_strength = (n + 1 - (home_off_pts or 15)) / n if home_off_pts else 0.5
    home_def_strength = (n + 1 - (home_def_pts or 15)) / n if home_def_pts else 0.5
    away_off_strength = (n + 1 - (away_off_pts or 15)) / n if away_off_pts else 0.5
    away_def_strength = (n + 1 - (away_def_pts or 15)) / n if away_def_pts else 0.5
    # Combined: offense vs opponent defense, defense vs opponent offense
    home_score = 0.5 * home_off_strength * (1 - away_def_strength) + 0.5 * (1 - away_off_strength) * home_def_strength
    away_score = 0.5 * away_off_strength * (1 - home_def_strength) + 0.5 * (1 - home_off_strength) * away_def_strength
    # PPG tilt (normalize around 112)
    home_ppg_norm = (home_ppg - 100) / 30 if home_ppg else 0
    away_ppg_norm = (away_ppg - 100) / 30 if away_ppg else 0
    home_score += 0.1 * (home_ppg_norm - away_ppg_norm)
    away_score += 0.1 * (away_ppg_norm - home_ppg_norm)
    total = home_score + away_score
    if total <= 0:
        prob = 0.5
    else:
        prob = home_score / total
    prob += HOME_COURT_ADVANTAGE
    return max(0.0, min(1.0, prob))


def _key_advantages(
    predicted_winner_abbr: str,
    home_abbr: str,
    away_abbr: str,
    home_off: Dict[str, Optional[int]],
    home_def: Dict[str, Optional[int]],
    away_off: Dict[str, Optional[int]],
    away_def: Dict[str, Optional[int]],
    home_ppg: float,
    away_ppg: float,
    home_pace: float,
    away_pace: float,
) -> List[str]:
    """Build a short list of key advantage phrases for the predicted winner (e.g. 'defensive rebounding', 'pace control')."""
    advantages = []
    is_home_winner = predicted_winner_abbr == home_abbr
    win_def = home_def if is_home_winner else away_def
    lose_def = away_def if is_home_winner else home_def
    win_off = home_off if is_home_winner else away_off
    win_pace = home_pace if is_home_winner else away_pace
    lose_pace = away_pace if is_home_winner else home_pace
    # Defensive rank: lower = better
    if (win_def.get("reb") or 30) < (lose_def.get("reb") or 30):
        advantages.append("defensive rebounding")
    if (win_def.get("pts") or 30) <= 10:
        advantages.append("points defense")
    if (win_off.get("pts") or 20) <= 8:
        advantages.append("scoring offense")
    if win_pace > lose_pace + 2:
        advantages.append("pace control")
    return advantages[:3]


class GamePredictionService:
    def __init__(self):
        self.cache = get_cache_service()
        self._team_stats = TeamStatsService()

    def _build_prediction_payload(
        self,
        game_id: str,
        home_abbr: str,
        away_abbr: str,
        event_date: str,
        teams_by_abbr: Dict[str, Dict[str, Any]],
        def_ranks: Dict[int, Dict[str, Any]],
        off_ranks: Dict[int, Dict[str, Any]],
        season: str,
    ) -> Dict[str, Any]:
        home_team = _resolve_team(teams_by_abbr, home_abbr)
        away_team = _resolve_team(teams_by_abbr, away_abbr)
        home_id = int(home_team["id"]) if home_team and home_team.get("id") is not None else None
        away_id = int(away_team["id"]) if away_team and away_team.get("id") is not None else None

        home_def = def_ranks.get(home_id, {}) if home_id else {}
        home_off = off_ranks.get(home_id, {}) if home_id else {}
        away_def = def_ranks.get(away_id, {}) if away_id else {}
        away_off = off_ranks.get(away_id, {}) if away_id else {}

        home_abbr_nba = (home_team or {}).get("abbreviation") or home_abbr
        away_abbr_nba = (away_team or {}).get("abbreviation") or away_abbr
        home_stats = self._team_stats.get_team_stats(home_abbr_nba)
        away_stats = self._team_stats.get_team_stats(away_abbr_nba)
        default_ppg = 112.5
        default_pace = 100.0
        home_ppg = getattr(home_stats, "ppg", default_ppg) or default_ppg
        away_ppg = getattr(away_stats, "ppg", default_ppg) or default_ppg
        home_pace = getattr(home_stats, "pace", default_pace) or default_pace
        away_pace = getattr(away_stats, "pace", default_pace) or default_pace

        try:
            pace_ranks = ContextCollector.get_cached_pace_ranks(season)
            if home_id and (home_pace is None or home_pace == default_pace):
                p = pace_ranks.get(home_id, {})
                if p.get("possessions"):
                    home_pace = float(p["possessions"])
            if away_id and (away_pace is None or away_pace == default_pace):
                p = pace_ranks.get(away_id, {})
                if p.get("possessions"):
                    away_pace = float(p["possessions"])
        except Exception:
            pass

        if home_ppg == default_ppg or away_ppg == default_ppg:
            try:
                team_ppg_from_logs = ContextCollector._get_team_ppg_from_player_logs(season)
                if home_id and home_ppg == default_ppg and home_id in team_ppg_from_logs:
                    home_ppg = team_ppg_from_logs[home_id]
                if away_id and away_ppg == default_ppg and away_id in team_ppg_from_logs:
                    away_ppg = team_ppg_from_logs[away_id]
            except Exception:
                pass

        prob_home = _win_probability_from_ranks(
            home_off.get("pts"),
            home_def.get("pts"),
            away_off.get("pts"),
            away_def.get("pts"),
            home_ppg,
            away_ppg,
        )
        prob_away = 1.0 - prob_home
        predicted_winner_abbr = home_abbr if prob_home >= 0.5 else away_abbr
        predicted_winner_name = (
            (home_team or {}).get("full_name") or home_abbr
            if predicted_winner_abbr == home_abbr
            else (away_team or {}).get("full_name") or away_abbr
        )

        key_adv = _key_advantages(
            predicted_winner_abbr,
            home_abbr,
            away_abbr,
            home_off,
            home_def,
            away_off,
            away_def,
            home_ppg,
            away_ppg,
            home_pace,
            away_pace,
        )
        key_advantage_summary = " and ".join(key_adv) if key_adv else "balanced matchup"
        return {
            "gameId": game_id,
            "home": home_abbr,
            "away": away_abbr,
            "home_team_id": home_id,
            "away_team_id": away_id,
            "home_full_name": (home_team or {}).get("full_name") or home_abbr,
            "away_full_name": (away_team or {}).get("full_name") or away_abbr,
            "predicted_winner": predicted_winner_abbr,
            "predicted_winner_name": predicted_winner_name,
            "win_probability_home": round(prob_home * 100, 1),
            "win_probability_away": round(prob_away * 100, 1),
            "key_advantage_summary": key_advantage_summary,
            "outlook_summary": None,
            "game_time_utc": event_date,
            "home_off_rank_pts": home_off.get("pts"),
            "home_def_rank_pts": home_def.get("pts"),
            "away_off_rank_pts": away_off.get("pts"),
            "away_def_rank_pts": away_def.get("pts"),
            "home_ppg": home_ppg,
            "away_ppg": away_ppg,
            "home_pace": home_pace,
            "away_pace": away_pace,
        }

    def _populate_prediction_summaries_async(self, cache_key: str, predictions: List[Dict[str, Any]]) -> None:
        """Fill outlook_summary in background so request path stays fast."""
        if not predictions:
            return

        def _run() -> None:
            started = time.perf_counter()
            try:
                cached = self.cache.get(cache_key)
                rows = list(cached) if isinstance(cached, list) else list(predictions)
                updated = False
                for row in rows:
                    if row.get("outlook_summary"):
                        continue
                    pred = row.get("predicted_winner") or ""
                    win_pct = int(
                        row.get("win_probability_home", 50)
                        if pred == row.get("home")
                        else row.get("win_probability_away", 50)
                    )
                    row["outlook_summary"] = self._generate_prediction_summary(
                        row.get("home") or "",
                        row.get("away") or "",
                        pred,
                        win_pct,
                        row.get("key_advantage_summary") or "balanced matchup",
                        float(row.get("home_ppg") or 112.5),
                        float(row.get("away_ppg") or 112.5),
                        float(row.get("home_pace") or 100.0),
                        float(row.get("away_pace") or 100.0),
                    )
                    updated = True
                if updated:
                    self.cache.set(cache_key, rows, ttl=86400)
            except Exception as exc:
                logger.debug("Background prediction summaries failed", error=str(exc))
            finally:
                logger.info(
                    "Prediction summaries background task complete",
                    cache_key=cache_key,
                    elapsed_ms=round((time.perf_counter() - started) * 1000, 1),
                )

        threading.Thread(target=_run, daemon=True).start()

    def get_todays_predictions(self, target_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """
        Get predictions for all games on the given date (default today).
        Returns list of { gameId, home, away, home_team_id, away_team_id, predicted_winner, win_probability_home, win_probability_away, key_advantage_summary, game_time_utc, ... }.
        """
        target_date = target_date or date.today()
        cache_key = f"game_predictions:{target_date.isoformat()}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        request_started = time.perf_counter()
        from .espn_api_service import get_espn_service
        espn = get_espn_service()
        date_str = target_date.strftime("%Y%m%d")
        scoreboard_started = time.perf_counter()
        try:
            scoreboard = espn.get_scoreboard(date=date_str)
        except Exception as e:
            logger.warning("Scoreboard fetch failed", date=target_date.isoformat(), error=str(e))
            scoreboard = None
        logger.info(
            "Scoreboard fetch complete",
            date=target_date.isoformat(),
            elapsed_ms=round((time.perf_counter() - scoreboard_started) * 1000, 1),
        )
        if not scoreboard or not isinstance(scoreboard.get("events"), list):
            logger.warning("No scoreboard events for date", date=target_date.isoformat())
            self.cache.set(cache_key, [], ttl=3600)
            return []

        teams_by_abbr = _get_teams_by_abbr()
        season = get_current_season()
        ranks_started = time.perf_counter()
        def_ranks = ContextCollector.get_cached_defensive_ranks(season)
        off_ranks = ContextCollector.get_cached_offensive_ranks(season)
        if not def_ranks or not off_ranks:
            def_fb, off_fb = ContextCollector.get_cached_team_ranks_fallback(season)
            if not def_ranks and def_fb:
                def_ranks = def_fb
            if not off_ranks and off_fb:
                off_ranks = off_fb
            warming_key = f"ranks_warming:{season}:60s"
            if self.cache.get(warming_key) is None:
                self.cache.set(warming_key, True, ttl=60)
                ContextCollector._trigger_background_rank_refresh(season)
        logger.info(
            "Rank lookup complete",
            season=season,
            has_def=bool(def_ranks),
            has_off=bool(off_ranks),
            elapsed_ms=round((time.perf_counter() - ranks_started) * 1000, 1),
        )

        predictions = []
        for event in scoreboard["events"]:
            try:
                game_id = str(event.get("id", ""))
                comps = event.get("competitions") or []
                if not comps:
                    continue
                comp = comps[0]
                competitors = comp.get("competitors") or []
                home_abbr = away_abbr = None
                for c in competitors:
                    abbr = (c.get("team") or {}).get("abbreviation", "")
                    if (c.get("homeAway") or "").lower() == "home":
                        home_abbr = abbr.strip().upper()
                    else:
                        away_abbr = abbr.strip().upper()
                if not home_abbr or not away_abbr:
                    continue

                predictions.append(
                    self._build_prediction_payload(
                        game_id=game_id,
                        home_abbr=home_abbr,
                        away_abbr=away_abbr,
                        event_date=event.get("date") or "",
                        teams_by_abbr=teams_by_abbr,
                        def_ranks=def_ranks,
                        off_ranks=off_ranks,
                        season=season,
                    )
                )
            except Exception as e:
                logger.warning("Failed to build prediction for game", game_id=event.get("id"), error=str(e))
                continue

        self.cache.set(cache_key, predictions, ttl=86400)
        self._populate_prediction_summaries_async(cache_key, predictions)
        try:
            from .accuracy_tracking_service import record_game_predictions
            record_game_predictions(target_date, predictions)
        except Exception as e:
            logger.debug("record_game_predictions failed", date=target_date.isoformat(), error=str(e))
        logger.info(
            "Prediction request complete",
            date=target_date.isoformat(),
            games=len(predictions),
            elapsed_ms=round((time.perf_counter() - request_started) * 1000, 1),
        )
        return predictions

    def _resolve_game_from_espn(self, game_id: str) -> Optional[Dict[str, Any]]:
        """When game is not in today's predictions, try to load from ESPN summary and build minimal prediction."""
        try:
            from .espn_api_service import get_espn_service
            espn = get_espn_service()
            summary = espn.get_game_summary(game_id)
            if not summary:
                return None
            header = summary.get("header") or {}
            comps = header.get("competitions") or []
            if not comps:
                return None
            comp = comps[0]
            competitors = comp.get("competitors") or []
            home_abbr = away_abbr = None
            for c in competitors:
                abbr = ((c.get("team") or {}).get("abbreviation") or "").strip().upper()
                if (c.get("homeAway") or "").lower() == "home":
                    home_abbr = abbr
                else:
                    away_abbr = abbr
            if not home_abbr or not away_abbr:
                return None
            teams_by_abbr = _get_teams_by_abbr()
            season = get_current_season()
            def_ranks = ContextCollector.get_cached_defensive_ranks(season) or {}
            off_ranks = ContextCollector.get_cached_offensive_ranks(season) or {}
            if not def_ranks or not off_ranks:
                def_fb, off_fb = ContextCollector.get_cached_team_ranks_fallback(season)
                if not def_ranks and def_fb:
                    def_ranks = def_fb
                if not off_ranks and off_fb:
                    off_ranks = off_fb
            event_date = (comps[0].get("date") if comps else "") or comp.get("date") or ""
            return self._build_prediction_payload(
                game_id=game_id,
                home_abbr=home_abbr,
                away_abbr=away_abbr,
                event_date=event_date,
                teams_by_abbr=teams_by_abbr,
                def_ranks=def_ranks,
                off_ranks=off_ranks,
                season=season,
            )
        except Exception as e:
            logger.debug("Resolve game from ESPN failed", game_id=game_id, error=str(e))
            return None

    def get_game_prediction_detail(self, game_id: str, target_date: Optional[date] = None) -> Optional[Dict[str, Any]]:
        """Get full prediction and detail for one game (for game detail page)."""
        target_date = target_date or date.today()
        cache_key = f"game_prediction_detail:v3:{game_id}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        predictions = self.get_todays_predictions(target_date)
        one = next((p for p in predictions if p["gameId"] == game_id), None)
        if not one:
            one = self._resolve_game_from_espn(game_id)
        if not one:
            return None

        season = get_current_season()
        home_id = one.get("home_team_id")
        away_id = one.get("away_team_id")
        home_abbr = (one.get("home") or "").strip().upper()
        away_abbr = (one.get("away") or "").strip().upper()

        if home_id is None or away_id is None:
            teams_by_abbr = _get_teams_by_abbr()
            if home_id is None:
                ht = _resolve_team(teams_by_abbr, home_abbr)
                home_id = int(ht["id"]) if ht and ht.get("id") is not None else None
            if away_id is None:
                at = _resolve_team(teams_by_abbr, away_abbr)
                away_id = int(at["id"]) if at and at.get("id") is not None else None
            one["home_team_id"] = home_id
            one["away_team_id"] = away_id

        wait_until_ranks_ready(10.0)

        def_ranks = ContextCollector.get_cached_defensive_ranks(season)
        off_ranks = ContextCollector.get_cached_offensive_ranks(season)
        pace_ranks = ContextCollector.get_cached_pace_ranks(season)
        pos_ranks = ContextCollector.get_cached_position_ranks(season)

        if not def_ranks or not off_ranks or not pace_ranks or not pos_ranks:
            def_ranks, off_ranks, pace_ranks, pos_ranks = _wait_for_ranks(season, 8000)

        # If primary tables are still empty for these teams, try the fallback (also cache-backed, instant when warm)
        _hid_check = int(home_id) if home_id is not None else None
        _aid_check = int(away_id) if away_id is not None else None
        need_def = not def_ranks or (_hid_check and def_ranks.get(_hid_check) is None) or (_aid_check and def_ranks.get(_aid_check) is None)
        need_off = not off_ranks or (_hid_check and off_ranks.get(_hid_check) is None) or (_aid_check and off_ranks.get(_aid_check) is None)
        if need_def or need_off:
            def_fb, off_fb = ContextCollector.get_cached_team_ranks_fallback(season)
            if need_def and def_fb:
                def_ranks = dict(def_ranks)
                for tid, r in def_fb.items():
                    tid_int = int(tid) if tid is not None else None
                    if tid_int is not None and (tid_int not in def_ranks or not def_ranks.get(tid_int)):
                        def_ranks[tid_int] = r
            if need_off and off_fb:
                off_ranks = dict(off_ranks)
                for tid, r in off_fb.items():
                    tid_int = int(tid) if tid is not None else None
                    if tid_int is not None and (tid_int not in off_ranks or not off_ranks.get(tid_int)):
                        off_ranks[tid_int] = r

        _hid = int(home_id) if home_id is not None else None
        _aid = int(away_id) if away_id is not None else None
        # Use trailing `or {}`: `(None or None)` and falsy `{}` must not become Python None (JSON null) on the client
        home_def_full = ((def_ranks.get(_hid) or def_ranks.get(home_id)) or {}) if (_hid or home_id) else {}
        away_def_full = ((def_ranks.get(_aid) or def_ranks.get(away_id)) or {}) if (_aid or away_id) else {}
        home_off_full = ((off_ranks.get(_hid) or off_ranks.get(home_id)) or {}) if (_hid or home_id) else {}
        away_off_full = ((off_ranks.get(_aid) or off_ranks.get(away_id)) or {}) if (_aid or away_id) else {}
        # If league tables omitted PTS rows but the scoreboard prediction has scalar ranks, merge so charts are not empty
        if home_def_full.get("pts") is None and one.get("home_def_rank_pts") is not None:
            home_def_full = {**home_def_full, "pts": one["home_def_rank_pts"]}
        if away_def_full.get("pts") is None and one.get("away_def_rank_pts") is not None:
            away_def_full = {**away_def_full, "pts": one["away_def_rank_pts"]}
        if home_off_full.get("pts") is None and one.get("home_off_rank_pts") is not None:
            home_off_full = {**home_off_full, "pts": one["home_off_rank_pts"]}
        if away_off_full.get("pts") is None and one.get("away_off_rank_pts") is not None:
            away_off_full = {**away_off_full, "pts": one["away_off_rank_pts"]}
        # Pace / position defense dicts use int team_id keys; JSON cache may deserialize ids as str — use _hid/_aid first
        home_pace_data = (
            (pace_ranks.get(_hid) or pace_ranks.get(home_id) or {})
            if (_hid is not None or home_id)
            else {}
        )
        away_pace_data = (
            (pace_ranks.get(_aid) or pace_ranks.get(away_id) or {})
            if (_aid is not None or away_id)
            else {}
        )

        # Position defense: how each team defends each position
        positions = ["PG", "SG", "SF", "PF", "C"]
        home_pos_defense = {}
        away_pos_defense = {}
        for pos in positions:
            pos_data = pos_ranks.get(pos, {})
            if _hid is not None or home_id:
                home_pos_defense[pos] = pos_data.get(_hid) or pos_data.get(home_id) or {}
            if _aid is not None or away_id:
                away_pos_defense[pos] = pos_data.get(_aid) or pos_data.get(away_id) or {}

        # --- Key players ---
        home_key_players = _get_team_key_players(home_id, season)
        away_key_players = _get_team_key_players(away_id, season)

        # --- H2H history ---
        h2h_games = _get_h2h_from_schedule(home_id, away_id, home_abbr, away_abbr, season)
        h2h_wins_home = sum(1 for g in h2h_games if g.get("winner") == home_abbr)
        h2h_wins_away = len(h2h_games) - h2h_wins_home

        # Build extended outlook for detail page (longer LLM summary; include player averages and recent form)
        key_players_text = _format_key_players_for_prompt(home_key_players, away_key_players, home_abbr, away_abbr)
        extended_outlook = self._generate_game_outlook(
            home_abbr, away_abbr,
            one["predicted_winner"],
            one["win_probability_home"] if one["predicted_winner"] == home_abbr else one["win_probability_away"],
            one["key_advantage_summary"],
            one.get("home_ppg"), one.get("away_ppg"), one.get("home_pace"), one.get("away_pace"),
            one.get("home_off_rank_pts"), one.get("home_def_rank_pts"),
            one.get("away_off_rank_pts"), one.get("away_def_rank_pts"),
            key_players_text=key_players_text,
        )

        ranks_incomplete = not (def_ranks and off_ranks and pace_ranks and pos_ranks)
        incomplete = (
            home_id is None
            or away_id is None
            or not home_def_full
            or not away_def_full
            or not home_off_full
            or not away_off_full
            or ranks_incomplete
        )
        ttl = 300 if incomplete else 86400

        one = {
            **one,
            "outlook_extended": extended_outlook,
            # Full rank breakdowns
            "home_def_full": home_def_full,
            "away_def_full": away_def_full,
            "home_off_full": home_off_full,
            "away_off_full": away_off_full,
            "home_pace_data": home_pace_data,
            "away_pace_data": away_pace_data,
            # Position-based defense
            "home_pos_defense": home_pos_defense,
            "away_pos_defense": away_pos_defense,
            # Key players
            "home_key_players": home_key_players,
            "away_key_players": away_key_players,
            # H2H
            "h2h_games": h2h_games,
            "h2h_wins_home": h2h_wins_home,
            "h2h_wins_away": h2h_wins_away,
            "_incomplete": incomplete,
        }
        self.cache.set(cache_key, one, ttl=ttl)
        return one

    def _generate_prediction_summary(
        self,
        home_abbr: str,
        away_abbr: str,
        winner_abbr: str,
        win_pct: int,
        key_advantage: str,
        home_ppg: float,
        away_ppg: float,
        home_pace: float,
        away_pace: float,
    ) -> str:
        """Short LLM or rule-based summary for list view."""
        try:
            from .rationale_generator import get_rationale_generator
            gen = get_rationale_generator()
            if not gen.is_available():
                return f"{winner_abbr} favored ({win_pct}%). Key advantage: {key_advantage}."
            # Detect whether the first service is chat-based (OpenAI) or single-prompt (Ollama)
            first_svc = gen.services[0] if gen.services else None
            for_chat = hasattr(first_svc, "client") if first_svc else True
            prompt = build_game_summary_prompt(
                home_abbr=home_abbr,
                away_abbr=away_abbr,
                winner_abbr=winner_abbr,
                win_pct=win_pct,
                key_advantage=key_advantage,
                home_ppg=home_ppg,
                away_ppg=away_ppg,
                home_pace=home_pace,
                away_pace=away_pace,
                for_chat_api=for_chat,
            )
            if for_chat and first_svc and hasattr(first_svc, "client"):
                try:
                    resp = first_svc.client.chat.completions.create(
                        model=first_svc.model,
                        messages=[
                            {"role": "system", "content": GAME_SUMMARY_SYSTEM_PROMPT},
                            {"role": "user", "content": prompt},
                        ],
                        temperature=0.4,
                        max_tokens=60,
                    )
                    result = (resp.choices[0].message.content or "").strip()
                    if result:
                        return result[:200]
                except Exception:
                    pass
            result = gen._generate_simple(prompt, max_tokens=60)
            if result:
                return result.strip()[:200]
        except Exception as e:
            logger.debug("Game prediction LLM summary failed", error=str(e))
        return f"{winner_abbr} favored ({win_pct}%). Key advantage: {key_advantage}."

    def _generate_game_outlook(
        self,
        home_abbr: str,
        away_abbr: str,
        winner_abbr: str,
        win_pct: float,
        key_advantage: str,
        home_ppg: Optional[float],
        away_ppg: Optional[float],
        home_pace: Optional[float],
        away_pace: Optional[float],
        home_off_pts: Optional[int],
        home_def_pts: Optional[int],
        away_off_pts: Optional[int],
        away_def_pts: Optional[int],
        key_players_text: Optional[str] = None,
    ) -> str:
        """Longer LLM-generated outlook for game detail page. Includes player averages and recent form when provided."""
        try:
            from .rationale_generator import get_rationale_generator
            gen = get_rationale_generator()
            if not gen.is_available():
                return (
                    f"The model favors {winner_abbr} with a {win_pct:.0f}% win probability. "
                    f"Key factors: {key_advantage}. Use the team comparison and defensive matchup sections below for details."
                )
            first_svc = gen.services[0] if gen.services else None
            for_chat = hasattr(first_svc, "client") if first_svc else True
            prompt = build_game_outlook_prompt(
                home_abbr=home_abbr,
                away_abbr=away_abbr,
                winner_abbr=winner_abbr,
                win_pct=win_pct,
                key_advantage=key_advantage,
                home_ppg=home_ppg,
                away_ppg=away_ppg,
                home_pace=home_pace,
                away_pace=away_pace,
                home_off_pts=home_off_pts,
                home_def_pts=home_def_pts,
                away_off_pts=away_off_pts,
                away_def_pts=away_def_pts,
                key_players_text=key_players_text,
                for_chat_api=for_chat,
            )
            if for_chat and first_svc and hasattr(first_svc, "client"):
                try:
                    resp = first_svc.client.chat.completions.create(
                        model=first_svc.model,
                        messages=[
                            {"role": "system", "content": GAME_OUTLOOK_SYSTEM_PROMPT},
                            {"role": "user", "content": prompt},
                        ],
                        temperature=0.5,
                        max_tokens=400,
                    )
                    result = (resp.choices[0].message.content or "").strip()
                    if result:
                        return result[:800]
                except Exception:
                    pass
            result = gen._generate_simple(prompt, max_tokens=400)
            if result:
                return result.strip()[:800]
        except Exception as e:
            logger.debug("Game outlook LLM failed", error=str(e))
        return (
            f"The model favors {winner_abbr} with a {win_pct:.0f}% win probability based on team metrics and matchup. "
            f"Key factors: {key_advantage}."
        )


def _avg(vals: List[float]) -> Optional[float]:
    """Return mean of a list, or None if empty."""
    return round(sum(vals) / len(vals), 1) if vals else None


def _format_key_players_for_prompt(
    home_players: List[Dict[str, Any]],
    away_players: List[Dict[str, Any]],
    home_abbr: str,
    away_abbr: str,
    max_per_side: int = 3,
) -> str:
    """Format key players' season averages and last-5 for LLM prompt (player stats in prediction context)."""
    def fmt(p: Dict[str, Any]) -> str:
        name = (p.get("name") or p.get("full_name") or "?").strip().split()[-1] or "?"
        pts = p.get("season_pts")
        l5 = p.get("last5_pts")
        reb = p.get("season_reb")
        ast = p.get("season_ast")
        s = f"{name} {pts:.1f} ppg" if pts is not None else f"{name}"
        if l5 is not None:
            s += f" (last 5: {l5:.1f})"
        if reb is not None or ast is not None:
            extras = []
            if reb is not None:
                extras.append(f"{reb:.1f} rpg")
            if ast is not None:
                extras.append(f"{ast:.1f} apg")
            s += " " + ", ".join(extras)
        return s

    home_str = ", ".join(fmt(p) for p in (home_players or [])[:max_per_side])
    away_str = ", ".join(fmt(p) for p in (away_players or [])[:max_per_side])
    if not home_str and not away_str:
        return ""
    lines = []
    if home_str:
        lines.append(f"{home_abbr} key players: {home_str}.")
    if away_str:
        lines.append(f"{away_abbr} key players: {away_str}.")
    return " ".join(lines)


def _parse_opp_abbr(matchup: str) -> Optional[str]:
    """Parse opponent abbreviation from NBA game-log matchup string (e.g. 'LAL vs. GSW' → 'GSW')."""
    if not matchup:
        return None
    mu = matchup.upper().strip()
    m = _re.search(r'([A-Z]{2,4})\s+(?:VS\.?|V\.?|@)\s+([A-Z]{2,4})', mu)
    if m:
        return m.group(2).strip(" .")
    return None


def _get_team_key_players(
    team_id: Optional[int],
    season: str,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """Return top players for a team with season and last-5 averages from cached game logs."""
    if not team_id:
        return []
    try:
        cache = get_cache_service()
        cache_key = f"team_key_players:{team_id}:{season}:{limit}:24h"
        cached = cache.get(cache_key)
        if isinstance(cached, list):
            return cached
        all_players = NBADataService.fetch_all_players_including_rookies() or []
        team_players = [p for p in all_players if int(p.get("team_id") or -1) == team_id]
        results = []
        for player in team_players:
            pid = player.get("id")
            if not pid:
                continue
            try:
                logs = NBADataService.fetch_player_game_log(pid, season)
                if not logs:
                    continue
                # Compute average minutes from logs
                mins_vals = []
                for g in logs[:20]:
                    m_raw = g.get("minutes", g.get("min"))
                    if m_raw is None or m_raw == "":
                        continue
                    try:
                        m_str = str(m_raw)
                        if ":" in m_str:
                            mm, ss = m_str.split(":", 1)
                            mins_vals.append(float(mm) + (float(ss) / 60.0))
                        else:
                            mins_vals.append(float(m_str))
                    except Exception:
                        pass
                avg_mins = (_avg(mins_vals) or 0)
                if avg_mins < 12:
                    continue
                pts = [float(g.get("pts", 0) or 0) for g in logs]
                reb = [float(g.get("reb", 0) or 0) for g in logs]
                ast = [float(g.get("ast", 0) or 0) for g in logs]
                last5 = logs[:5]
                l5_pts = [float(g.get("pts", 0) or 0) for g in last5]
                l5_reb = [float(g.get("reb", 0) or 0) for g in last5]
                l5_ast = [float(g.get("ast", 0) or 0) for g in last5]
                results.append({
                    "id": pid,
                    "name": player.get("full_name") or player.get("name"),
                    "position": player.get("position"),
                    "avg_min": round(avg_mins, 1),
                    "season_pts": _avg(pts),
                    "season_reb": _avg(reb),
                    "season_ast": _avg(ast),
                    "last5_pts": _avg(l5_pts),
                    "last5_reb": _avg(l5_reb),
                    "last5_ast": _avg(l5_ast),
                    "games_played": len(logs),
                })
            except Exception:
                continue
        results.sort(key=lambda x: (x.get("season_pts") or 0), reverse=True)
        out = results[:limit]
        cache.set(cache_key, out, ttl=86400)
        return out
    except Exception as e:
        logger.debug("_get_team_key_players failed", team_id=team_id, error=str(e))
        return []


def _get_h2h_from_schedule(
    home_team_id: Optional[int],
    away_team_id: Optional[int],
    home_abbr: str,
    away_abbr: str,
    season: str,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """
    Use ESPN team schedule to find past H2H meetings between the two teams.
    Returns list of {date, home, away, home_score, away_score, winner} dicts.
    """
    if not home_team_id:
        return []
    try:
        from .espn_mapping_service import get_espn_mapping_service
        from .espn_api_service import get_espn_service
        mapping = get_espn_mapping_service()
        home_slug = mapping.get_espn_team_slug(home_team_id)
        if not home_slug:
            return []
        espn = get_espn_service()
        schedule = espn.get_team_schedule(home_slug)
        meetings = []
        for event in schedule:
            comps = event.get("competitions") or []
            if not comps:
                continue
            comp = comps[0]
            competitors = comp.get("competitors") or []
            ev_home = ev_away = None
            for c in competitors:
                abbr = ((c.get("team") or {}).get("abbreviation") or "").strip().upper()
                ha = (c.get("homeAway") or "").lower()
                score_raw = c.get("score") or "0"
                try:
                    score = int(str(score_raw).split(".")[0])
                except Exception:
                    score = 0
                if ha == "home":
                    ev_home = {"abbr": abbr, "score": score}
                else:
                    ev_away = {"abbr": abbr, "score": score}
            if not ev_home or not ev_away:
                continue
            # Only include games between these two specific teams
            pair = {_normalize_team_abbr(ev_home["abbr"]), _normalize_team_abbr(ev_away["abbr"])}
            req_pair = {_normalize_team_abbr(home_abbr), _normalize_team_abbr(away_abbr)}
            if req_pair != pair:
                continue
            # Only include completed games (score > 0)
            if ev_home["score"] == 0 and ev_away["score"] == 0:
                continue
            game_date = (event.get("date") or "")[:10]
            winner = _normalize_team_abbr(ev_home["abbr"]) if ev_home["score"] > ev_away["score"] else _normalize_team_abbr(ev_away["abbr"])
            meetings.append({
                "date": game_date,
                "home": _normalize_team_abbr(ev_home["abbr"]),
                "away": _normalize_team_abbr(ev_away["abbr"]),
                "home_score": ev_home["score"],
                "away_score": ev_away["score"],
                "winner": winner,
            })
        # Sort descending by date, take most recent
        meetings.sort(key=lambda x: x.get("date", ""), reverse=True)
        return meetings[:limit]
    except Exception as e:
        logger.debug("_get_h2h_from_schedule failed", error=str(e))
        return []


def get_game_prediction_service() -> GamePredictionService:
    return GamePredictionService()

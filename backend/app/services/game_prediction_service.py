"""
Game Prediction Service - Evaluates today's NBA games and predicts likely winner.
Uses team-level metrics (def/off ranks, pace, PPG), matchup advantages, and LLM for explanations.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any
from datetime import date, datetime
import re as _re
import structlog
from .context_collector import ContextCollector
from .team_stats_service import TeamStatsService
from .cache_service import get_cache_service
from .nba_api_service import NBADataService

logger = structlog.get_logger()

# Home court advantage as win probability boost (e.g. 0.52 -> 52% base for home)
HOME_COURT_ADVANTAGE = 0.04


def _get_teams_by_abbr() -> Dict[str, Dict[str, Any]]:
    """Return map of uppercase abbreviation -> {id, full_name, abbreviation}."""
    teams = NBADataService.fetch_all_teams() or []
    out = {}
    for t in teams:
        abbr = (t.get("abbreviation") or "").strip().upper()
        if abbr:
            out[abbr] = {"id": t.get("id"), "full_name": t.get("full_name"), "abbreviation": abbr}
    return out


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

        from .espn_api_service import get_espn_service
        espn = get_espn_service()
        date_str = target_date.strftime("%Y%m%d")
        scoreboard = espn.get_scoreboard(date=date_str)
        if not scoreboard or not isinstance(scoreboard.get("events"), list):
            logger.warning("No scoreboard events for date", date=target_date.isoformat())
            self.cache.set(cache_key, [], ttl=3600)
            return []

        teams_by_abbr = _get_teams_by_abbr()
        season = "2025-26"
        def_ranks = ContextCollector._calculate_defensive_ranks(season)
        off_ranks = ContextCollector._calculate_offensive_ranks(season)
        if not def_ranks and not off_ranks:
            def_fb, off_fb = ContextCollector._calculate_team_ranks_from_player_stats(season)
            if not def_ranks:
                def_ranks = def_fb or {}
            if not off_ranks:
                off_ranks = off_fb or {}

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

                home_team = teams_by_abbr.get(home_abbr)
                away_team = teams_by_abbr.get(away_abbr)
                home_id = int(home_team["id"]) if home_team and home_team.get("id") is not None else None
                away_id = int(away_team["id"]) if away_team and away_team.get("id") is not None else None

                home_def = def_ranks.get(home_id, {}) if home_id else {}
                home_off = off_ranks.get(home_id, {}) if home_id else {}
                away_def = def_ranks.get(away_id, {}) if away_id else {}
                away_off = off_ranks.get(away_id, {}) if away_id else {}

                home_stats = self._team_stats.get_team_stats(home_abbr)
                away_stats = self._team_stats.get_team_stats(away_abbr)
                home_ppg = getattr(home_stats, "ppg", 112.5) or 112.5
                away_ppg = getattr(away_stats, "ppg", 112.5) or 112.5
                home_pace = getattr(home_stats, "pace", 100.0) or 100.0
                away_pace = getattr(away_stats, "pace", 100.0) or 100.0

                prob_home = _win_probability_from_ranks(
                    home_off.get("pts"), home_def.get("pts"),
                    away_off.get("pts"), away_def.get("pts"),
                    home_ppg, away_ppg,
                )
                prob_away = 1.0 - prob_home
                predicted_winner_abbr = home_abbr if prob_home >= 0.5 else away_abbr
                predicted_winner_name = (home_team or {}).get("full_name") or home_abbr if predicted_winner_abbr == home_abbr else (away_team or {}).get("full_name") or away_abbr

                key_adv = _key_advantages(
                    predicted_winner_abbr, home_abbr, away_abbr,
                    home_off, home_def, away_off, away_def,
                    home_ppg, away_ppg, home_pace, away_pace,
                )
                key_advantage_summary = " and ".join(key_adv) if key_adv else "balanced matchup"

                # Optional LLM summary (can be sync or async; keep short for list view)
                llm_summary = self._generate_prediction_summary(
                    home_abbr, away_abbr,
                    predicted_winner_abbr, round(prob_home * 100 if predicted_winner_abbr == home_abbr else prob_away * 100),
                    key_advantage_summary,
                    home_ppg, away_ppg, home_pace, away_pace,
                )

                event_date = event.get("date") or ""
                predictions.append({
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
                    "outlook_summary": llm_summary,
                    "game_time_utc": event_date,
                    "home_off_rank_pts": home_off.get("pts"),
                    "home_def_rank_pts": home_def.get("pts"),
                    "away_off_rank_pts": away_off.get("pts"),
                    "away_def_rank_pts": away_def.get("pts"),
                    "home_ppg": home_ppg,
                    "away_ppg": away_ppg,
                    "home_pace": home_pace,
                    "away_pace": away_pace,
                })
            except Exception as e:
                logger.warning("Failed to build prediction for game", game_id=event.get("id"), error=str(e))
                continue

        self.cache.set(cache_key, predictions, ttl=86400)
        return predictions

    def get_game_prediction_detail(self, game_id: str, target_date: Optional[date] = None) -> Optional[Dict[str, Any]]:
        """Get full prediction and detail for one game (for game detail page)."""
        target_date = target_date or date.today()
        cache_key = f"game_prediction_detail:{game_id}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        predictions = self.get_todays_predictions(target_date)
        one = next((p for p in predictions if p["gameId"] == game_id), None)
        if not one:
            return None

        season = "2025-26"
        home_id = one.get("home_team_id")
        away_id = one.get("away_team_id")
        home_abbr = one["home"]
        away_abbr = one["away"]

        # --- Full rank data ---
        def_ranks = ContextCollector._calculate_defensive_ranks(season) or {}
        off_ranks = ContextCollector._calculate_offensive_ranks(season) or {}
        if not def_ranks and not off_ranks:
            def_fb, off_fb = ContextCollector._calculate_team_ranks_from_player_stats(season)
            def_ranks = def_fb or {}
            off_ranks = off_fb or {}
        pace_ranks = ContextCollector._calculate_pace_ranks(season) or {}
        pos_ranks = ContextCollector._calculate_position_defensive_ranks(season) or {}

        home_def_full = def_ranks.get(home_id, {}) if home_id else {}
        away_def_full = def_ranks.get(away_id, {}) if away_id else {}
        home_off_full = off_ranks.get(home_id, {}) if home_id else {}
        away_off_full = off_ranks.get(away_id, {}) if away_id else {}
        home_pace_data = pace_ranks.get(home_id, {}) if home_id else {}
        away_pace_data = pace_ranks.get(away_id, {}) if away_id else {}

        # Position defense: how each team defends each position
        positions = ["PG", "SG", "SF", "PF", "C"]
        home_pos_defense = {}
        away_pos_defense = {}
        for pos in positions:
            pos_data = pos_ranks.get(pos, {})
            if home_id:
                home_pos_defense[pos] = pos_data.get(home_id, {})
            if away_id:
                away_pos_defense[pos] = pos_data.get(away_id, {})

        # --- Key players ---
        home_key_players = _get_team_key_players(home_id, season)
        away_key_players = _get_team_key_players(away_id, season)

        # --- H2H history ---
        h2h_games = _get_h2h_from_schedule(home_id, away_id, home_abbr, away_abbr, season)
        h2h_wins_home = sum(1 for g in h2h_games if g.get("winner") == home_abbr)
        h2h_wins_away = len(h2h_games) - h2h_wins_home

        # Build extended outlook for detail page (longer LLM summary)
        extended_outlook = self._generate_game_outlook(
            home_abbr, away_abbr,
            one["predicted_winner"],
            one["win_probability_home"] if one["predicted_winner"] == home_abbr else one["win_probability_away"],
            one["key_advantage_summary"],
            one.get("home_ppg"), one.get("away_ppg"), one.get("home_pace"), one.get("away_pace"),
            one.get("home_off_rank_pts"), one.get("home_def_rank_pts"),
            one.get("away_off_rank_pts"), one.get("away_def_rank_pts"),
        )

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
        }
        self.cache.set(cache_key, one, ttl=86400)
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
            prompt = (
                f"In one short sentence, why might {winner_abbr} win today's NBA game vs their opponent? "
                f"Game: {away_abbr} @ {home_abbr}. Predicted winner: {winner_abbr} ({win_pct}% win probability). "
                f"Key statistical advantages: {key_advantage}. Home PPG: {home_ppg:.1f}, Away PPG: {away_ppg:.1f}. "
                f"Pace: {home_pace:.1f} vs {away_pace:.1f}. Reply with only one concise sentence, no prefix."
            )
            result = gen._generate_simple(prompt)
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
    ) -> str:
        """Longer LLM-generated outlook for game detail page."""
        try:
            from .rationale_generator import get_rationale_generator
            gen = get_rationale_generator()
            if not gen.is_available():
                return (
                    f"The model favors {winner_abbr} with a {win_pct:.0f}% win probability. "
                    f"Key factors: {key_advantage}. Use the team comparison and defensive matchup sections below for details."
                )
            prompt = (
                f"Write a short paragraph (2-4 sentences) explaining the game outlook for today's NBA game: {away_abbr} @ {home_abbr}. "
                f"Predicted winner: {winner_abbr} ({win_pct:.0f}% win probability). "
                f"Key statistical advantages: {key_advantage}. "
                f"Home team PPG: {home_ppg or 'N/A'}, Away team PPG: {away_ppg or 'N/A'}. "
                f"Pace: Home {home_pace or 'N/A'}, Away {away_pace or 'N/A'}. "
                f"Offensive ranks (1=best): Home {home_off_pts}, Away {away_off_pts}. Defensive ranks (1=best): Home {home_def_pts}, Away {away_def_pts}. "
                f"Be concise and focus on why the model predicts this outcome. No bullet points."
            )
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
                    m_raw = g.get("min")
                    if m_raw is None:
                        continue
                    try:
                        mins_vals.append(float(str(m_raw).split(":")[0]))
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
        return results[:limit]
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
            pair = {ev_home["abbr"], ev_away["abbr"]}
            if not ({home_abbr, away_abbr} == pair or {home_abbr.upper(), away_abbr.upper()} == pair):
                continue
            # Only include completed games (score > 0)
            if ev_home["score"] == 0 and ev_away["score"] == 0:
                continue
            game_date = (event.get("date") or "")[:10]
            winner = ev_home["abbr"] if ev_home["score"] > ev_away["score"] else ev_away["abbr"]
            meetings.append({
                "date": game_date,
                "home": ev_home["abbr"],
                "away": ev_away["abbr"],
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

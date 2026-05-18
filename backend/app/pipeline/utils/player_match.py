"""Match ESPN box score athletes to NBA player IDs."""
from __future__ import annotations
import re
from typing import Any, Dict, List, Optional, Tuple


def _norm_name(name: str) -> str:
    s = (name or "").lower().strip()
    s = re.sub(r"[^a-z\s]", "", s)
    return " ".join(s.split())


def build_name_team_index(players: List[Dict[str, Any]]) -> Dict[Tuple[str, str], int]:
    """(normalized_name, team_abbr) -> nba player_id"""
    teams = {}
    for p in players:
        tid = p.get("team_id")
        abbr = (p.get("team_abbreviation") or p.get("team") or "").upper()
        if tid and abbr:
            teams[int(tid)] = abbr

    index: Dict[Tuple[str, str], int] = {}
    for p in players:
        pid = p.get("id")
        if not pid:
            continue
        name = _norm_name(p.get("full_name") or p.get("name") or "")
        if not name:
            continue
        tid = p.get("team_id")
        abbr = (p.get("team_abbreviation") or "").upper()
        if not abbr and tid:
            abbr = teams.get(int(tid), "")
        if abbr:
            index[(name, abbr)] = int(pid)
        index[(name, "")] = int(pid)
    return index


def match_espn_athlete(
    athlete: Dict[str, Any],
    team_abbr: str,
    index: Dict[Tuple[str, str], int],
    espn_to_nba: Optional[Dict[str, int]] = None,
) -> Optional[int]:
    espn_id = str(athlete.get("id") or "")
    if espn_to_nba and espn_id in espn_to_nba:
        return espn_to_nba[espn_id]
    display = athlete.get("displayName") or athlete.get("shortName") or ""
    name = _norm_name(display)
    abbr = (team_abbr or "").upper()
    if (name, abbr) in index:
        return index[(name, abbr)]
    if (name, "") in index:
        return index[(name, "")]
    parts = name.split()
    if len(parts) >= 2:
        last_first = f"{parts[-1]} {' '.join(parts[:-1])}"
        if (last_first, abbr) in index:
            return index[(last_first, abbr)]
    return None

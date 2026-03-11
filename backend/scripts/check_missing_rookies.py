#!/usr/bin/env python3
"""
Run through NBA CommonAllPlayers (current season) and ESPN rosters to find
players missing from the app (e.g. rookies). Outputs suggested rookie_merge.json
entries. Run from repo root: cd backend && PYTHONPATH=. python scripts/check_missing_rookies.py
"""
from __future__ import annotations

import json
import re
import sys

# Run from backend so app is importable
sys.path.insert(0, ".")

from app.services.nba_api_service import NBADataService


# Team abbrs that ESPN uses but README wants normalized (rookie_merge.json)
_ESPN_ABBR_TO_README = {"NO": "NOP", "SA": "SAS", "NY": "NYK", "GS": "GSW", "WSH": "WAS", "UTAH": "UTA"}


def _normalize_name(s: str) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", s.strip().lower())


def _name_variants(name_lower: str):
    """Yield name variants for matching (e.g. 'k.j. simpson' -> 'kj simpson')."""
    yield name_lower
    no_dots = name_lower.replace(".", "").replace(" ", " ")
    if no_dots != name_lower:
        yield no_dots


def main() -> None:
    # 1) NBA team_id -> abbreviation
    id_to_abbr: dict[int, str] = {}
    for abbr, tid in NBADataService.ESPN_ABBR_TO_NBA_ID.items():
        if tid not in id_to_abbr:
            id_to_abbr[tid] = abbr

    # 2) CommonAllPlayers (current season) — same scheme as nba_api_service
    nba_players: list[dict] = []
    name_to_nba: dict[str, tuple[int, int | None]] = {}  # name_lower -> (person_id, team_id)

    try:
        from nba_api.stats.endpoints import commonallplayers

        cap = commonallplayers.CommonAllPlayers(is_only_current_season=1, timeout=25)
        data = cap.get_dict()
        result_sets = data.get("resultSets", [])
        if result_sets:
            headers = result_sets[0].get("headers", [])
            rows = result_sets[0].get("rowSet", [])
            try:
                person_id_idx = headers.index("PERSON_ID")
                display_idx = headers.index("DISPLAY_FIRST_LAST")
                team_id_idx = headers.index("TEAM_ID")
            except ValueError:
                person_id_idx, display_idx, team_id_idx = 0, 2, 8

            for row in rows:
                if len(row) <= max(person_id_idx, display_idx, team_id_idx):
                    continue
                person_id = row[person_id_idx]
                full_name = (row[display_idx] or "Unknown").strip()
                team_id = row[team_id_idx] if team_id_idx < len(row) else None
                if not person_id:
                    continue
                nba_players.append({"id": person_id, "full_name": full_name, "team_id": team_id})
                key = _normalize_name(full_name)
                if key and key not in name_to_nba:
                    name_to_nba[key] = (person_id, team_id)
                for v in _name_variants(key):
                    if v and v not in name_to_nba:
                        name_to_nba[v] = (person_id, team_id)
    except Exception as e:
        print("CommonAllPlayers fetch failed:", e, file=sys.stderr)
        nba_players = []
        name_to_nba = {}

    nba_ids = {p["id"] for p in nba_players}
    nba_on_roster = [p for p in nba_players if p.get("team_id")]

    # 3) App player list (includes rookie_merge)
    app_players = NBADataService.fetch_all_players_including_rookies() or []
    app_ids = {p.get("id") for p in app_players if p.get("id")}
    app_names_lower = {_normalize_name(p.get("full_name") or "") for p in app_players}
    app_names_lower = {n for n in app_names_lower if n}

    # 4) Missing by ID: in CommonAllPlayers (on roster) but not in app
    suggested_by_id: list[dict] = []
    for p in nba_on_roster:
        pid = p["id"]
        if pid in app_ids:
            continue
        abbr = id_to_abbr.get(p.get("team_id") or 0) or ""
        abbr = _ESPN_ABBR_TO_README.get(abbr, abbr)
        suggested_by_id.append({
            "full_name": p["full_name"],
            "nba_id": pid,
            "team_abbr": abbr,
        })

    # 5) Missing by name: on ESPN roster but not in app
    espn_name_to_team, _ = NBADataService._fetch_espn_roster_mapping()
    suggested_by_espn: list[dict] = []
    for name_lower, team_id in espn_name_to_team.items():
        if not name_lower or name_lower in app_names_lower:
            continue
        abbr = id_to_abbr.get(team_id, "")
        abbr = _ESPN_ABBR_TO_README.get(abbr, abbr)
        nba_id = None
        for v in _name_variants(name_lower):
            if v in name_to_nba:
                nba_id, _ = name_to_nba[v]
                break
        suggested_by_espn.append({
            "full_name": name_lower.title(),
            "nba_id": nba_id or "LOOKUP",
            "team_abbr": abbr,
        })

    # 6) Report
    print("=== Missing from app (in CommonAllPlayers current season, on roster) ===")
    print(f"Count: {len(suggested_by_id)}")
    if suggested_by_id:
        print(json.dumps(suggested_by_id, indent=2))

    print("\n=== Missing from app (on ESPN roster, not in app) ===")
    print(f"Count: {len(suggested_by_espn)}")
    if suggested_by_espn:
        print(json.dumps(suggested_by_espn, indent=2))

    # Ready-to-merge: only entries with integer nba_id that are not already in app (dedupe by id)
    seen_ids = set(app_ids)
    to_merge: list[dict] = []
    for e in suggested_by_id:
        if e["nba_id"] not in seen_ids:
            to_merge.append(e)
            seen_ids.add(e["nba_id"])
    for e in suggested_by_espn:
        if isinstance(e["nba_id"], int) and e["nba_id"] not in seen_ids:
            to_merge.append(e)
            seen_ids.add(e["nba_id"])

    if to_merge:
        print("\n=== Suggested rookie_merge.json entries (add to backend/app/data/rookie_merge.json) ===")
        print(json.dumps(to_merge, indent=2))


if __name__ == "__main__":
    main()

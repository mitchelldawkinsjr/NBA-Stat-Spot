"""Basketball-logic validation for player box-score rows before analytics.

Invalid rows are still stored (quarantine-in-place) with validation_status set
so aggregates can exclude them without dropping evidence.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


class BoxScoreValidator:
    STATUS_VALID = "valid"
    STATUS_WARNING = "warning"
    STATUS_INVALID = "invalid"

    MAX_MINUTES_WITH_OT = 60.0  # regulation + OT allowance

    COUNTING_KEYS = (
        "points",
        "rebounds",
        "assists",
        "steals",
        "blocks",
        "turnovers",
        "three_pointers_made",
        "field_goals_made",
        "field_goals_attempted",
        "free_throws_made",
    )

    @classmethod
    def validate_player_record(cls, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a normalized player box record.

        Accepts either DB column names (points, rebounds, …) or short keys
        (pts, reb, …). Returns {status, failures}.
        """
        failures: List[str] = []
        warnings: List[str] = []

        fgm = cls._int(record, "field_goals_made", "fgm")
        fga = cls._int(record, "field_goals_attempted", "fga")
        tpm = cls._int(record, "three_pointers_made", "tpm", "three_point_field_goals_made")
        ftm = cls._int(record, "free_throws_made", "ftm")
        points = cls._int(record, "points", "pts")
        reb = cls._int(record, "rebounds", "reb")
        ast = cls._int(record, "assists", "ast")
        stl = cls._int(record, "steals", "stl")
        blk = cls._int(record, "blocks", "blk")
        tov = cls._int(record, "turnovers", "tov")

        if fga is not None and fgm is not None and fgm > fga:
            failures.append(f"FGM {fgm} > FGA {fga}")
        if fgm is not None and tpm is not None and tpm > fgm:
            failures.append(f"3PM {tpm} > FGM {fgm}")

        for label, val in (
            ("points", points),
            ("rebounds", reb),
            ("assists", ast),
            ("steals", stl),
            ("blocks", blk),
            ("turnovers", tov),
            ("three_pointers_made", tpm),
            ("field_goals_made", fgm),
            ("field_goals_attempted", fga),
            ("free_throws_made", ftm),
        ):
            if val is not None and val < 0:
                failures.append(f"negative {label}")

        # Points identity only when FG fields are present (sparse ESPN ingest often omits them).
        has_fg = cls._has_any(record, "field_goals_made", "fgm", "field_goals_attempted", "fga")
        if has_fg and points is not None and fgm is not None and tpm is not None:
            ftm_use = ftm if ftm is not None else 0
            expected = 2 * (fgm - tpm) + 3 * tpm + ftm_use
            if points != expected:
                failures.append(f"points {points} != computed {expected}")

        minutes = cls.parse_minutes(
            record.get("minutes_played")
            if record.get("minutes_played") is not None
            else record.get("minutes")
        )
        if minutes is not None and minutes > cls.MAX_MINUTES_WITH_OT:
            failures.append(f"minutes {minutes} exceed possible game duration")

        if minutes is not None and minutes <= 0 and (points or 0) > 0:
            warnings.append("zero minutes with positive points")

        status = cls.STATUS_VALID
        if failures:
            status = cls.STATUS_INVALID
        elif warnings:
            status = cls.STATUS_WARNING

        return {"status": status, "failures": failures + warnings}

    @classmethod
    def parse_minutes(cls, minutes: Any) -> Optional[float]:
        if minutes is None or minutes == "":
            return None
        if isinstance(minutes, (int, float)):
            return float(minutes)
        if isinstance(minutes, str):
            s = minutes.strip()
            if ":" in s:
                parts = s.split(":", 1)
                try:
                    mins = float(parts[0])
                    secs = float(parts[1]) if len(parts) > 1 else 0.0
                    return round(mins + secs / 60.0, 2)
                except ValueError:
                    return None
            try:
                return float(s)
            except ValueError:
                return None
        return None

    @classmethod
    def _has_any(cls, record: Dict[str, Any], *keys: str) -> bool:
        for k in keys:
            if k in record and record[k] is not None:
                return True
        return False

    @classmethod
    def _int(cls, record: Dict[str, Any], *keys: str) -> Optional[int]:
        for k in keys:
            if k not in record or record[k] is None:
                continue
            try:
                return int(record[k])
            except (TypeError, ValueError):
                return 0
        return None


def validate_and_serialize(record: Dict[str, Any]) -> Tuple[str, Optional[str]]:
    """Return (status, failures_json_or_none) for DB columns."""
    import json

    result = BoxScoreValidator.validate_player_record(record)
    failures = result.get("failures") or []
    failures_json = json.dumps(failures) if failures else None
    return result["status"], failures_json

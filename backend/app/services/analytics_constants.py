"""Shared analytics agent constants."""

FORMULA_VERSION = "v1-stats-calculator"

STAT_TYPES = ["pts", "reb", "ast", "tpm"]

WINDOWS = {
    "l5": 5,
    "l10": 10,
    "l20": 20,
    "season": None,
}

DISPLAY_TYPE = {"pts": "PTS", "reb": "REB", "ast": "AST", "tpm": "3PM", "pra": "PRA"}

"""Pipeline feature flags and settings."""
import os


def _env_bool(key: str, default: bool = False) -> bool:
    val = (os.getenv(key) or "").strip().lower()
    if not val:
        return default
    return val in ("1", "true", "yes", "on")


def pipeline_read_stats() -> bool:
    return _env_bool("PIPELINE_READ_STATS", True)


def pipeline_read_dashboard() -> bool:
    return _env_bool("PIPELINE_READ_DASHBOARD", True)


def pipeline_shadow_build() -> bool:
    return _env_bool("PIPELINE_SHADOW_BUILD", True)


def pipeline_auto_publish() -> bool:
    return _env_bool("PIPELINE_AUTO_PUBLISH", False)

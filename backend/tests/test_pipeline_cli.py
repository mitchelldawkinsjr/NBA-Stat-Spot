"""Pipeline CLI and dry-run."""
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def test_pipeline_dry_run_exits_zero():
    env = {**dict(__import__("os").environ), "PYTHONPATH": str(BACKEND)}
    r = subprocess.run(
        [sys.executable, "-m", "app.pipeline", "run", "data_quality", "--dry-run"],
        cwd=str(BACKEND),
        env=env,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    assert "dry-run" in r.stdout.lower() or "dry-run ok" in r.stdout.lower()


def test_pipeline_jobs_registered():
    from app.pipeline.cli import JOBS

    assert "ingest_schedule" in JOBS
    assert "build_dashboard" in JOBS
    assert "settle_accuracy" in JOBS
    assert "compute_analytics" in JOBS
    assert "build_prop_evaluations" in JOBS

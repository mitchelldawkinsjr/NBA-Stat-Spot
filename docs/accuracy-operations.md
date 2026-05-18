# Accuracy Operations (AI Pick + Top Picks)

This guide documents the operational scripts and commands for:

- Backfilling historical accuracy rows
- Hybrid-filling missing Top Picks rows
- Settling accuracy for a specific date/season
- Verifying API payloads after backfill/settle

## Production server access

**`vps ssh`** takes you to the production host (interactive shell). App directory is typically **`/opt/nba-stat-spot`**. Then run `docker compose` / `docker exec` as in [Production container examples](#production-container-examples) below. See Cursor rule **`prod-vps-ssh`** for agent behavior.

## Script: `backend/scripts/backfill_accuracy_history.py`

Run from repo root unless noted.

### Local dry-run (safe preview)

```bash
cd backend
PYTHONPATH=. python3 scripts/backfill_accuracy_history.py --days 14 --top-picks --dry-run
```

### Backfill last 14 days (AI pick + optional game predictions + top picks) and settle

```bash
cd backend
PYTHONPATH=. python3 scripts/backfill_accuracy_history.py --days 14 --top-picks --settle
```

### Explicit date range (inclusive)

```bash
cd backend
PYTHONPATH=. python3 scripts/backfill_accuracy_history.py \
  --from-date 2026-03-12 --to-date 2026-03-25 \
  --top-picks --settle
```

### Top Picks-only hybrid fill (no AI pick generation)

```bash
cd backend
PYTHONPATH=. python3 scripts/backfill_accuracy_history.py \
  --from-date 2026-03-12 --to-date 2026-03-25 \
  --no-pick-of-the-day --top-picks --settle
```

### Key flags

- `--days N`: rolling window ending yesterday
- `--from-date YYYY-MM-DD --to-date YYYY-MM-DD`: explicit range
- `--no-pick-of-the-day`: skip AI pick row generation
- `--game-predictions`: include game prediction row backfill
- `--top-picks`: for each date, if no `prop_prediction_records` exist, run Top Picks generation for that date
- `--no-settle`: skip settlement pass
- `--season 2025-26`: override default season for player game logs
- `--dry-run`: print actions, no DB writes

## Admin settle endpoint

The Admin dashboard button calls the same endpoint below.

### Settle yesterday (default)

```bash
curl -X POST "https://<host>/api/v1/admin/settle-accuracy"
```

### Settle a specific date + season

```bash
curl -X POST "https://<host>/api/v1/admin/settle-accuracy?settle_date=2026-03-25&season=2025-26"
```

Expected `result` payload sections:

- `game_predictions`
- `pick_of_the_day`
- `top_picks`

## Verify output after runs

### Accuracy history for UI range

```bash
curl "https://<host>/api/v1/accuracy/history?days=14"
```

Confirm response includes:

- `top_picks.overall`
- `top_picks.by_tier`
- `top_picks.by_confidence_band`
- `top_picks.by_stat`
- `top_picks.by_direction`
- `top_picks.tier_x_stat`
- `top_picks.tier_x_direction`
- `top_picks.records`

For pipeline ingest/build/settle, see [Data Pipeline](data-pipeline.md).

## Production container examples

If running in Docker on VPS:

```bash
docker exec -it nba-stat-spot-backend \
  bash -lc 'cd /app/backend && PYTHONPATH=. python3 scripts/backfill_accuracy_history.py --days 14 --top-picks --settle'
```

For memory-constrained hosts, run one day at a time:

```bash
for d in 2026-03-12 2026-03-13 2026-03-14; do
  docker exec -it nba-stat-spot-backend \
    bash -lc "cd /app/backend && PYTHONPATH=. python3 scripts/backfill_accuracy_history.py --from-date $d --to-date $d --top-picks --settle"
done
```

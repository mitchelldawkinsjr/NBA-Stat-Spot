# Data Pipeline

The pipeline ingests NBA/ESPN data into Postgres, builds versioned dashboard snapshots, and settles accuracy—without coupling to user HTTP traffic.

## Architecture

- **Pipeline container** (`nba-stat-spot-pipeline`): runs `supercronic /app/pipeline_crontab`
- **API container**: serves reads; optional flags to read curated data

## Feature flags

| Variable | Default | Effect |
|----------|---------|--------|
| `PIPELINE_READ_STATS` | `false` | `fetch_player_game_log` prefers `player_game_stats` |
| `PIPELINE_READ_DASHBOARD` | `false` | Props endpoints read published snapshots |
| `PIPELINE_SHADOW_BUILD` | `true` | Snapshots built unpublished until admin publish |
| `PIPELINE_AUTO_PUBLISH` | `false` | Auto-publish when build + quality pass |

## CLI

```bash
cd backend
PYTHONPATH=. python -m app.pipeline run <job> [--date YYYY-MM-DD] [--season 2025-26]
PYTHONPATH=. python -m app.pipeline backfill --from-date 2026-03-01 --to-date 2026-03-14 --jobs ingest_schedule,ingest_boxscores,build_dashboard,settle_accuracy
```

Jobs: `ingest_schedule`, `ingest_boxscores`, `ingest_player_logs`, `build_dashboard`, `build_ranks`, `settle_accuracy`, `data_quality`

## Admin API

- `GET /api/v1/admin/pipeline/status`
- `POST /api/v1/admin/pipeline/publish?date=&artifact=`
- `POST /api/v1/admin/pipeline/run/{job_name}?date=&season=`

## Dashboard API

- `GET /api/v1/dashboard/home?date=` — aggregated published snapshots

## Production

```bash
docker compose -f docker-compose.prod.yml up -d pipeline
docker compose -f docker-compose.prod.yml logs -f pipeline
docker exec -it nba-stat-spot-pipeline sh -lc 'cd /app && PYTHONPATH=/app python -m app.pipeline run data_quality --dry-run'
```

Apply migrations before first run:

```bash
docker exec -it nba-stat-spot-backend alembic upgrade head
```

## Rollout

1. Deploy pipeline with flags off; verify `player_game_stats` fills.
2. `PIPELINE_READ_STATS=true`
3. Shadow build; publish via admin; `PIPELINE_READ_DASHBOARD=true`

See also [Accuracy Operations](accuracy-operations.md).

# Data Pipeline

The pipeline ingests NBA/ESPN data into Postgres, validates box scores, precomputes
analytics aggregates and prop evaluations, builds dashboard snapshots, and settles
accuracy—without coupling derived-metric math to user HTTP traffic.

## Architecture

```
ingest (schedule/box/logs)
  → BoxScoreValidator (quarantine invalid rows on player_game_stats)
  → compute_analytics → player_stat_windows + player_line_hit_rates
  → build_prop_evaluations → player_prop_evaluations
  → build_dashboard (assembles snapshots from prop rows)
  → API reads tables / published snapshots
```

- **Pipeline container** (`nba-stat-spot-pipeline`): runs `supercronic /app/pipeline_crontab`
- **API container**: serves reads from precomputed tables and optional published snapshots

## Feature flags

| Variable | Default | Effect |
|----------|---------|--------|
| `PIPELINE_READ_STATS` | `true` | `fetch_player_game_log` prefers `player_game_stats` |
| `PIPELINE_READ_DASHBOARD` | `true` | Props endpoints prefer published snapshots |
| `PIPELINE_SHADOW_BUILD` | `true` | Snapshots built unpublished until admin publish |
| `PIPELINE_AUTO_PUBLISH` | `false` | Auto-publish when build + quality pass |

Daily props / best picks also read `player_prop_evaluations` when rows exist for the date (independent of snapshot flags), with live-compute fallback.

## CLI

```bash
cd backend
PYTHONPATH=. python -m app.pipeline run <job> [--date YYYY-MM-DD] [--season 2025-26]
PYTHONPATH=. python -m app.pipeline backfill --from-date 2026-03-01 --to-date 2026-03-14 --jobs ingest_schedule,ingest_boxscores,build_dashboard,settle_accuracy
```

Jobs: `ingest_schedule`, `ingest_boxscores`, `ingest_player_logs`, `compute_analytics`, `build_prop_evaluations`, `build_dashboard`, `build_ranks`, `settle_accuracy`, `data_quality`

## Schedule (UTC)

| Time | Job |
|------|-----|
| `*/30` 23–5 | `ingest_schedule`, `ingest_boxscores` |
| `0 10` | `ingest_player_logs` |
| `5 10` | `compute_analytics` |
| `10 10` | `build_prop_evaluations` |
| `15 11` | `build_ranks` |
| `20 11` | `build_dashboard` |
| `35 11` | `settle_accuracy` |
| `40 11` | `data_quality` |

## Precomputed tables

| Table | Written by | Read by |
|-------|------------|---------|
| `player_game_stats` (+ `validation_status`) | ingest jobs | analytics, API game logs |
| `player_stat_windows` | `compute_analytics` | player trends/streaks |
| `player_line_hit_rates` | `compute_analytics` | live props L5/L10/L20 |
| `player_prop_evaluations` | `build_prop_evaluations` | daily props, best picks, dashboard |
| `dashboard_snapshots` | `build_dashboard` | dashboard home when published |

`formula_version` is currently `v1-stats-calculator` — bump and recompute when calculator rules change.

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

1. Deploy + `alembic upgrade head`.
2. Backfill analytics: `python -m app.pipeline run compute_analytics --season <current>`.
3. `python -m app.pipeline run build_prop_evaluations --date <today>`.
4. `python -m app.pipeline run build_dashboard --date <today>`.
5. Confirm API has `PIPELINE_READ_STATS=true` / `PIPELINE_READ_DASHBOARD=true` (compose defaults).
6. After quality looks good, set `PIPELINE_AUTO_PUBLISH=true` and `PIPELINE_SHADOW_BUILD=false`.

See also [Accuracy Operations](accuracy-operations.md).

# Ops Runbook (MVP)

- Env: none required (public data). Do not expose secrets.
- Rate-limits: automatic backoff and retry with jitter.
- Caching: in-memory with short TTLs (60–300s) to keep latency <3s.
- Health: /healthz endpoint returns 200 when app is ready.
- Logs: structured JSON to stdout; include request id and latency.

## Common Issues
- nba_api upstream slow → rely on cache; increase TTL temporarily.
- Schedule endpoint down → dashboard falls back to league-wide suggestions.

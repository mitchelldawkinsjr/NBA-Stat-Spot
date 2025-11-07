# Operations Runbook

**Purpose**: Quick reference guide for operations, troubleshooting, and common issues in production.

**Use this guide when**:
- Debugging production issues
- Understanding system behavior and configuration
- Configuring caching and rate limits
- Checking health endpoints
- Responding to incidents

---

- Env: none required (public data). Do not expose secrets.
- Rate-limits: automatic backoff and retry with jitter.
- Caching: in-memory with short TTLs (60–300s) to keep latency <3s.
- Health: /healthz endpoint returns 200 when app is ready.
- Logs: structured JSON to stdout; include request id and latency.

## Common Issues
- nba_api upstream slow → rely on cache; increase TTL temporarily.
- Schedule endpoint down → dashboard falls back to league-wide suggestions.

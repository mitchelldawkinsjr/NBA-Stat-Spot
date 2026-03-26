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

## Admin UI and API

- **Backend** (`ADMIN_SECRET`): When set, all `/api/v1/admin/*` routes require header `X-Admin-Secret: <same value>` or `Authorization: Bearer <same value>`.
- **Frontend** (`VITE_ADMIN_SECRET`): Set at **build time** to the **same string** as `ADMIN_SECRET`. Then:
  - Visiting `/admin` shows a password screen until the user enters that value (stored in `sessionStorage` for the browser session).
  - All `apiFetch` calls to `/api/v1/admin/*` automatically send `X-Admin-Secret`.
- If `VITE_ADMIN_SECRET` is unset, the admin page has no password gate and no admin header is sent (matches a backend with no `ADMIN_SECRET` for local dev).
- **Lock admin**: Button on the admin dashboard clears the session gate and returns home.

## Accuracy Commands

Use the dedicated command guide for backfill and settlement operations:

- [Accuracy Operations](accuracy-operations.md)

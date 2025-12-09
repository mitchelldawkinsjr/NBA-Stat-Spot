# Mitch Cloud Migration & Deployment Playbook

Living document that consolidates every selected decision inside Mitch Cloud so migrations from any external app can be landed using the exact standards already codified in the repo. Treat this as the operational baseline; cross‑reference the linked source files for implementation detail.

## Canonical References

- Platform overview: [README.md](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/README.md), [docs/architecture.md](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/docs/architecture.md), [docs/project-structure.md](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/docs/project-structure.md)
- Runtime procedures: [docs/deployment.md](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/docs/deployment.md), [docs/deployment-workflow.md](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/docs/deployment-workflow.md)
- Infrastructure: [docs/vps-environment-setup.md](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/docs/vps-environment-setup.md), [docker-compose.infrastructure.yml](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/docker-compose.infrastructure.yml)
- Client orchestration: [docs/multi-repo-deployment.md](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/docs/multi-repo-deployment.md), [docs/docker-app-deployment.md](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/docs/docker-app-deployment.md), [clients/README.md](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/clients/README.md)
- Automation: [.github/workflows/](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/tree/main/.github/workflows)
- Backups & resiliency: [docs/duplicati-backup-setup.md](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/docs/duplicati-backup-setup.md), [docs/monitoring-alerts-setup.md](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/docs/monitoring-alerts-setup.md), [docs/custom-configurations.md](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/docs/custom-configurations.md)

## 1. Platform Snapshot

**Core stack.** FastAPI backend ([backend/](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/tree/main/backend)), React/Vite frontend ([frontend/](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/tree/main/frontend)), all packaged through [docker-compose.yml](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/docker-compose.yml) on the shared `360ws-network`. Infrastructure services (Portainer, Netdata, Uptime Kuma, n8n, Duplicati, Ollama, Nginx Proxy Manager) live in [docker-compose.infrastructure.yml](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/docker-compose.infrastructure.yml) and run continuously on the VPS.

**Compute baseline.** Production VPS must meet the spec from [docs/vps-environment-setup.md](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/docs/vps-environment-setup.md) (≥4 vCPU, 8 GB RAM, 100 GB SSD, Ubuntu 22.04 or Debian 12) with Docker + Compose installed and `/data` mounted for persistent volumes (database dirs, WordPress content, backups, etc.).

**Networks.** All containers are isolated by concern-specific bridge networks (`management_network`, `monitoring_network`, `automation_network`, `storage_network`, `ai_network`, `proxy_network`, plus shared `360ws-network`). Client workloads attach to `360ws-network` so they can be proxied without exposing host ports unnecessarily.

**Context tagging.** Containers are labeled with `com.360ws.*` keys so the backend context router can filter services (see [backend/app/routers/contexts.py](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/backend/app/routers/contexts.py)). Preserve labels when adding new services so UI filtering, analytics, and monitoring remain accurate.

**Persistence & backups.** Everything under `/data` is considered source of truth for runtime state. Duplicati (from [docker-compose.infrastructure.yml](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/docker-compose.infrastructure.yml)) snapshots Docker volumes + configs to Backblaze B2 nightly, orchestrated by n8n pre/post tasks (Section 7 in [docs/architecture.md](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/docs/architecture.md)). WordPress backups additionally flow through UpdraftPlus/MainWP. The GitHub Actions job [.github/workflows/backup-verification.yml](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/.github/workflows/backup-verification.yml) validates the B2 bucket (`mitchcloud-backups` by default) every morning at 10 AM UTC.

## 2. Source Control & Repo Norms

**Main repository.** Houses core app, infra compose files, documentation, and automation. Treat `main` branch as deployable: deployments only occur when PRs merge into `main` or when workflows are triggered manually (see [docs/deployment-workflow.md](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/docs/deployment-workflow.md)). Direct pushes do not deploy—this is intentional.

**Client repositories.** Every WordPress site or custom Docker app lives in its own repo derived from the templates under [clients/templates/](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/tree/main/clients/templates). The templates already include Docker Compose stacks, env samples, and GitHub Actions workflows so deployment posture stays consistent. Track every onboarded client in [clients/registry.json](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/clients/registry.json); the backend APIs read this registry when surfacing environments.

**Helper tooling.** Use [scripts/create-client-repo.sh](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/scripts/create-client-repo.sh) to bootstrap new repos (WordPress or docker-app) with the standard layout, secrets placeholders, and workflow wiring.

**.gitignore & secrets.** Only commit infrastructure code and templates. Environment files (`.env`), generated backups, and `/data/**` never leave the VPS. Follow the GitHub hardening steps captured in Section 14.1 of [docs/architecture.md](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/docs/architecture.md) (SSH-only auth, branch protection, required PR reviews).

## 3. GitHub Actions Automation

| Workflow | Scope | Trigger | Required secrets |
| --- | --- | --- | --- |
| [.github/workflows/ci.yml](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/.github/workflows/ci.yml) | Backend + frontend build sanity | Every PR + push to `main` | none (uses default runners) |
| [.github/workflows/deploy-app.yml](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/.github/workflows/deploy-app.yml) | Core frontend/backend stack | PR merged to `main` touching app code, or manual dispatch | `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`, optional `SLACK_WEBHOOK` |
| [.github/workflows/deploy-infrastructure.yml](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/.github/workflows/deploy-infrastructure.yml) | Portainer, Netdata, n8n, Duplicati, Ollama, Nginx Proxy | PR merged to `main` touching infra compose or manual dispatch | Same as above |
| [.github/workflows/deploy.yml](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/.github/workflows/deploy.yml) | General-purpose deploy hook (kept for backward compat) | Any merged PR to `main` or manual dispatch | Same as above |
| [.github/workflows/backup-verification.yml](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/.github/workflows/backup-verification.yml) | Daily Backblaze B2 verification | 10 AM UTC cron + manual dispatch | `B2_APPLICATION_KEY_ID`, `B2_APPLICATION_KEY`, optional `SLACK_WEBHOOK` |

**Behavioral guardrails.** Each deploy job contains `if: github.event.pull_request.merged == true || github.event_name == 'workflow_dispatch'`, so merges and manual runs are the only ways to ship. Health checks curl the backend (`:8000/health`) and frontend (`:3000`) before notifying Slack.

**Client repo workflows.** Templates under [clients/templates](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/tree/main/clients/templates) (see each template’s `.github/workflows/deploy.yml`) mirror the same trigger logic: merge to `main` or manual dispatch, then SSH into the VPS, clone/update under `/opt/360ws/clients/<type>/<repo>`, run `docker-compose up -d --build`, and execute health/content sync toggles (WordPress workflows also handle content XML and DB exports).

## 4. Environment Baseline & Provisioning

1. **Prep the VPS** using [docs/vps-environment-setup.md](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/docs/vps-environment-setup.md): install Docker/Compose, build the `/data` directory tree (AI, automation, monitoring, databases, wordpress, nginx, backups, etc.), and open only the required ports (80/443/81 for Nginx Proxy Manager, 8200 for Duplicati, etc.).
2. **Clone repo** into `/opt/360ws`, ensure ownership is set to the deployment user, and configure backend & frontend `.env` files (`backend/.env` requires Docker socket path, CORS origins, Netdata URL, Backblaze + MainWP + n8n credentials; `frontend/.env` needs `VITE_API_URL`).
3. **Bring up infrastructure services** with `docker-compose -f docker-compose.infrastructure.yml up -d`, then deploy the main stack via `docker-compose up -d` or rely on the GitHub Actions workflows.
4. **Reverse proxy** all public services through Nginx Proxy Manager ([docker-compose.infrastructure.yml](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/docker-compose.infrastructure.yml) already publishes 80/443/81). SSL issuance uses Let’s Encrypt (refer to [docs/ssl-certificates-setup.md](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/docs/ssl-certificates-setup.md)).
5. **Monitoring + alerts**: Add each service to Uptime Kuma, configure Netdata alerts & Slack hooks per [docs/monitoring-alerts-setup.md](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/docs/monitoring-alerts-setup.md), and verify GitHub Action notifications flow to the same workspace.

## 5. Migration Pipeline for New Apps

1. **Assess readiness**
   - Containerize the workload (Dockerfile + [docker-compose.yml](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/docker-compose.yml)).
   - Identify data directories and ensure they map to bind mounts inside `/data/<app>` so Duplicati can capture them.
   - Define health endpoints for GitHub Actions to probe post-deploy.
2. **Pick repo type**
   - **WordPress site**: copy [clients/templates/wordpress/](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/tree/main/clients/templates/wordpress), fill `.env`, update compose ports, commit the template README, and set up optional content/db export files for GUI-made changes.
   - **Generic Docker app**: copy [clients/templates/docker-app/](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/tree/main/clients/templates/docker-app), customize Dockerfile + compose, add `.env`. Use the included workflow to handle deployment.
3. **Wire secrets**: In the new GitHub repo, add `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`, and optional `SLACK_WEBHOOK`. For workloads that need third-party credentials, inject them through repo-level variables or the `.env` file that stays on the VPS.
4. **Register client**: Update [clients/registry.json](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/clients/registry.json) (or call `POST /api/v1/wordpress/sites/create` / `POST /api/v1/apps/create`) so the dashboard can surface the new workload and analytics/backup policies know about it.
5. **Deploy via PR**: Push to a feature branch, open a PR, and merge into `main`. The workflow will SSH into `/opt/360ws/clients/...`, pull the repo, rebuild, run health checks, and emit Slack notifications. Manual dispatch is available for emergency redeploys.
6. **Post-deploy hooks**:
   - Add monitors in Uptime Kuma for the new app domain/port.
   - If applicable, configure UpdraftPlus/MainWP via backend endpoints so WordPress backups route to Backblaze B2 (`UPDRAFTPLUS_*` env vars).
   - Document any client-specific overrides inside [docs/custom-configurations.md](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/docs/custom-configurations.md).

## 6. Operational Norms

- **Health verification**: Always confirm `/api/v1/services`, `/health`, and the frontend load after deployments (the workflows already curl these, but manual verification is recommended for migrations).
- **Monitoring**: Netdata covers system metrics, Uptime Kuma tracks uptime, Portainer offers ad-hoc container introspection, and Slack receives deployment/backup alerts.
- **Backups**: Four Duplicati jobs (databases @1 AM, Docker volumes @2 AM, WordPress @3 AM, configs @4 AM) plus n8n orchestration (12:30 AM pre-tasks, post-upload verification). Keep Backblaze bucket usage aligned between `.env` (`B2_BUCKET_NAME`, default `360ws-backups`) and the backup verification workflow (`mitchcloud-backups`)—update both if you rename.
- **Branch protection**: Enforce reviews + CI success on `main` so deployments remain intentional (see [docs/deployment-workflow.md](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/docs/deployment-workflow.md)).

## 7. Security & Secrets

- Store SSH material in GitHub Secrets only (`VPS_SSH_KEY` is the private key; ensure the public half lives in `/root/.ssh/authorized_keys` on the VPS). Rotate keys whenever staff changes.
- Never commit `.env` files. Backend env template documents all required keys (Netdata URL, Backblaze creds, MainWP, UpdraftPlus, VPS host/user for workflows).
- For Slack notifications, use an incoming webhook stored as `SLACK_WEBHOOK`. Keep this optional but recommended for situational awareness across contexts.
- Nginx Proxy Manager should be fronted with strong credentials and, if possible, IP restrictions; else ensure it is only exposed via HTTPS with Let’s Encrypt certs (see [docs/ssl-certificates-setup.md](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/docs/ssl-certificates-setup.md)).

## 8. Disaster Recovery & Validation

- **Restore drills**: Follow the DR steps in [docs/duplicati-backup-setup.md](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/docs/duplicati-backup-setup.md) and Section 7 of [docs/architecture.md](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/docs/architecture.md) (RTO/RPO guidance) to rehearse restoring `/data` + Docker stacks onto a fresh VPS.
- **Backup verification**: Monitor the daily GitHub Actions job; any failure triggers Slack alerts. Investigate bucket drift immediately.
- **Rollback**: Use Git history + `docker-compose up -d --build` to revert to known-good commits, or trigger a redeploy of prior tags via manual workflow dispatch referencing a previous commit SHA.

## 9. Quick Links & Next Actions

- Runbook for deploying databases: [docs/database-deployment-guide.md](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/docs/database-deployment-guide.md)
- Service testing checklist: [docs/service-testing.md](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/docs/service-testing.md)
- SSL hardening: [docs/ssl-certificates-setup.md](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/docs/ssl-certificates-setup.md)
- Scripts for MainWP bootstrap: [backend/scripts/setup_mainwp_stack.py](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/blob/main/backend/scripts/setup_mainwp_stack.py)
- Diagram set: [docs/diagrams/](https://github.com/mitchelldawkinsjr/360-Web-Solutions-Cloud/tree/main/docs/diagrams) for visual flows (CI/CD, backups, monitoring)

Keep this playbook close while migrating apps; when an edge case arises, update the relevant source doc and link it back here so future migrations inherit the same truth.

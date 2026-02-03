# mitch-cloud Deployment Guide

**Purpose**: Complete guide for deploying NBA-Stat-Spot to mitch-cloud VPS infrastructure following the canonical playbook standards.

**Reference**: This guide follows the [mitch-cloud Migration Playbook](../mitch-cloud-migration-playbook.md) standards.

---

## Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Initial Server Setup](#initial-server-setup)
- [Deployment Workflow](#deployment-workflow)
- [Post-Deployment Configuration](#post-deployment-configuration)
- [Monitoring & Maintenance](#monitoring--maintenance)
- [Troubleshooting](#troubleshooting)
- [Rollback Procedures](#rollback-procedures)

## Overview

NBA-Stat-Spot is deployed to mitch-cloud as a Docker app client following these standards:

- **Location**: `/opt/nba-stat-spot`
- **Network**: Attached to `360ws-network` for proxy integration
- **Database**: PostgreSQL in Docker Compose (persisted to `/data/databases/nba-stat-spot`)
- **Deployment**: Automated via GitHub Actions on merge to `main`
- **Monitoring**: Integrated with Uptime Kuma, Netdata, and Slack alerts
- **Backups**: Included in Duplicati database backup job (1 AM UTC)

## Prerequisites

### Server Requirements

Per mitch-cloud playbook Section 4:
- Docker and Docker Compose installed
- `/data` directory structure exists
- `360ws-network` Docker network exists
- SSH access configured with public key in `/root/.ssh/authorized_keys`
- Nginx Proxy Manager running (from infrastructure compose)
- Domain/subdomain DNS configured
- SSL certificate setup (Let's Encrypt via Nginx Proxy Manager)

### GitHub Secrets

Configure these secrets in your GitHub repository (Settings → Secrets and variables → Actions):

- `VPS_HOST` - mitch-cloud server IP/domain
- `VPS_USER` - SSH username (typically root or deployment user)
- `VPS_SSH_KEY` - Private SSH key (public key must be in `/root/.ssh/authorized_keys` on VPS)
- `SLACK_WEBHOOK` - Optional, for deployment notifications

## Initial Server Setup

### 1. Run Setup Script

On the mitch-cloud server, run the setup script to create directory structure and verify prerequisites:

```bash
# Clone or copy the repository first, then:
cd /path/to/nba-stat-spot
sudo bash scripts/setup-mitch-cloud.sh
```

This script will:
- Verify Docker and Docker Compose are installed
- Create directory structure at `/opt/nba-stat-spot`
- Create data directories at `/data/databases/nba-stat-spot` and `/data/nba-stat-spot/logs`
- Ensure `360ws-network` exists
- Create `.env` file template

### 2. Configure Environment Variables

Edit the `.env` file on the VPS:

```bash
nano /opt/nba-stat-spot/.env
```

Required variables (see `.env.example` for full template):

```bash
# Database (already configured in docker-compose.prod.yml)
DATABASE_URL=postgresql://nba_props_user:nba_props_password@postgres:5432/nba_props

# Environment
ENV=production
PORT=8007
OLLAMA_HOST=http://localhost:11434  # Point to your Ollama server (update host as needed)

# CORS - IMPORTANT: Set your frontend domain(s). Include GitHub Pages origin if using it.
CORS_ORIGINS=https://mitchelldawkinsjr.github.io,https://nba-stat-spot.360web.cloud

# Optional: NBA API key
API_NBA_KEY=your-api-key-here
```

**Security Note**: Never commit the `.env` file. It stays on the VPS only.

### 3. Clone Repository (First Time Only)

If this is the first deployment, clone the repository:

```bash
cd /opt
git clone https://github.com/your-username/NBA-Stat-Spot.git nba-stat-spot
cd nba-stat-spot
```

## Deployment Workflow

### Automatic Deployment

Deployment happens automatically when:
- A PR is merged to `main` branch that touches:
  - `backend/**`
  - `docker-compose.prod.yml`
  - `Dockerfile.backend`
  - `.github/workflows/deploy-mitch-cloud.yml`

The GitHub Actions workflow will:
1. SSH into the VPS
2. Sync code to `/opt/nba-stat-spot`
3. Build Docker images
4. Start services with `docker-compose -f docker-compose.prod.yml up -d`
5. Run database migrations
6. Perform health check
7. Send Slack notification (if configured)

### Manual Deployment

To deploy manually:

```bash
# SSH into the VPS
ssh user@your-vps-host

# Navigate to app directory
cd /opt/nba-stat-spot

# Pull latest code
git pull origin main

# Build and deploy
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d

# Run migrations
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Verify health
curl http://localhost:8007/healthz
```

### Manual Workflow Dispatch

You can also trigger deployment manually from GitHub:
1. Go to Actions → "Deploy to mitch-cloud"
2. Click "Run workflow"
3. Select branch and click "Run workflow"

## Post-Deployment Configuration

### 1. Configure Reverse Proxy (Nginx Proxy Manager)

**Option A – Frontend on VPS (recommended: same origin, data loads reliably)**

Serves the React app and proxies `/api/*` to the backend. No CORS; all requests same-origin.

1. Add Proxy Host in Nginx Proxy Manager
2. **Domain Names**: `nba-stat-spot.360web.cloud` (or your subdomain)
3. **Forward Hostname/IP**: `nba-stat-spot-frontend` (frontend container name)
4. **Forward Port**: `80`
5. **Forward Scheme**: `http`
6. **SSL**: Enable Let's Encrypt certificate
7. Ensure the proxy host uses the `360ws-network` so it can reach `nba-stat-spot-frontend`

The frontend container serves the SPA and proxies `/api/` to the backend (port 8007) internally.

**Option B – Frontend on GitHub Pages only**

If you are not running the frontend container and only use GitHub Pages:

1. **Forward Hostname/IP**: `nba-stat-spot-backend`
2. **Forward Port**: `8007`
3. Set `CORS_ORIGINS=https://mitchelldawkinsjr.github.io,https://nba-stat-spot.360web.cloud` in backend `.env`

**Same-origin frontend (no CORS)**

To serve the frontend from the same host as the API and avoid CORS entirely:

1. Build the frontend with the **same-origin** script (root base path, relative API):
   ```bash
   cd frontend
   npm run build:app
   ```
   This sets `VITE_USE_RELATIVE_API=true` and does **not** set `VITE_GITHUB_PAGES`, so the app uses `base: '/'` and requests go to `/api/...` on the same origin.

2. Deploy the built `frontend/dist` to the host that also proxies `/api/` to the backend (e.g. into the frontend container or static root used by Nginx). The existing Nginx config in `deploy/nginx.conf` already serves the SPA at `/` and proxies `/api/` to the backend.

3. For CI/deploy pipeline: run `npm run build:app` in the frontend directory. Do **not** set `VITE_GITHUB_PAGES` or `VITE_REPO_NAME` for this build.

### 2. Set Up Monitoring

#### Uptime Kuma

Add a monitor for the backend:
- **Type**: HTTP(s)
- **URL**: `https://nba-stat-spot.360ws.cloud/healthz`
- **Interval**: 60 seconds

#### Netdata

Netdata should automatically discover containers. Verify:
- Container metrics are visible
- Database metrics are tracked
- Alerts are configured (optional)

#### Slack Alerts

Deployment notifications are sent automatically if `SLACK_WEBHOOK` secret is configured.

### 3. Register Client (Optional)

To register the app in mitch-cloud dashboard:

1. Update `clients/registry.json` in the mitch-cloud repository, OR
2. Call the backend API: `POST /api/v1/apps/create` with app metadata

This enables dashboard visibility and backup policy awareness.

### 4. Verify Backups

Ensure Duplicati includes the database in backups:

- Database data: `/data/databases/nba-stat-spot`
- Should be included in the 1 AM UTC database backup job

Verify backup job includes this path in Duplicati configuration.

## Monitoring & Maintenance

### Health Checks

The backend exposes a health endpoint:

```bash
# From VPS
curl http://localhost:8007/healthz

# From external (via proxy)
curl https://nba-stat-spot.360ws.cloud/healthz
```

Expected response: `{"status": "ok"}`

### View Logs

```bash
# Backend logs
docker-compose -f docker-compose.prod.yml logs -f backend

# Database logs
docker-compose -f docker-compose.prod.yml logs -f postgres

# All services
docker-compose -f docker-compose.prod.yml logs -f
```

### Scheduled Tasks (Cron Jobs)

The backend runs scheduled tasks via supercronic:
- Daily props refresh: 11:00 AM UTC (6:00 AM EST)
- High hit rate refresh: 11:05 AM UTC
- Best bets scan: 11:10 AM UTC
- Cache cleanup: 3:00 AM UTC

View cron logs:
```bash
docker-compose -f docker-compose.prod.yml logs backend | grep supercronic
```

### Database Maintenance

#### Run Migrations

```bash
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

#### Backup Database

```bash
# Manual backup
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U nba_props_user nba_props > backup_$(date +%Y%m%d).sql
```

Automated backups are handled by Duplicati (1 AM UTC daily).

#### Access Database

```bash
docker-compose -f docker-compose.prod.yml exec postgres psql -U nba_props_user -d nba_props
```

### Update Application

To update the application:

1. Make changes and push to `main` branch
2. Deployment happens automatically via GitHub Actions
3. Or manually trigger workflow dispatch

To update without code changes (e.g., rebuild images):

```bash
cd /opt/nba-stat-spot
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d --build
```

## Troubleshooting

### Deployment Fails

1. **Check GitHub Actions logs** for specific error
2. **Verify SSH connection**: Test manually from GitHub Actions runner
3. **Check server resources**: Ensure Docker has enough memory/disk
4. **Verify network**: Ensure `360ws-network` exists

### Health Check Fails

```bash
# Check if container is running
docker-compose -f docker-compose.prod.yml ps

# Check backend logs
docker-compose -f docker-compose.prod.yml logs backend

# Test health endpoint directly
docker-compose -f docker-compose.prod.yml exec backend curl http://localhost:8000/healthz
```

### Database Connection Issues

```bash
# Verify PostgreSQL is running
docker-compose -f docker-compose.prod.yml ps postgres

# Check database logs
docker-compose -f docker-compose.prod.yml logs postgres

# Test connection
docker-compose -f docker-compose.prod.yml exec backend python -c "from app.database import engine; print(engine.connect())"
```

### CORS Errors

1. Verify `CORS_ORIGINS` in `.env` includes your frontend domain
2. Check backend logs for CORS errors
3. Ensure frontend is using correct backend URL

### Cron Jobs Not Running

```bash
# Check if supercronic is running
docker-compose -f docker-compose.prod.yml exec backend ps aux | grep supercronic

# Check cron logs
docker-compose -f docker-compose.prod.yml logs backend | grep -i cron
```

### Network Issues

```bash
# Verify network exists
docker network inspect 360ws-network

# Check container network connectivity
docker-compose -f docker-compose.prod.yml exec backend ping postgres
```

## Rollback Procedures

### Quick Rollback (Git)

```bash
cd /opt/nba-stat-spot
git checkout <previous-commit-sha>
docker-compose -f docker-compose.prod.yml up -d --build
```

### Rollback via GitHub Actions

1. Go to Actions → "Deploy to mitch-cloud"
2. Find the previous successful deployment
3. Click "Re-run jobs" → "Re-run failed jobs"

### Database Rollback

If migrations need to be rolled back:

```bash
# List migration history
docker-compose -f docker-compose.prod.yml exec backend alembic history

# Rollback to specific revision
docker-compose -f docker-compose.prod.yml exec backend alembic downgrade <revision>
```

### Complete Rollback

If you need to revert to Fly.io:

1. Keep Fly.io deployment active until mitch-cloud is verified
2. Revert GitHub Actions workflow changes
3. Update frontend workflow to use Fly.io URL
4. Database backup should be available from Fly.io SQLite export

## Security Checklist

- [ ] `.env` file is not committed to repository
- [ ] Strong database passwords are set
- [ ] CORS origins are explicitly configured
- [ ] SSL/HTTPS is enabled via Nginx Proxy Manager
- [ ] SSH keys are properly secured
- [ ] GitHub Secrets are configured
- [ ] Firewall rules are in place (minimal port exposure)
- [ ] Database backups are verified
- [ ] Monitoring alerts are configured

## Additional Resources

- [mitch-cloud Migration Playbook](../mitch-cloud-migration-playbook.md) - Complete playbook reference
- [Deployment Guide](deployment.md) - General deployment information
- [API Documentation](../docs/api-contracts.md) - API endpoint documentation

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review GitHub Actions logs
3. Check mitch-cloud infrastructure logs (Netdata, Uptime Kuma)
4. Refer to mitch-cloud playbook for infrastructure-specific issues

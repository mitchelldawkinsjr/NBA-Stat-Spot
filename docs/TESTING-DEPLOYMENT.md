# mitch-cloud Migration Testing Guide

Complete testing checklist for the NBA-Stat-Spot migration to mitch-cloud.

## Pre-Deployment Checklist

### 1. GitHub Secrets Configuration

Configure in GitHub: Settings → Secrets and variables → Actions

- [ ] `VPS_HOST` - mitch-cloud server IP or domain
- [ ] `VPS_USER` - SSH username (typically `root`)
- [ ] `VPS_SSH_KEY` - Private SSH key
- [ ] `SLACK_WEBHOOK` - Optional, for notifications

**Verify SSH key:**
```bash
# On your local machine, test SSH connection
ssh -i ~/.ssh/your-key ${VPS_USER}@${VPS_HOST}
```

### 2. Server Prerequisites

SSH into the mitch-cloud server and verify:

```bash
# Check Docker
docker --version
docker-compose --version

# Check directory structure
ls -la /opt/360ws/clients/docker-app/
ls -la /data/

# Check 360ws-network
docker network ls | grep 360ws-network
```

### 3. Run Server Setup Script

```bash
# On the mitch-cloud server
cd /path/to/nba-stat-spot
sudo bash scripts/setup-mitch-cloud.sh
```

This creates:
- `/opt/360ws/clients/docker-app/nba-stat-spot/`
- `/data/databases/nba-stat-spot/`
- `/data/nba-stat-spot/logs/`
- `.env` template file

### 4. Configure Environment Variables

```bash
# Edit the .env file on the server
sudo nano /opt/360ws/clients/docker-app/nba-stat-spot/.env
```

Required settings:
```bash
DATABASE_URL=postgresql://nba_props_user:nba_props_password@postgres:5432/nba_props
ENV=production
PORT=8007
CORS_ORIGINS=https://your-username.github.io,https://nba-stat-spot.360web.cloud
API_NBA_KEY=your-api-key-if-you-have-one
```

## Deployment Testing

### Test 1: Manual Deployment (Recommended First)

Test deployment manually before using GitHub Actions:

```bash
# SSH into server
ssh ${VPS_USER}@${VPS_HOST}

# Navigate to app directory
cd /opt/360ws/clients/docker-app/nba-stat-spot

# Ensure 360ws-network exists
docker network create 360ws-network 2>/dev/null || true

# Build and start services
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# Check container status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f postgres

# Run migrations
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Test health endpoint
curl http://localhost:8007/healthz
# Expected: {"status":"ok"}
```

**Expected Results:**
- [ ] Backend container is running
- [ ] PostgreSQL container is running and healthy
- [ ] Health check returns `{"status":"ok"}`
- [ ] No errors in logs

### Test 2: Database Migration

```bash
# On the server, in the app directory
cd /opt/360ws/clients/docker-app/nba-stat-spot

# Run migration script
bash scripts/migrate-database.sh

# Verify database connection
docker-compose -f docker-compose.prod.yml exec backend python -c "from app.database import engine; print('Connected:', engine.connect())"

# Check tables were created
docker-compose -f docker-compose.prod.yml exec postgres psql -U nba_props_user -d nba_props -c "\dt"
```

**Expected Results:**
- [ ] Migration runs without errors
- [ ] Database connection successful
- [ ] Tables are created

### Test 3: Scheduled Tasks (Cron Jobs)

```bash
# Check if supercronic is running
docker-compose -f docker-compose.prod.yml exec backend ps aux | grep supercronic

# View cron logs
docker-compose -f docker-compose.prod.yml logs backend | grep -i cron

# Manually trigger a cron job to test
docker-compose -f docker-compose.prod.yml exec backend curl -f -X POST "http://localhost:8007/api/v1/admin/refresh/daily-props?min_confidence=50&limit=10"
```

**Expected Results:**
- [ ] Supercronic process is running
- [ ] Cron jobs appear in logs
- [ ] Manual cron job execution works

### Test 4: GitHub Actions Workflow

Trigger deployment via GitHub Actions:

**Option A: Push to main**
```bash
# On your local machine
git add .
git commit -m "Deploy to mitch-cloud"
git push origin migrate-to-mitch-cloud
# Create PR and merge to main
```

**Option B: Manual dispatch**
1. Go to GitHub → Actions → "Deploy to mitch-cloud"
2. Click "Run workflow"
3. Select branch: `migrate-to-mitch-cloud` (or `main` after merge)
4. Click "Run workflow"

**Monitor deployment:**
- Watch GitHub Actions logs in real-time
- Check for Slack notification (if configured)

**Expected Results:**
- [ ] Workflow completes successfully
- [ ] SSH connection works
- [ ] Files are synced to server
- [ ] Docker images build successfully
- [ ] Services start without errors
- [ ] Migrations run
- [ ] Health check passes
- [ ] Slack notification received (if configured)

### Test 5: Reverse Proxy & SSL

Configure Nginx Proxy Manager to route traffic to the backend:

1. **Log into Nginx Proxy Manager** (from mitch-cloud infrastructure)

2. **Add Proxy Host:**
   - Domain: `nba-stat-spot.360ws.cloud`
   - Forward to: `nba-stat-spot-backend:8000`
   - Enable Websockets Support
   - Enable Block Common Exploits

3. **Add SSL Certificate:**
   - Use Let's Encrypt
   - Force SSL

4. **Test external access:**
```bash
# From your local machine
curl https://nba-stat-spot.360ws.cloud/healthz
# Expected: {"status":"ok"}
```

**Expected Results:**
- [ ] Proxy host created successfully
- [ ] SSL certificate issued
- [ ] External health check passes
- [ ] HTTPS is enforced

### Test 6: CORS Configuration

Test that the frontend can connect to the backend:

```bash
# From your local machine
curl -H "Origin: https://your-username.github.io" \
     -H "Access-Control-Request-Method: GET" \
     -X OPTIONS \
     https://nba-stat-spot.360ws.cloud/api/v1/props/daily
```

**Expected Results:**
- [ ] CORS headers are present in response
- [ ] Frontend domain is allowed

### Test 7: Frontend Deployment

Deploy the frontend to GitHub Pages:

```bash
# Trigger frontend deployment
git push origin main  # If deploy-pages.yml triggers on push

# Or manually dispatch
# Go to GitHub → Actions → "Deploy to GitHub Pages" → Run workflow
```

**Test the deployed frontend:**
1. Visit your GitHub Pages URL
2. Check browser console for errors
3. Test API calls to the backend
4. Verify data loads correctly

**Expected Results:**
- [ ] Frontend deploys successfully
- [ ] No console errors
- [ ] Backend API calls succeed
- [ ] Data displays correctly

### Test 8: Monitoring Setup

#### Uptime Kuma
1. Log into Uptime Kuma (from mitch-cloud infrastructure)
2. Add monitor:
   - Type: HTTP(s)
   - URL: `https://nba-stat-spot.360ws.cloud/healthz`
   - Interval: 60 seconds
3. Verify monitor shows "Up"

#### Netdata
1. Log into Netdata
2. Verify containers are visible:
   - `nba-stat-spot-backend`
   - `nba-stat-spot-postgres`
3. Check metrics are being collected

**Expected Results:**
- [ ] Uptime Kuma monitor shows "Up"
- [ ] Netdata shows container metrics
- [ ] No alerts triggered

### Test 9: Backup Verification

Ensure database is included in backups:

1. Check Duplicati configuration (from mitch-cloud infrastructure)
2. Verify backup job includes:
   - `/data/databases/nba-stat-spot`
3. Run a test backup
4. Verify backup completes successfully

**Expected Results:**
- [ ] Backup job includes NBA-Stat-Spot database
- [ ] Test backup runs successfully
- [ ] Backup appears in Backblaze B2 bucket

## Post-Deployment Verification

### Full System Test

Run through these end-to-end tests:

1. **Backend API:**
```bash
curl https://nba-stat-spot.360ws.cloud/healthz
curl https://nba-stat-spot.360ws.cloud/api/v1/props/daily
curl https://nba-stat-spot.360ws.cloud/api/v1/players/search?name=LeBron
```

2. **Frontend:**
   - Visit GitHub Pages URL
   - Navigate through pages
   - Test search functionality
   - Verify prop suggestions load

3. **Database:**
   - Verify data persists across container restarts
   - Check scheduled tasks populate cache

4. **Monitoring:**
   - Verify all monitors show "Up"
   - Check metrics are flowing to Netdata
   - Confirm Slack notifications work

## Rollback Plan

If issues occur, rollback steps:

### Option 1: Revert to Previous Deployment

```bash
# On the server
cd /opt/360ws/clients/docker-app/nba-stat-spot
git log --oneline -10  # Find previous commit
git checkout <previous-commit-sha>
docker-compose -f docker-compose.prod.yml up -d --build
```

### Option 2: Re-enable Fly.io (Emergency)

1. Edit `.github/workflows/deploy-fly.yml`
2. Remove the `if: false` condition
3. Update frontend to use Fly.io URL
4. Deploy to Fly.io

### Option 3: Restore from Backup

```bash
# Stop containers
docker-compose -f docker-compose.prod.yml down

# Restore database from Duplicati backup
# (Follow Duplicati restore procedures)

# Restart containers
docker-compose -f docker-compose.prod.yml up -d
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs backend

# Check resource usage
docker stats

# Rebuild without cache
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
```

### Database Connection Fails

```bash
# Check PostgreSQL is running
docker-compose -f docker-compose.prod.yml ps postgres

# Check PostgreSQL logs
docker-compose -f docker-compose.prod.yml logs postgres

# Verify environment variables
docker-compose -f docker-compose.prod.yml exec backend env | grep DATABASE_URL
```

### Health Check Fails

```bash
# Check if backend is listening
docker-compose -f docker-compose.prod.yml exec backend netstat -tlnp | grep 8000

# Test health endpoint from inside container
docker-compose -f docker-compose.prod.yml exec backend curl http://localhost:8000/healthz

# Check application logs
docker-compose -f docker-compose.prod.yml logs backend | tail -100
```

### GitHub Actions Fails

1. Check GitHub Actions logs for specific error
2. Verify GitHub Secrets are set correctly
3. Test SSH connection manually
4. Check server has enough disk space: `df -h`

## Success Criteria

Migration is complete when all of the following are true:

- [ ] Backend deploys successfully via GitHub Actions
- [ ] Database migrations run without errors
- [ ] Health endpoint returns successful response
- [ ] Frontend connects to backend successfully
- [ ] CORS configuration allows frontend requests
- [ ] Scheduled cron jobs are running
- [ ] SSL/HTTPS is configured and working
- [ ] Uptime Kuma monitor shows "Up"
- [ ] Netdata shows container metrics
- [ ] Backups include the database
- [ ] No errors in application logs
- [ ] Fly.io workflow is disabled
- [ ] All documentation is updated

## Next Steps After Successful Migration

1. Update DNS if using custom domain
2. Configure additional monitoring/alerts as needed
3. Set up log rotation if not already configured
4. Document any custom configurations
5. Update team documentation with new URLs
6. Decommission Fly.io deployment (after stable period)

## Support Resources

- [mitch-cloud Deployment Guide](mitch-cloud-deployment.md)
- [mitch-cloud Migration Playbook](../mitch-cloud-migration-playbook.md)
- [GitHub Actions Workflow](.github/workflows/deploy-mitch-cloud.yml)
- [Server Setup Script](scripts/setup-mitch-cloud.sh)
- [Database Migration Script](scripts/migrate-database.sh)

# VPS Verification Guide

This guide helps you verify that NBA-Stat-Spot is running correctly on your VPS and accessible via the frontend.

## Quick Status Check

Run this script on your VPS:

```bash
# SSH into your VPS
ssh user@your-vps-host

# Navigate to app directory
cd /opt/nba-stat-spot

# Run status check script
bash scripts/check-vps-status.sh
```

This will check:
- Container status (backend, postgres, redis)
- Health endpoints
- Network connectivity
- Volume mounts
- Configuration files

## Manual Verification Steps

### 1. Check Containers Are Running

```bash
cd /opt/nba-stat-spot
docker-compose -f docker-compose.prod.yml ps
```

Expected output: All three containers (backend, postgres, redis) should show "Up" status.

### 2. Test Backend Health Endpoint

```bash
# From VPS
curl http://localhost:8007/healthz

# Expected: {"status":"ok"}
```

### 3. Test Backend API Endpoint

```bash
# From VPS
curl http://localhost:8007/api/v1/props/daily

# Should return JSON with prop suggestions
```

### 4. Verify Redis Connection

```bash
docker-compose -f docker-compose.prod.yml exec redis redis-cli ping
# Expected: PONG
```

### 5. Verify PostgreSQL Connection

```bash
docker-compose -f docker-compose.prod.yml exec postgres psql -U nba_props_user -d nba_props -c "SELECT 1;"
# Expected: 1
```

### 6. Check Logs for Errors

```bash
# Backend logs
docker-compose -f docker-compose.prod.yml logs --tail=50 backend

# Redis logs
docker-compose -f docker-compose.prod.yml logs --tail=20 redis

# PostgreSQL logs
docker-compose -f docker-compose.prod.yml logs --tail=20 postgres
```

Look for:
- Connection errors
- Redis connection failures
- Database migration errors
- Port binding issues

## Frontend-Backend Connection

### Current Configuration

- **Frontend URL**: `https://mitchelldawkinsjr.github.io/NBA-Stat-Spot/`
- **Backend URL** (default): `https://nba-stat-spot.360web.cloud`
- **Backend Port**: `8007`

### Verify Backend is Accessible

1. **Check Nginx Proxy Manager Configuration**:
   - Domain: `nba-stat-spot.360web.cloud` (or your configured domain)
   - Forward to: `nba-stat-spot-backend:8007`
   - Network: `360ws-network`
   - SSL: Enabled (Let's Encrypt)

2. **Test Backend from External**:
   ```bash
   # From your local machine
   curl https://nba-stat-spot.360web.cloud/healthz
   # Expected: {"status":"ok"}
   ```

3. **Test API Endpoint**:
   ```bash
   curl https://nba-stat-spot.360web.cloud/api/v1/props/daily
   # Should return JSON data
   ```

### Verify CORS Configuration

The backend must allow requests from GitHub Pages. Check `.env` file:

```bash
cd /opt/nba-stat-spot
cat .env | grep CORS_ORIGINS
```

Should include:
```
CORS_ORIGINS=https://mitchelldawkinsjr.github.io,https://nba-stat-spot.360web.cloud
```

If CORS is not configured, update `.env` and restart:

```bash
# Edit .env
nano .env

# Add/update CORS_ORIGINS
CORS_ORIGINS=https://mitchelldawkinsjr.github.io,https://nba-stat-spot.360web.cloud

# Restart backend
docker-compose -f docker-compose.prod.yml restart backend
```

## Troubleshooting

### Backend Not Accessible

1. **Check container is running**:
   ```bash
   docker-compose -f docker-compose.prod.yml ps backend
   ```

2. **Check port binding**:
   ```bash
   docker-compose -f docker-compose.prod.yml ps backend
   # Should show 0.0.0.0:8007->8007/tcp
   ```

3. **Check network**:
   ```bash
   docker network inspect 360ws-network | grep nba-stat-spot-backend
   ```

4. **Check Nginx Proxy Manager**:
   - Verify proxy host is configured
   - Check SSL certificate is valid
   - Verify forwarding to correct container and port

### CORS Errors in Browser

If you see CORS errors when accessing the frontend:

1. **Verify CORS_ORIGINS in .env**:
   ```bash
   grep CORS_ORIGINS /opt/nba-stat-spot/.env
   ```

2. **Restart backend**:
   ```bash
   cd /opt/nba-stat-spot
   docker-compose -f docker-compose.prod.yml restart backend
   ```

3. **Check backend logs**:
   ```bash
   docker-compose -f docker-compose.prod.yml logs backend | grep -i cors
   ```

### Redis Connection Issues

1. **Check Redis container**:
   ```bash
   docker-compose -f docker-compose.prod.yml ps redis
   ```

2. **Test Redis connection**:
   ```bash
   docker-compose -f docker-compose.prod.yml exec redis redis-cli ping
   ```

3. **Check backend can reach Redis**:
   ```bash
   docker-compose -f docker-compose.prod.yml exec backend ping -c 2 redis
   ```

### Database Connection Issues

1. **Check PostgreSQL container**:
   ```bash
   docker-compose -f docker-compose.prod.yml ps postgres
   ```

2. **Test database connection**:
   ```bash
   docker-compose -f docker-compose.prod.yml exec backend python -c "from app.database import engine; print('Connected:', engine.connect())"
   ```

3. **Check migrations**:
   ```bash
   docker-compose -f docker-compose.prod.yml exec backend alembic current
   ```

## Complete Verification Checklist

- [ ] All containers are running (backend, postgres, redis)
- [ ] Backend health endpoint responds: `curl http://localhost:8007/healthz`
- [ ] Backend is accessible externally: `curl https://nba-stat-spot.360web.cloud/healthz`
- [ ] API endpoint works: `curl https://nba-stat-spot.360web.cloud/api/v1/props/daily`
- [ ] Redis is accessible: `docker-compose exec redis redis-cli ping`
- [ ] PostgreSQL is accessible: `docker-compose exec postgres pg_isready`
- [ ] CORS_ORIGINS includes GitHub Pages URL
- [ ] Nginx Proxy Manager is configured correctly
- [ ] SSL certificate is valid
- [ ] Frontend can connect to backend (test in browser console)

## Testing Frontend Connection

1. **Open browser DevTools** (F12)
2. **Go to Network tab**
3. **Visit**: `https://mitchelldawkinsjr.github.io/NBA-Stat-Spot/`
4. **Check for API requests**:
   - Look for requests to `https://nba-stat-spot.360web.cloud/api/...`
   - Verify they return 200 OK (not CORS errors)
   - Check response data is valid JSON

5. **Check Console for Errors**:
   - No CORS errors
   - No connection refused errors
   - API calls succeed

## If Something Is Wrong

1. **Run status check script**: `bash scripts/check-vps-status.sh`
2. **Check logs**: `docker-compose -f docker-compose.prod.yml logs`
3. **Verify configuration**: Check `.env` file
4. **Restart services**: `docker-compose -f docker-compose.prod.yml restart`
5. **Check Nginx Proxy Manager**: Verify proxy configuration
6. **Verify DNS**: Ensure domain points to your VPS IP

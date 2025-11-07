# Deployment Guide

This document covers deployment strategies for the NBA Stat Spot application.

## Table of Contents
- [Local Development](#local-development)
- [Docker Deployment](#docker-deployment)
- [Production Deployment](#production-deployment)
- [Environment Variables](#environment-variables)
- [Database Setup](#database-setup)
- [Health Checks](#health-checks)

## Local Development

### Prerequisites
- Python 3.11+
- Node.js 20+
- npm or yarn

### Backend Setup
```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements.txt

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --app-dir backend
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### Development with Docker Compose
```bash
# Start development containers with hot reload
docker-compose -f docker-compose.dev.yml up

# Backend: http://localhost:8000
# Frontend: http://localhost:5173
```

## Docker Deployment

### Production Build
```bash
# Build and start production containers
docker-compose up -d

# View logs
docker-compose logs -f

# Stop containers
docker-compose down
```

### Container Details

#### Backend Container
- **Base Image**: `python:3.11-slim`
- **Port**: 8000
- **Health Check**: `/healthz` endpoint
- **Database**: SQLite by default (file: `nba_props.db`)

#### Frontend Container
- **Build Stage**: Node.js 20 Alpine (builds React app)
- **Runtime**: Nginx Alpine (serves static files)
- **Port**: 80 (mapped to 5173 on host)
- **Proxy**: Routes `/api/*` to backend container

### Nginx Configuration
The frontend container uses Nginx to:
- Serve static React build files
- Proxy API requests to backend
- Handle client-side routing (SPA fallback)

Configuration: `deploy/nginx.conf`

## Production Deployment

### Option 1: Docker Compose (Single Server)

**Best for**: Small to medium deployments, single server setup

1. **Prepare Environment**
   ```bash
   # Set environment variables
   export DATABASE_URL=postgresql://user:pass@localhost/nba_props
   export ENVIRONMENT=production
   ```

2. **Deploy**
   ```bash
   docker-compose up -d --build
   ```

3. **Run Database Migrations**
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

### Option 2: Separate Services (Recommended for Scale)

**Backend Deployment** (e.g., Render, Railway, Fly.io)
- Deploy FastAPI app as a web service
- Configure PostgreSQL database
- Set environment variables
- Run migrations on deploy

**Frontend Deployment** (e.g., Vercel, Netlify, Cloudflare Pages)
- Build static files: `npm run build`
- Deploy `dist/` directory
- Configure API proxy or set `VITE_API_TARGET`

### Option 3: Kubernetes (Enterprise)

1. **Create Kubernetes manifests**
   - Deployment for backend
   - Deployment for frontend
   - Service definitions
   - Ingress configuration

2. **Deploy**
   ```bash
   kubectl apply -f k8s/
   ```

## Environment Variables

### Backend

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./nba_props.db` | Database connection string |
| `ENVIRONMENT` | `development` | Environment name (development/production) |
| `REDIS_URL` | - | Redis connection (for Celery/caching) |
| `API_RATE_LIMIT` | - | Request rate limit per minute |
| `LOG_LEVEL` | `INFO` | Logging level |

### Frontend

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_TARGET` | `http://localhost:8000` | Backend API URL |

**Note**: Vite requires `VITE_` prefix for environment variables to be exposed to the client.

## Database Setup

### SQLite (Development)
No setup required. Database file is created automatically at `backend/nba_props.db`.

### PostgreSQL (Production)

1. **Create Database**
   ```sql
   CREATE DATABASE nba_props;
   CREATE USER nba_props_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE nba_props TO nba_props_user;
   ```

2. **Set Connection String**
   ```bash
   export DATABASE_URL=postgresql://nba_props_user:your_password@localhost/nba_props
   ```

3. **Run Migrations**
   ```bash
   alembic upgrade head
   ```

4. **Seed Initial Data** (if needed)
   ```bash
   python backend/scripts/seed_teams.py
   ```

## Health Checks

### Backend Health Endpoint
```bash
curl http://localhost:8000/healthz
# Response: {"status": "ok"}
```

### Container Health Checks
```bash
# Check backend
docker-compose exec backend curl http://localhost:8000/healthz

# Check frontend
curl http://localhost:5173
```

## Monitoring & Logging

### Structured Logging
- Backend uses `structlog` for JSON-formatted logs
- Logs include request IDs and latency metrics
- Output to stdout (captured by container orchestrator)

### Common Issues

1. **Database Connection Errors**
   - Verify `DATABASE_URL` is correct
   - Check database is accessible from container
   - Ensure migrations have run

2. **API Proxy Issues**
   - Verify backend container name is `backend` in docker-compose
   - Check Nginx configuration
   - Ensure backend is healthy: `/healthz`

3. **CORS Errors**
   - Backend allows all origins in development
   - Configure specific origins for production

4. **Build Failures**
   - Clear Docker cache: `docker-compose build --no-cache`
   - Verify Node.js/Python versions match Dockerfile

## Scaling Considerations

### Backend Scaling
- Use a process manager (e.g., Gunicorn with Uvicorn workers)
- Implement connection pooling for database
- Use Redis for distributed caching
- Consider Celery for background job processing

### Frontend Scaling
- Static files can be served via CDN
- No server-side rendering required (pure SPA)
- Consider edge deployment (Cloudflare, Vercel Edge)

### Database Scaling
- SQLite: Not suitable for concurrent writes
- PostgreSQL: Use connection pooling (PgBouncer)
- Consider read replicas for analytics queries

## Security Checklist

- [ ] Set `ENVIRONMENT=production`
- [ ] Use strong database passwords
- [ ] Configure CORS for specific origins
- [ ] Enable HTTPS/TLS
- [ ] Set up rate limiting
- [ ] Keep dependencies updated
- [ ] Use secrets management (not hardcoded)
- [ ] Enable database backups
- [ ] Configure firewall rules
- [ ] Set up monitoring/alerting

## Backup & Recovery

### Database Backups

**SQLite:**
```bash
cp backend/nba_props.db backups/nba_props_$(date +%Y%m%d).db
```

**PostgreSQL:**
```bash
pg_dump -U nba_props_user nba_props > backups/nba_props_$(date +%Y%m%d).sql
```

### Automated Backups
Set up cron job or scheduled task:
```bash
# Daily backup at 2 AM
0 2 * * * /path/to/backup-script.sh
```


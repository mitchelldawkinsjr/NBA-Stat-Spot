# Fly.io Backend Deployment Guide

This guide will help you deploy the NBA Stat Spot backend to Fly.io and connect it to your GitHub Pages frontend.

## Prerequisites

1. A Fly.io account (sign up at https://fly.io)
2. Fly CLI installed (see installation below)
3. GitHub repository with the code
4. GitHub Pages frontend deployed at: https://mitchelldawkinsjr.github.io/NBA-Stat-Spot/

## Step 1: Install Fly CLI

### macOS
```bash
curl -L https://fly.io/install.sh | sh
```

### Linux
```bash
curl -L https://fly.io/install.sh | sh
```

### Windows (PowerShell)
```powershell
powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"
```

### Verify Installation
```bash
flyctl version
```

## Step 2: Login to Fly.io

```bash
flyctl auth login
```

This will open your browser to authenticate with Fly.io.

## Step 3: Deploy Backend to Fly.io

### Option A: Deploy via Fly CLI (Recommended)

1. **Initialize Fly.io App**
   ```bash
   cd /path/to/NBA-Stat-Spot
   flyctl launch
   ```
   
   This will:
   - Detect your `fly.toml` configuration
   - Ask you to name your app (or use existing)
   - Ask for region (choose closest to users, e.g., `iad` for US East)
   - Create the app on Fly.io

2. **Set Environment Variables**
   ```bash
   flyctl secrets set CORS_ORIGINS="https://mitchelldawkinsjr.github.io,http://localhost:5173"
   flyctl secrets set DATABASE_URL="sqlite:///./nba_props.db"
   ```

3. **Deploy**
   ```bash
   flyctl deploy
   ```
   
   This will:
   - Build your Docker image
   - Push it to Fly.io
   - Deploy and start your app

### Option B: Deploy via GitHub Actions (CI/CD)

1. The repository includes `fly.toml` configuration
2. Add Fly.io secrets to GitHub:
   - Go to GitHub repo → Settings → Secrets → Actions
   - Add secret: `FLY_API_TOKEN`
   - Get token: `flyctl auth token`

3. Create `.github/workflows/deploy-backend.yml`:
   ```yaml
   name: Deploy Backend to Fly.io
   
   on:
     push:
       branches: [main]
       paths:
         - 'backend/**'
         - 'Dockerfile.backend'
         - 'fly.toml'
   
   jobs:
     deploy:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: superfly/flyctl-actions/setup-flyctl@master
         - run: flyctl deploy --remote-only
           env:
             FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
   ```

## Step 4: Get Your Fly.io Backend URL

1. After deployment, your app will be available at:
   - `https://nba-stat-spot-api.fly.dev`
   - Or a custom domain if you've configured one

2. **Test the backend:**
   ```bash
   curl https://nba-stat-spot-api.fly.dev/healthz
   ```
   Should return: `{"status":"ok"}`

3. **View app info:**
   ```bash
   flyctl status
   flyctl info
   ```

## Step 5: Update GitHub Actions Workflow

1. Go to your GitHub repository
2. Navigate to **Settings → Secrets and variables → Actions**
3. Add or update the secret:
   - Name: `BACKEND_API_URL`
   - Value: Your Fly.io backend URL (e.g., `https://nba-stat-spot-api.fly.dev`)

4. The workflow will automatically use this when building the frontend

## Step 6: Verify CORS Configuration

The backend is already configured to allow requests from:
- `https://mitchelldawkinsjr.github.io` (GitHub Pages)
- Any origins specified in `CORS_ORIGINS` environment variable

You can verify CORS is working by checking the browser console on your GitHub Pages site.

## Step 7: Optional: Add PostgreSQL

Fly.io offers PostgreSQL databases. If you want to upgrade from SQLite:

1. **Create PostgreSQL Database**
   ```bash
   flyctl postgres create --name nba-stat-spot-db --region iad
   ```

2. **Attach to Your App**
   ```bash
   flyctl postgres attach --app nba-stat-spot-api nba-stat-spot-db
   ```
   
   This automatically sets `DATABASE_URL` environment variable.

3. **Verify**
   ```bash
   flyctl secrets list
   ```
   You should see `DATABASE_URL` set automatically.

**Note:** SQLite works fine for development, but PostgreSQL is recommended for production and persists data across deployments.

## Step 8: Monitor and Debug

### View Logs
```bash
# Real-time logs
flyctl logs

# Follow logs
flyctl logs -a nba-stat-spot-api

# Historical logs
flyctl logs --app nba-stat-spot-api
```

### Check Status
```bash
flyctl status
flyctl info
```

### SSH into Machine
```bash
flyctl ssh console -a nba-stat-spot-api
```

### Test API Endpoints
```bash
# Test health endpoint
curl https://nba-stat-spot-api.fly.dev/healthz

# Test games endpoint
curl https://nba-stat-spot-api.fly.dev/api/v1/games/today

# Test props endpoint
curl https://nba-stat-spot-api.fly.dev/api/v1/props/daily
```

### Scale Your App
```bash
# Scale to 2 instances
flyctl scale count 2

# Scale memory
flyctl scale memory 512

# Scale CPU
flyctl scale vm shared-cpu-2x
```

## Troubleshooting

### Backend not responding
- Check Fly.io logs: `flyctl logs`
- Verify environment variables: `flyctl secrets list`
- Check app status: `flyctl status`
- Ensure `PORT` is not manually set (Fly.io sets it automatically)

### CORS errors
- Verify `CORS_ORIGINS` includes your GitHub Pages URL
- Check that the backend URL in GitHub secrets matches your Fly.io URL
- Update secrets: `flyctl secrets set CORS_ORIGINS="https://mitchelldawkinsjr.github.io,http://localhost:5173"`

### Database issues
- SQLite files are ephemeral on Fly.io (they reset on redeploy)
- Consider using PostgreSQL for persistent data
- Create PostgreSQL: `flyctl postgres create --name nba-stat-spot-db`

### Build failures
- Check that `Dockerfile.backend` is correct
- Verify Python version in Dockerfile
- Check build logs: `flyctl logs --build`

### Deployment issues
- Check `fly.toml` configuration
- Verify Dockerfile is in the correct location
- Ensure all dependencies are in `requirements.txt`

### App not starting
- Check logs: `flyctl logs`
- Verify port configuration in `fly.toml`
- Check if app is running: `flyctl status`

## Environment Variables Reference

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `CORS_ORIGINS` | Comma-separated list of allowed origins | `*` | No |
| `DATABASE_URL` | Database connection string | `sqlite:///./nba_props.db` | No |
| `PORT` | Server port | `8000` | No (Fly.io sets this) |

### Setting Secrets
```bash
# Set a secret
flyctl secrets set KEY="value"

# Set multiple secrets
flyctl secrets set KEY1="value1" KEY2="value2"

# List secrets
flyctl secrets list

# Remove a secret
flyctl secrets unset KEY
```

## Fly.io Features

### Auto-scaling
- Configured in `fly.toml` with `auto_start_machines` and `auto_stop_machines`
- Free tier: Apps can scale to 0 when idle
- Paid tier: Keep minimum machines running

### Regions
- Choose closest to your users
- Common regions: `iad` (US East), `sjc` (US West), `lhr` (London), `nrt` (Tokyo)

### Custom Domains
```bash
# Add custom domain
flyctl domains add yourdomain.com

# Check DNS records
flyctl dns records list yourdomain.com
```

### Health Checks
- Fly.io automatically health checks your app
- Configure in `fly.toml` if needed

## Cost Considerations

### Free Tier
- 3 shared-cpu-1x VMs with 256MB RAM
- 160GB outbound data transfer
- 3GB persistent volume storage

### Paid Plans
- Start at $1.94/month per VM
- More resources available
- Better performance and reliability

## Next Steps

1. Install Fly CLI
2. Login: `flyctl auth login`
3. Deploy: `flyctl launch` (first time) or `flyctl deploy`
4. Get your Fly.io backend URL
5. Add `BACKEND_API_URL` secret to GitHub
6. Re-run the GitHub Actions workflow to rebuild frontend
7. Test the deployed site!

## Useful Commands

```bash
# Deploy
flyctl deploy

# View logs
flyctl logs

# Check status
flyctl status

# SSH into app
flyctl ssh console

# Scale app
flyctl scale count 2

# View secrets
flyctl secrets list

# Set secrets
flyctl secrets set KEY="value"

# Open app in browser
flyctl open

# View app info
flyctl info
```

## Support

- Fly.io Docs: https://fly.io/docs
- Fly.io Community: https://community.fly.io
- Fly.io Status: https://status.fly.io


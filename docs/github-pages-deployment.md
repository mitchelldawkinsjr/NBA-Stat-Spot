# GitHub Pages Deployment Guide

**Purpose**: Step-by-step guide for deploying the frontend to GitHub Pages with the backend hosted separately.

**Use this guide when**:
- You want free static hosting for the frontend
- You need to deploy the frontend separately from the backend
- You're using GitHub Actions for CI/CD
- You want to host the frontend on a free platform

**Note**: This only covers frontend deployment. The backend must be hosted separately (see [Deployment Guide](./deployment.md) for backend options).

---

## Architecture

- **Frontend**: Deployed to GitHub Pages (static files only)
- **Backend**: Must be hosted separately (Render, Railway, Fly.io, etc.)
- **API Communication**: Frontend calls backend via CORS

## Prerequisites

1. Backend deployed and accessible via HTTPS
2. CORS configured on backend to allow GitHub Pages domain
3. GitHub repository with Actions enabled

## Step 1: Configure Backend CORS

Update `backend/app/main.py` to allow your GitHub Pages domain:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://yourusername.github.io",  # Add your GitHub Pages URL
        "https://yourusername.github.io/NBA-Stat-Spot",  # If using project pages
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Step 2: Set Backend URL for Production

The frontend uses `VITE_API_TARGET` environment variable. For GitHub Pages, you'll need to:

1. Set the backend URL in the build process
2. Or use a config file that gets loaded at runtime

## Step 3: Create GitHub Actions Workflow

Create `.github/workflows/deploy-pages.yml`:

```yaml
name: Deploy to GitHub Pages

on:
  push:
    branches: [ main ]  # Change to your default branch
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: "pages"
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      
      - name: Install dependencies
        working-directory: frontend
        run: npm ci
      
      - name: Build
        working-directory: frontend
        env:
          VITE_API_TARGET: ${{ secrets.BACKEND_API_URL || 'https://your-backend-url.com' }}
        run: npm run build
      
      - name: Setup Pages
        uses: actions/configure-pages@v4
      
      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: frontend/dist

  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    needs: build
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

## Step 4: Configure GitHub Pages

1. Go to repository Settings → Pages
2. Source: Deploy from a branch → Select `gh-pages` branch (or use Actions)
3. Or use "GitHub Actions" as the source

## Step 5: Set Backend URL Secret

1. Go to repository Settings → Secrets and variables → Actions
2. Add secret: `BACKEND_API_URL` with your backend URL (e.g., `https://nba-stat-spot-api.onrender.com`)

## Step 6: Update Frontend for Production

The frontend needs to know the backend URL. Options:

### Option A: Environment Variable (Build Time)
Set `VITE_API_TARGET` in the GitHub Actions workflow (shown above).

### Option B: Runtime Configuration
Create a config file that gets loaded at runtime:

```typescript
// frontend/src/config.ts
export const API_BASE_URL = import.meta.env.VITE_API_TARGET || 
  (import.meta.env.PROD 
    ? 'https://your-backend-url.com'  // Production backend
    : 'http://localhost:8000')         // Development backend
```

Then update all fetch calls to use this base URL.

## Step 7: Handle Base Path (if using project pages)

If your GitHub Pages URL is `username.github.io/NBA-Stat-Spot`, update `vite.config.ts`:

```typescript
export default defineConfig({
  base: '/NBA-Stat-Spot/',  // Your repository name
  // ... rest of config
})
```

And update `index.html` to use relative paths for assets.

## Alternative: Vercel/Netlify (Easier)

For easier deployment with better features:

### Vercel
1. Connect GitHub repo
2. Set root directory: `frontend`
3. Build command: `npm run build`
4. Output directory: `dist`
5. Environment variable: `VITE_API_TARGET=https://your-backend.com`

### Netlify
1. Connect GitHub repo
2. Base directory: `frontend`
3. Build command: `npm run build`
4. Publish directory: `frontend/dist`
5. Environment variable: `VITE_API_TARGET=https://your-backend.com`

## Testing Locally

Test the production build locally:

```bash
cd frontend
VITE_API_TARGET=https://your-backend-url.com npm run build
npm run preview
```

## Notes

- GitHub Pages is free but has limitations (no server-side code, no environment variables at runtime)
- Backend must be publicly accessible via HTTPS
- CORS must be properly configured
- Consider using a custom domain for better branding


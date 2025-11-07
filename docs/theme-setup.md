# Sliced Pro Theme Setup

**Purpose**: Guide for setting up and maintaining the Sliced Pro theme assets in the frontend.

**Use this guide when**:
- Setting up the theme for the first time
- Updating theme assets after changes
- Understanding theme structure and dependencies
- Troubleshooting theme-related issues

---

The Sliced Pro theme assets are located in `THEME/dist/assets/` and are copied to `frontend/public/sliced/assets/` for use in the application.

## Setup Instructions

1. **Build the theme** (if needed):
   ```bash
   cd THEME/HTML
   npm install
   npm run build
   ```

2. **Copy assets to frontend**:
   ```bash
   # From project root
   cp -r THEME/dist/assets/* frontend/public/sliced/assets/
   ```

3. **Reference in HTML**:
   The theme CSS is already referenced in `frontend/index.html`:
   ```html
   <link rel="stylesheet" href="/sliced/assets/css/main.css" />
   ```

## Theme Assets Structure

```
frontend/public/sliced/assets/
├── css/
│   ├── main.css          # Main theme styles
│   ├── plugins.css       # Plugin-specific styles
│   └── tailwind.css      # Tailwind utilities
├── js/                   # Theme JavaScript (if needed)
├── images/               # Theme images
└── libs/                 # Third-party libraries
```

## Notes

- The theme CSS provides base styles and utilities that work alongside Tailwind CSS
- Assets in `frontend/public/` are served statically by Vite
- If you update the theme, rebuild and recopy the assets


# Dark Mode Implementation Summary

This document summarizes the dark mode implementation using Tailwind CSS class-based strategy across the NBA Stat Spot frontend.

## Configuration

- **Tailwind:** `darkMode: 'class'` is set in `tailwind.config.cjs`.
- **CSS:** `src/index.css` uses `@custom-variant dark (&:where(.dark, .dark *));` so `dark:` utilities apply when `.dark` is present on an ancestor (e.g. `<html>`).
- **Root:** The `<html>` element receives the `dark` class when dark mode is active; `data-mode="dark"` is also set for compatibility with existing CSS variables.

## Theme Initialization & Persistence

1. **ThemeContext (`src/context/ThemeContext.tsx`)**
   - **Initial state:** Reads `localStorage` key `nba-stat-spot-theme`. If the user has a stored `'dark'` or `'light'`, that is used. Otherwise, **system preference** is used via `window.matchMedia('(prefers-color-scheme: dark)')`.
   - **Persistence:** On every theme change, the value is written to `localStorage` and the `dark` class is applied or removed on `document.documentElement`.
   - **Toggle:** `toggleTheme()` switches between `'light'` and `'dark'`, which triggers the effect above (effectively `document.documentElement.classList.toggle('dark')`).

2. **First-paint script (`index.html`)**
   - A small inline script runs before first paint to avoid a flash of the wrong theme. It uses the same logic: if a stored preference exists, apply it; otherwise, if the system prefers dark, add the `dark` class. This keeps the initial HTML in sync with what the user (or system) expects.

## Dark Mode Toggle Component

- **`src/components/ThemeToggle.tsx`** uses `useTheme()` and renders a button that calls `toggleTheme()`. It shows a sun icon in dark mode (click to switch to light) and a moon icon in light mode (click to switch to dark). The button already uses `dark:` utilities for icon and hover states.

## UI Areas Updated for Dark Mode

- **Backgrounds:** `bg-white` → `bg-white dark:bg-gray-900` (or `dark:bg-slate-800` where the app uses slate). Page and section backgrounds use `bg-slate-50 dark:bg-slate-900` or equivalent.
- **Text:** `text-black` / `text-gray-900` → `text-gray-900 dark:text-white` (or `dark:text-slate-100`). Muted text uses `text-gray-600 dark:text-gray-400` (or `dark:text-slate-400`).
- **Cards & containers:** Cards and panels use `bg-white dark:bg-slate-800` (or `dark:bg-gray-800`) and `border border-gray-200 dark:border-gray-700` (or `dark:border-slate-700`).
- **Borders:** `border-gray-200` → `border-gray-200 dark:border-gray-700` (or `dark:border-slate-600` / `dark:border-slate-700`).
- **Buttons:** Primary buttons remain high-contrast (e.g. `bg-blue-600`); secondary/outline buttons use `bg-gray-100 dark:bg-slate-700`, `text-gray-700 dark:text-gray-300`, and `hover:bg-gray-50 dark:hover:bg-slate-600`.
- **Navigation:** `SliceProLayout` header, sidebar, and nav links use `dark:bg-slate-800`, `dark:border-slate-700`, and `dark:text-*` / `dark:hover:*` for active and hover states.
- **Modals:** The BetTracker “Record New Bet” modal and its form inputs, dropdowns, and toggle buttons use `dark:bg-slate-800`, `dark:border-slate-700`, and appropriate `dark:text-*` and `dark:bg-*` for inputs and options.
- **Inputs and forms:** Inputs, selects, and labels use `border-gray-300 dark:border-slate-600`, `bg-white dark:bg-slate-700`, `text-gray-900 dark:text-slate-100`, and `focus:ring-*` with `dark:focus:ring-*` where applicable. FiltersPanel, QuickPropLab, ParlayBuilder, and BetTracker form fields follow this pattern.

## Files Modified and Why

| File | Why |
|------|-----|
| `index.html` | Theme script: apply stored theme or system preference before first paint so the correct theme (and `dark` class) is set immediately. |
| `tailwind.config.cjs` | Already had `darkMode: 'class'`; no change needed. |
| `src/index.css` | Already had `@custom-variant dark` and `:root.dark` variables; added a short comment documenting the reusable card pattern (bg + border light/dark). |
| `src/context/ThemeContext.tsx` | Initial state: use system preference when no stored theme; persist and apply `dark` class on `document.documentElement`; added comment for toggle behavior. |
| `src/components/ThemeToggle.tsx` | Already had dark-aware styles; no logic change. |
| `src/layouts/SliceProLayout.tsx` | Already had dark variants for header, sidebar, nav, and season input; no change. |
| `src/components/GoodBetsDashboard.tsx` | Added/fixed dark variants for: empty games state block, loading spinner text, game status badges and card borders, “No games scheduled” and loading copy. |
| `src/pages/OverUnderPage.tsx` | Added dark variants for confidence label text colors in `RecommendationBadge`. |
| `src/components/BetTracker.tsx` | Added dark variants for: loading state container and text; empty state icon, heading, and description; Record New Bet modal (container, header, borders, toggle buttons, labels, inputs, selects, options, dropdown, and search suggestions). |

Other files (e.g. `TeamProfile`, `DailyPropsPage`, `ExplorePage`, `FiltersPanel`, `QuickPropLab`, `ParlayBuilder`, `SuggestionCards`, `AdminDashboard`, `Snackbar`) already used `dark:` utilities for their main surfaces, text, and borders; no further changes were required for this pass.

## Reusable Patterns

- **Card/panel:** `bg-white dark:bg-gray-800` (or `dark:bg-slate-800`) and `border border-gray-200 dark:border-gray-700` (or `dark:border-slate-700`). Documented in `src/index.css`.
- **Muted text:** `text-gray-600 dark:text-gray-400` or `text-gray-500 dark:text-gray-400`.
- **Inputs:** `border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-slate-100` with `focus:ring-2 focus:ring-blue-500/20 dark:focus:ring-blue-400/20`.

## Contrast and Palette

Dark mode uses Tailwind’s gray/slate palette (e.g. `gray-800`, `gray-900`, `slate-700`, `slate-800`) for backgrounds and borders so that text and controls retain sufficient contrast. Existing CSS variables in `:root.dark` (e.g. `--panel-bg`, `--panel-border`) remain in use for legacy panels and are aligned with the same palette.

## What Was Not Changed

- No layout or spacing utilities were removed or altered.
- No working code unrelated to theming was removed.
- Primary actions (e.g. blue buttons) are unchanged; only secondary and neutral surfaces were given dark variants.

## Result

The app supports both light and dark themes. The active theme is driven by the `dark` class on `<html>`, persisted in `localStorage`, and falls back to system preference when the user has not set a preference. Tailwind `dark:` utilities are used consistently across backgrounds, text, cards, borders, buttons, navigation, modals, and form controls.

# Design System Strategy: The Kinetic Performance Ledger

## 1. Overview & Creative North Star
The "Kinetic Performance Ledger" is our creative North Star for this design system. We are not just building a dashboard; we are creating a high-stakes editorial environment that mirrors the intensity of the NBA hardwood. 

To move beyond the "SaaS template" look, this system prioritizes **Atmospheric Depth** over flat layouts. We break the rigid grid through **Intentional Asymmetry**—for example, pairing dense data tables with oversized, editorial-style player imagery that bleeds off the container edges. The goal is a "Data-Rich Minimalism" where the complexity of betting odds feels sophisticated rather than cluttered.

## 2. Colors & Surface Architecture
Our palette uses a deep charcoal foundation to make "Hoop Orange" and "Stat Blue" vibrate with purpose.

### The "No-Line" Rule
Traditional 1px solid borders are strictly prohibited for sectioning. Boundaries must be defined solely through **Background Color Shifts** or tonal transitions.
- **Example:** A betting slip (`surface-container-high`, `#2a2a2a`) sits on the main dashboard area (`surface`, `#131313`) without a stroke. The change in hex value provides the edge.

### Surface Hierarchy & Nesting
Treat the UI as a physical stack of materials. Use the `surface-container` tiers to define "Importance via Elevation":
- **Base Layer:** `surface` (#131313) for the global background.
- **Section Layer:** `surface-container-low` (#1c1b1b) for large content areas.
- **Interactive Layer:** `surface-container-highest` (#353534) for cards or active modules that require the most attention.

### The "Glass & Gradient" Rule
To inject professional "soul," use **Glassmorphism** for floating elements like dropdown menus or live-score overlays. Use `surface-variant` (#353534) at 60% opacity with a `backdrop-blur-md`.
- **Signature Textures:** For primary CTAs, apply a subtle linear gradient from `primary_container` (#ff6b00) to `primary_fixed_dim` (#ffb693). This adds a 3D "lit-from-within" quality reminiscent of stadium lighting.

## 3. Typography: Editorial Authority
We utilize **Inter** as a condensed, high-density workhorse. The hierarchy is designed to highlight "The Number" (the odds/props) while keeping metadata legible but secondary.

- **Display & Headline:** Use `display-md` (2.75rem) for big-ticket player stats or win totals. This should feel bold and authoritative.
- **Titles:** `title-md` (1.125rem) is the standard for prop categories (e.g., "Points + Rebounds"). 
- **Data Labels:** `label-sm` (0.6875rem) should be used for secondary math and "Over/Under" indicators.
- **Hierarchy Note:** Never use "Hoop Orange" for long-form body text. Reserve it for primary numbers and actionable labels to maintain high-contrast visual signposts.

## 4. Elevation & Depth
Depth in this system is achieved through **Tonal Layering**, not structural lines.

- **The Layering Principle:** Place a `surface-container-lowest` card (#0e0e0e) on a `surface-container-low` (#1c1b1b) background to create a "recessed" look for historical data. Use `surface-container-high` (#2a2a2a) to create "lifted" interactive props.
- **Ambient Shadows:** For "floating" betting slips, use an extra-diffused shadow: `shadow-xl` with 6% opacity, using the `on_surface` color (#e5e2e1) as the shadow tint. This mimics natural light reflecting off the "Hoop Orange" elements.
- **The "Ghost Border" Fallback:** If a prop card requires a border for accessibility, use the `outline_variant` token (#5a4136) at **15% opacity**. This creates a "suggestion" of a container without breaking the editorial flow.

## 5. Components

### Buttons
- **Primary:** `primary_container` (#ff6b00) background with `on_primary` (#561f00) text. Use the `lg` roundedness (0.5rem).
- **Secondary (Odds Buttons):** `secondary_container` (#4a8eff) background. These should feel like solid, clickable blocks of data.

### Chips (Prop Status)
- **Active Prop:** Use a semi-transparent `tertiary_container` (#059eff) with a `tertiary` (#9ccaff) label. 
- **Sizing:** Keep chips compact using `spacing-1` (0.2rem) vertical and `spacing-2.5` (0.5rem) horizontal padding.

### Input Fields (Betting Amount)
- **State:** Use `surface_container_highest` (#353534) as the fill. 
- **Error State:** Transitions to `error_container` (#93000a) with a subtle `error` (#ffb4ab) glow.

### Cards & Lists (The Prop Feed)
- **Forbid Dividers:** Do not use lines to separate props. Use `spacing-4` (0.9rem) of vertical white space combined with a `surface-container-low` background shift to denote a new entry.
- **Live Indicators:** Use a pulsing "Stat Blue" (#007BFF) dot next to `label-md` text to show real-time data updates.

### Custom Component: The Prop-Slider
A bespoke slider for adjusting "Over/Under" lines should use a `secondary_fixed_dim` (#adc7ff) track with a high-contrast `primary_container` (#ff6b00) thumb.

## 6. Do's and Don'ts

### Do:
- **Use Intentional Asymmetry:** If a player has a "Hot Streak," let their photo break the top boundary of their data card.
- **Prioritize the Odds:** Ensure `title-lg` or `headline-sm` is used for the betting price (-110, +150).
- **Use Space as a Separator:** Use the `spacing-8` (1.75rem) value to separate major dashboard widgets.

### Don't:
- **Don't use 100% White:** Use `on_surface` (#e5e2e1) for text to prevent eye strain in dark mode.
- **Don't use 1px Borders:** Never use a solid line to separate the sidebar from the main content; use a `surface-container-lowest` (#0e0e0e) background for the sidebar instead.
- **Don't Over-Round:** Stick to the `lg` (0.5rem / 8px) scale for main cards. Avoid `full` (9999px) pills unless they are small action chips.
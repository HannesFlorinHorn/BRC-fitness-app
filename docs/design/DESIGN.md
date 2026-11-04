---
name: Berliner Ruder-Club Athletic Tracker
colors:
  surface: '#f9f9ff'
  surface-dim: '#d0daf6'
  surface-bright: '#f9f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f1f3ff'
  surface-container: '#e9edff'
  surface-container-high: '#e0e8ff'
  surface-container-highest: '#d8e2fe'
  on-surface: '#111b30'
  on-surface-variant: '#5c3f3e'
  inverse-surface: '#263046'
  inverse-on-surface: '#edf0ff'
  outline: '#916f6d'
  outline-variant: '#e5bdbb'
  surface-tint: '#bf0023'
  primary: '#ba0022'
  on-primary: '#ffffff'
  primary-container: '#e02636'
  on-primary-container: '#fffbff'
  inverse-primary: '#ffb3af'
  secondary: '#4c5e87'
  on-secondary: '#ffffff'
  secondary-container: '#bccefe'
  on-secondary-container: '#455780'
  tertiary: '#0051d6'
  on-tertiary: '#ffffff'
  tertiary-container: '#316bf3'
  on-tertiary-container: '#fffcff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ffdad8'
  primary-fixed-dim: '#ffb3af'
  on-primary-fixed: '#410006'
  on-primary-fixed-variant: '#930019'
  secondary-fixed: '#d8e2ff'
  secondary-fixed-dim: '#b3c6f5'
  on-secondary-fixed: '#031a40'
  on-secondary-fixed-variant: '#34466e'
  tertiary-fixed: '#dbe1ff'
  tertiary-fixed-dim: '#b4c5ff'
  on-tertiary-fixed: '#00174b'
  on-tertiary-fixed-variant: '#003ea8'
  background: '#f9f9ff'
  on-background: '#111b30'
  surface-variant: '#d8e2fe'
typography:
  display-hero:
    fontFamily: Poppins
    fontSize: 56px
    fontWeight: '700'
    lineHeight: 60px
    letterSpacing: -0.03em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '800'
    lineHeight: 38px
    letterSpacing: -0.02em
  body-lg:
    fontFamily: Manrope
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
    letterSpacing: 0em
  label-lg:
    fontFamily: Poppins
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 18px
    letterSpacing: 0.04em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1rem
  margin: 1rem
  gutter-tablet: 1.25rem
  margin-tablet: 1.5rem
  gutter-desktop: 1.5rem
  margin-desktop: 2.5rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.875rem
  space-lg: 1.25rem
  space-xl: 2rem
---

## Brand & Style

The design system establishes a high-performance, clean athletic aesthetic engineered specifically for rowing ergometer rooms, boathouse bays, and gym training sessions. It combines the historic maritime prestige of Berliner Ruder-Club (BRC)—founded in 1880 on the Wannsee—with the focused, high-contrast clarity of modern sports telemetry.

The visual style blends **High-Contrast Athletic Performance** with refined **Tonal Maritime Layering**:
- Crisp, bright maritime foundations ensure maximum legibility and energetic clarity in sunlit boathouses and brightly lit gym floors.
- The club’s heraldic star-red functions as a high-visibility operational accent for active splits, live recording states, stroke rate spikes, and high-priority call-to-actions.
- Clean, condensed data typography and monospaced telemetry ensure split times (`1:38.4 / 500m`), wattage, stroke rates (`s/m`), and heart rate zones can be digested instantly from an arm’s length on an ergometer mount or phone stand.
- Elements feature chiseled, compact geometry with subtle micro-borders rather than heavy blur effects, ensuring instant rendering and rapid recognition under high heart-rate conditions.

## Colors

The palette is engineered for pure legibility and light-adapted environments:

- **Primary (`#E02636` / Club Star-Red):** Derived from the historic BRC pennant star and burgee canton. Reserved strictly for active workout telemetry, primary buttons, recording status indicators, critical target zones, and brand hero moments. Never dilute it across large passive backgrounds.
- **Secondary (`#0F244A` / Deep Maritime Container):** Used for elevated cards, telemetry modules, and segmented control backgrounds.
- **Tertiary (`#2563EB` / Wannsee Cobalt):** Represents hydrodynamics, pace delta comparisons, and secondary graphical curves in performance charts.
- **Neutral (`#081327` / Abyssal Blue Base):** The primary canvas background. It maintains deep maritime character and sharp contrast.
- **Tonal Hierarchy & Contrast:**
  - `surface-base` (`#ffffff`): Canvas floor.
  - `surface-container` (`#f1f5f9`): Standard module and card background.
  - `surface-container-high` (`#e2e8f0`): Elevated list items, active cells, and input surfaces.
  - `surface-container-highest` (`#cbd5e1`): Interactive hover states and chip selections.
  - `text-primary` (`#0f172a`): Primary metrics, headers, and essential readouts.
  - `text-secondary` (`#334155`): Labels, unit designations (`/500m`, `SPM`, `WATTS`), and inactive values.
  - `text-muted` (`#64748b`): Timestamps, grid axis lines, and disabled toggles.

## Typography

Typography pairs the structural, athletic warmth of **Manrope** for body text and primary interface guidance with the precise geometric clarity of **Inter** for headlines and the modern cadence of **Poppins** for numerical telemetry, timers, pace metrics, and all unit labels.

### Usage Rules:
- **Numerical Telemetry:** Always use `Poppins` with tabular figures (`font-variant-numeric: tabular-nums`) so live split timers and watt counters remain perfectly static without horizontal jitter.
- **Labels & Units:** Render secondary labels (e.g. `AVG SPLIT`, `STROKE RATE`, `REST INTERVAL`) in uppercase `Poppins` using `label-sm` or `label-md` with tracking between `+0.04em` and `+0.08em` for rapid peripheral-vision scanning.
- **Narrative & Sectioning:** Use `Inter` and `Manrope` for session titles, crew rosters, logbook notes, and analytical summaries to ensure effortless readability during post-workout reviews.

## Layout & Spacing

The system implements a mobile-first responsive layout tailored for hand-held logging, cradle mounts on Concept2 ergometers, and tablet boathouse stands.

### Grid & Canvas Rhythms:
- **Mobile (<768px):** Single-column layout with a 4-column sub-grid for telemetry dashboards. Canvas margins are locked to `1rem` (`16px`) to maximize data card surface area on narrow devices.
- **Tablet (768px - 1024px):** 8-column layout with `1.25rem` gutters and `1.5rem` outer margins. Accommodates side-by-side live split charts and crew lineup tables.
- **Desktop (>1024px):** 12-column layout with max-width constrained to `1200px`, centered with `2.5rem` margins and `1.5rem` gutters for training plan architecture and longitudinal season analytics.

### Component Spacing Discipline:
- **Telemetry Dashboards:** Group high-priority pairs (e.g., metric value + unit label) with `space-xs` (4px).
- **Module Internal Padding:** Standard cards use `space-md` (14px) on mobile and `space-lg` (20px) on desktop to provide touch targets exceeding 48px for sweaty, chalked, or calloused hands.

## Elevation & Depth

To maintain visual clarity in bright environments, this design system relies on **Tonal Layering** and **Crisp Ghost Outlines** rather than diffused drop shadows:

- **Base Layer (Level 0):** Background surface `#ffffff`.
- **Card Surface (Level 1):** Background `#f1f5f9` framed by a 1px border of `#cbd5e1`. No shadow.
- **Interactive & Raised Telemetry (Level 2):** Background `#e2e8f0` with 1px border `#94a3b8`.
- **Active / Focused Telemetry (Level 3):** Background `#e2e8f0` paired with a 1.5px border of `#e02636` and an inner micro-glow (`box-shadow: inset 0 0 12px rgba(224, 38, 54, 0.12)`).
- **Modal Overlays & Sticky Live Bars:** Background `rgba(255, 255, 255, 0.94)` with `backdrop-filter: blur(12px)` and a top or bottom boundary line of `#cbd5e1`.

## Shapes

The design system enforces a **Rounded Athletic Geometry** (`roundedness: 2`):

- Standard components (telemetry tiles, text inputs, list items) use a comfortable `8px` (`0.5rem`) border radius.
- Cards, modal containers, and workout segment wrappers use `16px` (`1rem`) border radius (`rounded-lg`).
- Action pills and status indicator badges use full stadium pill curves (`9999px`) to immediately distinguish floating, tappable filters and active recording badges from structural data panels.
- This friendly, accessible corner radius maximizes internal card space for multi-column split tables while offering a modern, tactile feel aligned with the precision engineering of competitive racing shells.

## Components

### Buttons
- **Primary Athletic Button:** Solid `#e02636` background, `#ffffff` text, `Poppins` uppercase semi-bold font, `8px` radius, minimum height of `48px`. On active press, shifts to `#b91c1c`.
- **Secondary Club Button:** `#0f244a` background with 1px border `#cbd5e1`, `#ffffff` text. On hover/focus, border shifts to `#2563eb`.
- **Destructive / Stop Button:** Light crimson surface `#fee2e2` with border `#dc2626` and `#991b1b` text, indicating critical workout termination or lap reset.

### Telemetry Cards
- **Structure:** Modular container `#f1f5f9` with `1px` border `#cbd5e1` and `rounded-lg` corners.
- **Layout:** Top row features `label-sm` unit name (`SPLIT / 500M`, `STROKE RATE`) in `#334155`. Center features `telemetry-metric` in `#0f172a`. Bottom row provides comparative delta (`-0.8s vs target`) in `#10b981` (faster) or `#dc2626` (slower).

### Chips & Filters
- **Default:** `#f1f5f9` background, 1px border `#cbd5e1`, `#334155` text, stadium-pill radius, height `32px`.
- **Selected:** `#e2e8f0` surface with `#0284c7` or `#e02636` indicator dot, border `#2563eb`, text `#0f172a`.

### Workout Input Fields
- Input cavity with background `#ffffff`, 1px border `#cbd5e1`, and text in `#0f172a`.
- On focus: border shifts cleanly to `#e02636` with zero fuzzy blur rings.
- Large numerical stepper inputs incorporate bold `+` and `-` steppers on the right side for rapid ergometer drag factor and weight adjustments.

### Lists & Split Tables
- Alternating subtle rows (`#f1f5f9` and `#ffffff`) divided by hairline borders of `#cbd5e1`.
- High-contrast column alignments: text aligned left in `Manrope`, numeric metrics aligned right in tabular `Poppins`.

### Checkboxes & Segmented Controls
- Segmented tab switches (e.g., `Ergometer | On-Water | Weight Room`) use an inset container of `#f8fafc` with a sliding active segment in `#ffffff` framed by a subtle 1px border of `#cbd5e1` and text in `#0f172a`.
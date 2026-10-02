---
name: Telemetry Spec
colors:
  surface: '#f6faff'
  surface-dim: '#d5dbe1'
  surface-bright: '#f6faff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4fb'
  surface-container: '#e9eef5'
  surface-container-high: '#e3e9f0'
  surface-container-highest: '#dde3ea'
  on-surface: '#161c21'
  on-surface-variant: '#414846'
  inverse-surface: '#2b3136'
  inverse-on-surface: '#ecf1f8'
  outline: '#717976'
  outline-variant: '#c0c8c5'
  surface-tint: '#3e665d'
  primary: '#002720'
  on-primary: '#ffffff'
  primary-container: '#133d35'
  on-primary-container: '#7ea89d'
  inverse-primary: '#a5cfc4'
  secondary: '#56615a'
  on-secondary: '#ffffff'
  secondary-container: '#d7e3da'
  on-secondary-container: '#5a655e'
  tertiary: '#460900'
  on-tertiary: '#ffffff'
  tertiary-container: '#681a07'
  on-tertiary-container: '#f07f64'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#c0ece0'
  primary-fixed-dim: '#a5cfc4'
  on-primary-fixed: '#00201b'
  on-primary-fixed-variant: '#254e45'
  secondary-fixed: '#dae5dc'
  secondary-fixed-dim: '#bec9c1'
  on-secondary-fixed: '#141e18'
  on-secondary-fixed-variant: '#3f4943'
  tertiary-fixed: '#ffdad2'
  tertiary-fixed-dim: '#ffb4a3'
  on-tertiary-fixed: '#3d0700'
  on-tertiary-fixed-variant: '#7f2a16'
  background: '#f6faff'
  on-background: '#161c21'
  surface-variant: '#dde3ea'
typography:
  headline-xl:
    fontFamily: Space Grotesk
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 38px
    letterSpacing: -0.02em
  headline-xl-mobile:
    fontFamily: Space Grotesk
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 30px
    letterSpacing: -0.01em
  headline-lg:
    fontFamily: Space Grotesk
    fontSize: 22px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Space Grotesk
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 22px
  metric-display:
    fontFamily: Space Grotesk
    fontSize: 36px
    fontWeight: '500'
    lineHeight: 40px
    letterSpacing: -0.03em
  body-lg:
    fontFamily: IBM Plex Sans
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: IBM Plex Sans
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  code-sm:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  label-caps:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.08em
  label-badge:
    fontFamily: JetBrains Mono
    fontSize: 10px
    fontWeight: '500'
    lineHeight: 12px
    letterSpacing: 0.04em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-lg: 1.5rem
  margin: 1.5rem
  margin-mobile: 0.75rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1.25rem
  space-xl: 1.75rem
---

## Brand & Style

This design system is engineered for mission-critical telemetry, cryptographic audit logs, and infrastructure security compliance dashboards. The visual tone projects absolute precision, mathematical determinism, and institutional authority. It avoids frivolous decoration, soft shadows, or playful micro-interactions in favor of utilitarian density, crisp alignment, and structured data hierarchy.

The design movement combines **technical minimalism** with **functional enterprise brutalism**:
- Razor-sharp structural grid lines, thin 1px containment borders, and muted cool-slate tonal planes.
- Monospaced typography for machine hashes, rates, metrics, and technical labels paired with clean, geometric sans for editorial readability.
- Purposeful operational accents: deep forest slate green as the primary anchor, subdued beige/sage pills for verified statuses, and restrained safety amber/rust for fault indicators.
- Information density optimized for operators monitoring real-time pipelines, air-gapped enclaves, and cryptographic proofs.

## Colors

The palette is derived from technical laboratory interfaces and high-assurance security appliances. Surfaces feature high-luminance, pale cool-white and neutral-slate backgrounds framed by precise, desaturated slate borders.

### Palette Architecture
- **Primary (`#133D35`)**: Deep pine/forest slate. Used for primary CTA buttons, active progress tracks, verification indicators, and high-priority branding.
- **Secondary (`#5A655E`)**: Muted sage-slate. Used for technical secondary labels, telemetry tags, and structural badges.
- **Tertiary (`#8C341F`)**: Desaturated rust/crimson. Reserved exclusively for pipeline diverts, quarantine alerts, syntax anomalies, and dropped payload counters.
- **Neutral (`#6C7278`)**: Balanced technical slate. Used for intermediate borders, structural divider rules, metadata keys, and secondary metrics.

### Surface Tones & Tokens
- Canvas background: `#F9F9F8` (Warm technical off-white).
- Card container background: `#FFFFFF` (Solid white for contrast).
- Subdued panel background: `#F1F2ED` (Tinted neutral parchment/slate for inner modules and metrics pills).
- Border default: `#D4D9D5` (Precise 1px framing).
- Border subtle: `#E5E8E5` (Light internal rules).
- Text primary: `#121614` (Near-black carbon).
- Text secondary: `#555E57` (Subdued engine slate).
- Success / Verified: `#246B55` with `#E5EFE9` background.

## Typography

Typography establishes strict order through a high-contrast pairing of three specialized typefaces:

1. **Space Grotesk** governs page headers, section titles, and key operational metrics (`1,428,910`, `99.94%`). Its geometric structure provides an engineering feel without sacrificing digital readability.
2. **IBM Plex Sans** serves body copy, subtitles, narrative notes, and descriptive explanations.
3. **JetBrains Mono** is applied across all machine-readable telemetry: system metadata, node IDs, protocol names, hardware hashes, byte distributions, and uppercase operational labels.

All technical section tags, metadata headers, and telemetry keys are set in `label-caps` (`JetBrains Mono`, uppercase, tracking `+0.08em`).

## Layout & Spacing

The layout is built upon a 12-column rigid responsive grid system configured for maximum informational throughput:

- **Desktop (>= 1280px)**: 12-column layout with `1.5rem` outer margins and `1rem` column gutters. Metric cards span 3 columns each (4-up layout), pipeline stages split evenly into 4 columns, and lower audit modules utilize a 5:7 column split.
- **Tablet (768px - 1279px)**: 8-column layout. Metric cards flow into a 2x2 grid (4 columns each); pipeline cards stack into two rows of two.
- **Mobile (< 768px)**: 4-column layout with `0.75rem` outer margins. All metric and audit panels collapse to full-width stacked components.

Spacing adheres strictly to an 8pt architectural rhythm (`0.25rem`, `0.5rem`, `0.75rem`, `1.25rem`, `1.75rem`). White space is functional: tight component internal padding (`space-md`) ensures high telemetry density, while deliberate outer section margins (`space-xl`) isolate critical compliance domains.

## Elevation & Depth

Visual separation relies on **low-contrast 1px outlines** and **tonal planar containment** rather than drop shadows:

- **Zero Ambient Shadows**: Cards and buttons do not emit diffuse drop shadows. Floating or elevated impressions are achieved through crisp 1px borders (`#D4D9D5`) rendered over alternating background values (`#FFFFFF` resting atop `#F9F9F8`).
- **Inner Recessed Surfaces**: Secondary wells, code boxes, and telemetry sub-blocks utilize flat `#F1F2ED` backgrounds with hairline borders, conveying physical insertion into the parent card.
- **Status Accents**: Depth and urgency are established using colored 3px vertical accent bars on the left border of notification banners or container headers (e.g., `#133D35` for active pipelines, `#8C341F` for quarantine warnings).

## Shapes

The design system employs a soft, machined curvature scale (`roundedness: 1`):

- **Default UI Containers & Cards**: `0.25rem` (4px). Provides an exact, industrial instrument look without sharp 90-degree corners.
- **Badges & Telemetry Chips**: `0.125rem` (2px) to `0.25rem` (4px). Preserves strict tabular alignment when placed inside monospaced data grids.
- **Input Fields & Action Controls**: `0.25rem` (4px) corner radii.
- **Status Dots & Avatars**: Fixed circles (`50%` / full pill).

## Components

### Buttons & Actions
- **Primary Button**: Deep green background (`#133D35`), text in pure white (`#FFFFFF`), `0.25rem` radius, 8px 16px padding. Monospace or semi-bold sans typography. Hover darkens to `#0E2C26`.
- **Secondary / Ghost Button**: White surface with a 1px border (`#D4D9D5`), text `#121614`, hover state shifts surface to `#F1F2ED`. Accompanied by 14px mono action icons (e.g., download, refresh, copy).

### Telemetry Badges & Chips
- High-precision rectangular chips with 1px border (`#D4D9D5`) and neutral tint (`#F1F2ED` or `#EAECE8`).
- Set in uppercase `label-badge` (`JetBrains Mono`).
- Indicator dots (4px diameter) prefix status badges: glowing `#246B55` for active/verified, `#8C341F` for errors.

### Cards & Container Panels
- Pure white background (`#FFFFFF`), 1px solid border (`#D4D9D5`), `0.25rem` radius.
- Header bands integrate metadata badges and status pills pinned to top corners.
- Internal multi-metric grids are separated by 1px vertical borders (`#E5E8E5`) instead of empty whitespace gaps.

### Technical Data Tables & Proportional Bars
- Rows utilize hairline bottom dividers (`#E5E8E5`) with zero zebra-striping.
- Value cells display monospaced figures right-aligned for numeric comparisons.
- Segmented distribution bars use high-contrast color blocks representing syntax categories (`#133D35`, `#42635B`, `#5E5B4B`, `#8C8F8E`).

### Code & Hash Vault Inputs
- Recessed `#F5F6F3` background, 1px border `#D4D9D5`.
- Text styled in `JetBrains Mono` 12px with right-aligned one-click clipboard copy triggers.
- Monospace key-value footer pairings for hardware attestation stamps.
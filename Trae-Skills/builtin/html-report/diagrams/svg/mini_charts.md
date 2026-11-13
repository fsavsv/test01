# Lightweight SVG Mini Charts

> ⚠️ **Use ECharts for data visualization first.** The SVG templates in this file are only suitable for extremely simple scenarios. If your chart involves multi-point comparisons, axes, legends, or interactivity, use ECharts instead.

## Purpose

Use hand-written SVG only in these minimal scenarios:
- Single progress bar / donut percentage display
- Single-value gauge inside a card
- Minimal comparison with 1-3 simple values
- Purely decorative indicators with no axes or legends

**Not suitable (use ECharts instead):**
- Comparisons/rankings with > 3 data points
- Charts requiring axes or legends
- Multi-series data visualization
- Any scenario requiring tooltips or interactivity

## CSS Variables

Use the active values already injected from `references/color-system.md`.
These snippets consume page, chart-series, chart-accent, other, and semantic
roles but must not redeclare their values locally.

The main report contract uses `--ink` for primary text. If older snippets use `--fg`, treat it as equivalent to `--ink` and prefer `--ink` in new SVG.

---

## 1. Horizontal Bar Chart

**Suitable for:** Tiny comparison lists with 1-3 items. Use ECharts for rankings with more items, axes, legends, or tooltips.

### Calculation

```
bar_width = value / max_value * max_bar_px
```

### Full Example

```svg
<svg width="240" height="120" viewBox="0 0 240 120" xmlns="http://www.w3.org/2000/svg">
  <!-- Item 1 -->
  <text x="0" y="14" font-size="11" fill="var(--ink)">USA</text>
  <rect x="45" y="4" width="180" height="12" rx="3" fill="var(--chart-series-1)" opacity="0.9"/>
  <text x="228" y="14" font-size="10" fill="var(--ink)" text-anchor="end">45%</text>

  <!-- Item 2 -->
  <text x="0" y="38" font-size="11" fill="var(--ink)">China</text>
  <rect x="45" y="28" width="120" height="12" rx="3" fill="var(--chart-series-2)" opacity="0.75"/>
  <text x="168" y="38" font-size="10" fill="var(--ink)" text-anchor="end">30%</text>

  <!-- Item 3 -->
  <text x="0" y="62" font-size="11" fill="var(--ink)">Other</text>
  <rect x="45" y="52" width="48" height="12" rx="3" fill="var(--chart-other)" opacity="0.7"/>
  <text x="96" y="62" font-size="10" fill="var(--ink)" text-anchor="end">12%</text>
</svg>
```

---

## 2. Donut Chart

**Suitable for:** Proportional display of 2-3 simple categories. Use ECharts for larger category sets, labels, legends, or tooltips.

### Calculation

Use `stroke-dasharray` and `stroke-dashoffset` to simulate arc segments:

```
circumference = 2 * π * r
dash = percentage / 100 * circumference
offset = -cumulative_percentage / 100 * circumference
```

### Full Example (3 segments)

```svg
<svg width="120" height="120" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
  <!-- Background ring -->
  <circle cx="60" cy="60" r="45" fill="none" stroke="var(--muted)" stroke-width="12" opacity="0.2"/>

  <!-- Segment 1: 55% -->
  <circle cx="60" cy="60" r="45" fill="none"
    stroke="var(--chart-series-1)" stroke-width="12"
    stroke-dasharray="155.5 282.7"
    stroke-dashoffset="0"
    transform="rotate(-90 60 60)"
    stroke-linecap="round"/>

  <!-- Segment 2: 30% -->
  <circle cx="60" cy="60" r="45" fill="none"
    stroke="var(--chart-series-2)" stroke-width="12"
    stroke-dasharray="84.8 282.7"
    stroke-dashoffset="-155.5"
    transform="rotate(-90 60 60)"
    stroke-linecap="round"/>

  <!-- Segment 3: 15% -->
  <circle cx="60" cy="60" r="45" fill="none"
    stroke="var(--chart-other)" stroke-width="12"
    stroke-dasharray="42.4 282.7"
    stroke-dashoffset="-240.3"
    transform="rotate(-90 60 60)"
    stroke-linecap="round"/>

  <!-- Center text -->
  <text x="60" y="56" text-anchor="middle" font-size="18" font-weight="600" fill="var(--ink)">55%</text>
  <text x="60" y="72" text-anchor="middle" font-size="10" fill="var(--muted)">Completion</text>
</svg>
```

---

## 3. Progress Bar

**Suitable for:** Single percentage display (completion rate, achievement rate).

### Full Example

```svg
<svg width="200" height="20" viewBox="0 0 200 20" xmlns="http://www.w3.org/2000/svg">
  <!-- Background track -->
  <rect x="0" y="6" width="200" height="8" rx="4" fill="var(--muted)" opacity="0.2"/>
  <!-- Fill (72%) -->
  <rect x="0" y="6" width="144" height="8" rx="4" fill="var(--chart-series-1)"/>
  <!-- Percentage label -->
  <text x="150" y="13" font-size="9" fill="var(--ink)">72%</text>
</svg>
```

### Multi-Segment Progress Bar

```svg
<svg width="200" height="20" viewBox="0 0 200 20" xmlns="http://www.w3.org/2000/svg">
  <!-- Background -->
  <rect x="0" y="6" width="200" height="8" rx="4" fill="var(--muted)" opacity="0.2"/>
  <!-- Segment 1: Complete (40%) -->
  <rect x="0" y="6" width="80" height="8" rx="4" fill="var(--chart-positive)"/>
  <!-- Segment 2: In Progress (25%) -->
  <rect x="80" y="6" width="50" height="8" fill="var(--chart-accent)"/>
  <!-- Segment 3: Failed (10%) -->
  <rect x="130" y="6" width="20" height="8" fill="var(--chart-negative)"/>
</svg>
```

---

## 4. Gauge

**Suitable for:** Displaying a current value within a range (performance score, health rating).

### Calculation

Semi-circular arc uses `stroke-dasharray`; total arc length = π × r:

```
arc_length = π * r
filled = value / max_value * arc_length
```

### Full Example

```svg
<svg width="140" height="80" viewBox="0 0 140 80" xmlns="http://www.w3.org/2000/svg">
  <!-- Background arc -->
  <path d="M 15,70 A 55,55 0 0,1 125,70" fill="none" stroke="var(--muted)" stroke-width="10" opacity="0.2" stroke-linecap="round"/>
  <!-- Filled arc (75%) -->
  <path d="M 15,70 A 55,55 0 0,1 125,70" fill="none" stroke="var(--chart-series-1)" stroke-width="10" stroke-linecap="round"
    stroke-dasharray="129.6 172.8"
  />
  <!-- Center value -->
  <text x="70" y="68" text-anchor="middle" font-size="20" font-weight="600" fill="var(--ink)">75</text>
  <text x="70" y="78" text-anchor="middle" font-size="9" fill="var(--muted)">/100</text>
</svg>
```

---

## 5. Mini Stacked Bar

**Suitable for:** Showing the composition of one compact item. Use ECharts for multiple columns, time periods, axes, legends, or comparisons.

### Full Example

```svg
<svg width="200" height="44" viewBox="0 0 200 44" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="14" width="200" height="12" rx="6" fill="var(--muted)" opacity="0.18"/>
  <rect x="0" y="14" width="96" height="12" rx="6" fill="var(--chart-series-1)"/>
  <rect x="96" y="14" width="64" height="12" fill="var(--chart-series-2)"/>
  <rect x="160" y="14" width="40" height="12" rx="6" fill="var(--chart-other)"/>
  <text x="0" y="40" font-size="9" fill="var(--muted)">A 48%</text>
  <text x="96" y="40" font-size="9" fill="var(--muted)">B 32%</text>
  <text x="160" y="40" font-size="9" fill="var(--muted)">Other 20%</text>
</svg>
```

---

## Container Styling

Use a neutral card container around mini charts. The surface uses `--bg2`; colors stay on marks and legend dots.

```html
<div style="background:var(--bg2); border:1px solid var(--rule); border-radius:var(--radius-md); padding:var(--space-4);">
  <div style="font-size:12px; color:var(--muted); margin-bottom:var(--space-2);">Monthly Active User Distribution</div>
  <!-- SVG chart goes here -->
  <div style="display:flex; gap:var(--space-3); margin-top:var(--space-2); font-size:11px; color:var(--muted);">
    <span><span style="color:var(--chart-series-1);">●</span> Product A</span>
    <span><span style="color:var(--chart-series-2);">●</span> Product B</span>
  </div>
</div>
```

## Notes

- **When data exceeds 3 simple values, use ECharts — do not use SVG**
- All `fill`/`stroke` values use CSS variables for theme compatibility
- Keep SVG container surfaces neutral; use chart tokens only on data marks and legend dots
- Use `--chart-positive`, `--chart-warning`, and `--chart-negative` only for real semantic states
- The `rx` attribute rounds rectangle corners for a softer appearance
- Use `text-anchor="middle"` to center-align text

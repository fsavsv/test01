# Chart Contract

Use this contract for every quantitative chart in an HTML report. It extends
`references/color-system.md`: the report chooses one active color preset, then
all charts in that report inherit the matching chart palette from the same
preset.

## Chart Admission And Density

Re-evaluate every planned chart before authoring it. A chart is admitted only
when the reader needs to see a quantitative pattern such as trend, distribution,
ranking, composition, variance, or correlation and that pattern is materially
clearer than prose, an inline metric, or a compact table.

Choose the least complex adequate form:

- use prose for explanation, interpretation, causality, and qualitative findings;
- use an inline metric or metric row for one or a few headline numbers;
- use a compact table when exact values or a small structured comparison matter;
- use a chart when visual comparison reveals a pattern that is otherwise costly
  to understand.

Delete, combine, or replace a planned chart when it repeats another chart's
conclusion, merely decorates a section, lacks a distinct analytical question, or
turns a small exact dataset into a large visual without improving comprehension.

For PRDs, research reports, and whitepapers, use no more than one major chart per
`h2` by default. This is a ceiling, not a quota; zero charts is valid. Data-insight
reports and dashboards may exceed it when each chart answers a different
question. Do not place more than two analytical visual modules consecutively;
insert prose synthesis, interpretation, or a section conclusion before the next
visual. Optional decorative Intro media does not count toward analytical visual
density; neither do the permitted non-informational Intro CSS shapes. Evidence
images and analytical modules do.

An explicit user request for a dashboard or a supplied chart-led reference may
override these density defaults, but it does not override the distinct-question,
non-duplication, or data-integrity requirements.

## Decision Order

1. Select the report color preset from `references/color-system.md` before
   writing chart CSS or JavaScript.
2. Use one chart palette per report. Every chart reads the same
   `--chart-*` variables from `:root`.
3. Use chart colors only on data marks, legends, tooltip markers, and
   chart-specific focus states.
4. Use semantic chart colors only when the encoded data is explicitly status,
   risk, health, or positive/negative direction.
5. If the data needs more categories than the palette supports, change the
   structure before adding more colors.

## Palette Contract

Each report preset must provide the canonical chart roles defined in
`references/color-system.md`: four peer-series roles, other, two bounded
accents, positive/warning/negative, grid, axis, label, and tooltip background.
Do not redeclare values here or in the scaffold; inject the selected canonical
token block once, then consume those roles in chart code.

The first seven tokens are preset-specific. The semantic status tokens are
stable by default so that positive, warning, and negative meaning stays
recognizable across report styles.

Do not treat any one hue as the default chart effect. Business Blue, Product
Teal, Warm Editorial, Rose Pink, TraeWork Purple, and custom content-derived
palettes all share the same roles and usage rules; only token values change.
Rose Pink is used only for cute, romantic, lifestyle, soft consumer,
celebratory, or playful report cues. Internal scaffold tokens are not a chart
palette choice. Preset chart values should come from the curated palette catalog
in `references/color-system.md`, not from ad-hoc local color picking.

## Palette Use

- Single-series charts use `--chart-series-1`.
- Two peer series use `--chart-series-1` and `--chart-series-2`; the pair must
  be visibly separated.
- Three peer series use `--chart-series-1` through `--chart-series-3`.
- Four peer series may use `--chart-series-4` as the last allowed peer color.
- Long-tail, residual, low-priority, or grouped overflow categories use
  `--chart-other`.
- `--chart-accent` and `--chart-accent-2` are only for categories that are
  meaningfully different from ordinary peer comparison.
- `--chart-positive`, `--chart-warning`, and `--chart-negative` are only for
  explicit status, risk, health, or positive/negative direction.
- Category labels such as "success", "failed", "blocked", "accepted", or
  "rejected" do not automatically make a chart semantic. Use semantic colors
  only when the chart itself is a status/risk view.

If a chart needs more than four peer series, use Top N + `--chart-other`, small
multiples, faceting, or a table. Do not expand into ad-hoc category colors,
rainbow palettes, matplotlib-style maps, or unrelated preset colors.

## Same-Report Consistency

All charts in one report must share the same active palette:

- Read chart tokens once near the top of `assets/charts.js`.
- Reuse the same `chartSeries`, `chartOther`, `chartAccent`,
  `chartAccent2`, `success`, `warning`, and `danger` variables for every chart.
- Do not define one local `color: [...]` array for one chart and a different
  array for another chart.
- Legend, tooltip, label, and series-mark configurations for the same series must
  reference the same token.
- If a chart requires a documented exception, explain it in a nearby comment and
  keep the exception local to that chart.

## Surfaces

Chart color belongs in the chart body, not the report shell.

- Chart figures, cards, panels, and frames use page/report surfaces:
  `--bg`, `--bg2`, `--page-surface`, `--page-border`, and `--rule`.
- Do not use `--chart-series-*`, `--chart-accent`, or semantic status colors as
  card fills, section backgrounds, quote backgrounds, buttons, or decorative
  containers.
- If a chart panel needs focus, use a neutral fill and neutral border, then put
  accent on the figure title, key value, data mark, label, or marker. Do not use
  an accent or gradient border on the chart container.

## Shape And Rhythm

Use these as default chart-shape values unless the chart type requires a
documented exception:

| Element | Default |
|---|---|
| Chart figure/module radius | `12px` / `var(--radius-lg)` |
| Tooltip, tag, light control radius | `8px` / `var(--radius-md)` |
| Legend dot / tooltip marker radius | Circular, `999px` / `var(--radius-pill)` |
| Bar corner radius | `4px`; use `3px` for very thin bars |
| Stacked bar corners | Round only the exposed outer ends |
| Line width | `2px` default; up to `3px` for highlighted series |
| Point radius | `3px` to `4px`; hover `5px` to `6px` |
| Scatter point radius | Bounded scale, usually `4px` to `10px` |
| Grid line width | `1px`, lighter than a normal divider |
| Axis/label text | `--chart-axis` / `--chart-label`, 11-12px when dense |
| Chart height | 320-420px default; large analytical charts may use 480-560px |

Use round line caps for SVG sparklines, gauges, and small trend lines. Keep
rounded corners restrained: chart marks can be soft, but the report should not
look like a consumer card UI.

## ECharts Rules

- Use ECharts for quantitative charts.
- Initialize with `echarts.init(el, null, { renderer: 'svg' })`.
- Use `animation: false`; reports are static documents.
- Include tooltip with `appendToBody: true`.
- Add a resize listener for every chart instance.
- Keep chart initialization in `assets/charts.js`, not inline HTML scripts.
- Keep the chart useful when data is empty: show an explicit empty state instead
  of a blank container.

## Interaction And Labels

- Every chart needs a visible title or caption.
- Every chart should have a nearby one-sentence takeaway in the report prose.
- Use legends only when color is needed to decode series. If there are three or
  fewer series, inline legend placement is usually enough; more than three
  series should use a bottom or side legend area.
- Tooltip marker configuration must reuse the corresponding series color token.
- Long labels should be abbreviated on axes and shown fully in tooltip or table
  text.
- Null values in time series should remain gaps unless zero is semantically
  correct.
- Negative values must use chart types that support negative ranges; do not use
  pie, donut, funnel, or stacked-share charts for negative data.

## Acceptance Checks

Static acceptance checks validate configuration and source consistency. They do
not authorize browser use or prove runtime rendering.

- One active report preset is selected before chart authoring.
- All charts read the same `--chart-*` variables from `:root`.
- No chart uses hardcoded category colors or default library palettes.
- No ordinary peer category uses semantic status colors.
- No report surface uses chart colors as a fill.
- Shape values use the report radius and spacing tokens.
- Every chart container declares a non-zero `height` or `min-height`.
- The ECharts library script appears before `assets/charts.js` in document order.
- Each chart's initialization runs after its DOM container exists, either through
  end-of-body script order or an explicit DOM-ready guard.
- Legend, tooltip, label, and series-mark configurations reference the same token
  for each series.
- Dense, long-label, empty, null, and too-many-category cases are handled by
  source structure and explicit fallback logic, not by visual compression.

Rendered legend, tooltip, label, and mark behavior remains `NOT RUN` unless the
user explicitly requests the optional isolated rendered QA in
`references/qa-checklist.md`. Do not open or control the user's browser to prove
these checks.

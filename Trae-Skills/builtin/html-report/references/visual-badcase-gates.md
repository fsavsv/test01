# Visual Badcase Gates

Use this file as the authoring and static-review visual gate for file-like HTML
reports. These rules prevent known bad cases in generated report source. Rules
that depend on rendered geometry or interaction are not proven by static review
and do not authorize opening or controlling a browser.

## Priority 0 Gates

### V0-1 Page Background

- Default file-like reports use a neutral page background.
- Avoid pure black, neon blue-purple, full-page radial glow, and decorative
  gradients unless the user explicitly asks for a campaign or poster style.
- Dark mode is allowed only when the background is near-black, not `#000`, and
  content contrast remains readable.
- A `contained` Intro may use `--page-brand-soft` or `--page-surface-muted`.
  A qualified `integrated` or `stage` Intro may instead use a quiet page-token
  surface or full-surface media with a functional page-token scrim. This does
  not permit chart, status, or saturated colors on large surfaces.

### V0-1A Active Palette

- Reports choose one active palette from `references/color-system.md`: explicit
  user or brand direction first, then an accepted Hero, and only without a Hero,
  prompt and content cues. Internal scaffold tokens are allowed only before final
  palette selection; they are not an active palette or preset.
- Do not make any one hue, including purple or blue, the universal default
  visual effect.
- Rose Pink is allowed only for cute, romantic, lifestyle, soft consumer,
  celebratory, or playful cues. It is not the fallback for generic reports.
- TraeWork Purple is allowed only when the user explicitly requests TraeWork
  branding, provides a purple brand direction, or asks for that preset.
- Page colors and chart colors must stay in separate token layers while coming
  from the same active palette.
- Presets must use the curated palette set. Treat ad-hoc muddy yellow-brown,
  olive, dark teal, or gray-heavy category palettes as a visual bad case unless
  explicit user/brand direction or an accepted Hero supplies that cue.

### V0-1B Opening Intro

- A report Intro may use `contained`, `integrated`, or `stage` composition while
  remaining report-like. Promotional slogans, strong landing-page calls to
  action, an unexplained empty stage, and fixed `height: 100vh`, `100dvh`, or
  `100svh` openings are blocking bad cases.
- No layout modifier means `contained`. Using both
  `.report-intro--integrated` and `.report-intro--stage` is a blocking source
  error. `.report-intro--with-media` and `.report-intro--plain` are orthogonal
  states and do not select a layout mode.
- `contained` and `integrated` must include the one- or two-sentence conclusion
  summary in the Intro. A `stage` may omit it only when the immediately following
  `main > section#report-overview` places `.report-overview__summary` immediately
  after its heading and before evidence content.
- For one explicitly named film or media work, product, or brand, a silent text-
  only Intro without the bounded official lookup
  or a valid fallback is a blocking bad case. The image remains conditional.
- `integrated` requires accepted media covering the Intro surface, explicit
  desktop and mobile focal positions, a declared text-safe area, and a functional
  page-token scrim. Full-surface media is not itself a bad case; arbitrary media
  dominance without those controls is.
- A `stage` may be media-backed or purely typographic. Its source must use
  content-safe, bounded minimum geometry and reset that minimum for short
  landscape viewports, print, and forced-colors; motion or scroll effects must
  have a `prefers-reduced-motion` fallback.
- Accepted decorative official media carries no essential information and
  preserves complete reading order when removed.
- Broken, low-quality, poorly cropped, or readability-reducing Intro media must
  be removed without a placeholder. An `integrated` Intro then falls back to
  `contained`; a `stage` may remain typographic.
- A default image-free `contained` Intro may use at most two optional,
  low-emphasis flat CSS
  geometric shapes. They must use only page tokens, stay outside normal flow,
  convey no information, and use no gradient, shadow, or animation. More than
  two shapes, reserved layout space, or combining them with accepted Intro media,
  integrated, stage, or plain treatments is a blocking bad case; omit them for
  explicitly minimal or formal treatments.

### V0-1C Content Container Borders

- Cards, callouts, quotes, chart panels, recommendation blocks, and other content
  containers must not use an accent top, left, or full border, a border gradient,
  or a colored decorative strip.
- Use whitespace, a neutral rule, or a quiet surface to separate content. Keep
  accent on text, icons, key values, controls, or data marks.
- This gate does not prohibit button, input, selection, keyboard-focus, or other
  necessary interaction states.

### V0-2 Architecture And Process Diagrams

- Architecture, topology, flow, and process diagrams must be vector-first:
  Mermaid, Graphviz, PlantUML, HTML/CSS grid, or explicitly justified inline SVG.
- Prefer compact source-first diagrams with automatic layout. Treat hand-written
  SVG for every simple diagram as a generation bad case unless the user requests
  custom vector art.
- Do not use AI-generated bitmap images as the primary architecture diagram.
- Diagram text must be selectable/searchable where possible, or the image must
  be zoomable.
- Diagram source must declare readable node sizing, short labels, complete legend
  relationships, and complexity within `references/diagram-contract.md` limits.
  Missing labels, disconnected source references, or explicitly tangled manual
  connector paths are blocking static issues. Actual rendered readability and
  automatic-layout crossings remain `NOT RUN` under the default QA boundary.

### V0-3 Tables

- File-like reports must not rely on embedded horizontal scrollbars for core
  reading.
- Wide tables should be full-width, split into smaller semantic tables, turned
  into definition lists, or converted to responsive label/value cards.
- Raw data audit tables may scroll only when the table is explicitly positioned
  as a data appendix and uses the full report width.

## Priority 1 Gates

### V1-1 Typography Families

- A report should use at most two font families: one Sans for most content and
  one Mono for code, tags, IDs, or aligned technical values.
- Serif, italic, display, and decorative fonts are allowed only as a deliberate
  report personality choice. Do not mix them casually inside ordinary PRD or
  research report sections.
- Chinese content must include CJK system fallbacks.

### V1-2 Type Scale

- Body text is at least 14px.
- A report should use at most four text-size roles: caption, body, section, and
  display/title.
- A single visible component should normally use no more than two size roles.
- Avoid title/meta pairings where one side is visually five times larger than
  the other.

### V1-3 Element Purpose

- Every card, metric, callout, tag, icon, table, chart, evidence image, and diagram
  must have a clear information role. The only non-informational exceptions are
  qualified decorative Intro media or up to two permitted default-contained
  Intro CSS shapes; both remain non-essential.
- Do not use cards as generic decoration.
- Do not nest cards inside cards.
- Do not add icons or tags that do not encode type, state, category, owner, or
  priority.

### V1-4 Information Density

- Do not add a chart merely to decorate a chapter or create visual variety.
- Long-form PRDs, research reports, and whitepapers stay prose/table-led; one
  major chart per `h2` is a default ceiling, not a quota.
- Do not place more than two analytical charts, diagrams, or evidence images in
  sequence without prose synthesis, interpretation, or a section conclusion.
- Decorative Intro media and permitted Intro CSS shapes do not count toward
  analytical visual density; evidence screenshots and analytical visuals do.
- Merge or remove visuals that repeat the same analytical question or conclusion.
- Chart-led data-insight reports and dashboards may use higher density when every
  visual has a distinct decision or analytical role.

## Priority 2 Gates

### V2-1 Color Semantics

- Use the active report palette consistently. Do not remap one chart or section
  into another palette unless the user explicitly names another brand, provides
  a brand color, or asks for another visual style.
- Use one primary accent family and, at most, one secondary accent family.
- Use success, warning, and danger only when the content has real status
  meaning.
- When many categories are needed, derive chart colors from the report chart
  tokens, group long tails as Other, or use small multiples.

### V2-2 Balanced Grid Layout

- Multi-column rows should use 12-column spans: 12, 6, 4, or 3.
- Cards in one row must fill the row. If a row leaves 25% or more empty width,
  merge the item into the previous row, make it full-width, or rebalance the
  grid.
- Continuous blank regions larger than about 200px by 200px must be filled,
  collapsed, or removed, except for intentional breathing room inside a selected,
  content-led Intro mode. A `stage` still needs a content or composition reason;
  do not reserve blank space for absent media.
- Tables with four or more columns must not be placed inside narrow card grids
  or two-column layouts.

## Final Gate

Before finishing a report, apply all source-checkable V0 rules through static
inspection. If one fails, revise the HTML and rerun the affected static checks
before delivery.

Do not open, navigate, inspect, or control the user's browser for this gate.
Rendered geometry, clipping, contrast, readability, and interaction checks stay
`NOT RUN` by default. They may be evaluated only when the user explicitly asks
for the separate optional rendered QA defined in `references/qa-checklist.md`,
using an isolated test browser rather than the user's browser or session.

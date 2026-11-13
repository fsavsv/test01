# Element Usage Contract

Use this contract to decide which report element to use and how it should be
structured. The goal is clear evidence, not decorative component variety.

## Core Rule

Every visible element must have a job: conclusion, evidence, comparison, risk,
recommendation, navigation, or source context. Do not add cards, icons, tags, or
colored panels only to make the page look richer. The only bounded decorative
exception is up to two low-emphasis flat CSS shapes in an image-free default
`contained` Intro; they support composition, convey no information, and may
always be omitted.

## Element Matrix

| Element | Use When | Required Structure | Visual Rules | Forbidden |
|---|---|---|---|---|
| Report Intro | A report needs a clear opening | One `h1`; `contained` and `integrated` include a 1-2 sentence conclusion summary, while `stage` may put it first in the immediate `#report-overview`; optional source-backed metadata or up to three highlights | Select `contained`, `integrated`, or `stage`; keep the text layer centered and use qualified media only through the orthogonal media state | Conflicting mode classes; unqualified compulsory media; silent eligible-media omission; fixed viewport height; unmotivated empty stage; promotional slogans or calls to action |
| Metric card | A number needs emphasis | Label, value, optional delta, one-line context | Neutral surface, strong number, color only on value/delta | Full-card status fill; number without context |
| Insight card | A conclusion needs framing | Insight title, 1-2 sentence support, optional evidence link | Neutral card with border and tight hierarchy | Generic decorative cards; nested cards |
| Callout | Risk, caveat, decision, or next step | Short label, concise body, optional owner/date | Neutral or soft accent background, neutral border, optional accent icon | Saturated blocks; accent container border; many callouts in a row |
| Quote | Direct evidence or stakeholder voice | Quote text, source/context | Neutral surface, readable italic optional | Accent or gradient quote bar; decoration without evidence |
| Recommendation block | Final or section-level action | Recommendation, reason, impact, next step | Clear grouping, optional accent text/icon, responsive columns only for comparable items | Accent container border; vague "recommended" badge without rationale |
| Feature list | Scannable capabilities or findings | Title + short description per item | Border-bottom rows or compact grid | Turning every row into a heavy card |
| Table | Precise comparison or structured facts | Caption/title, aligned columns, wrapping cells | Full width for 4+ columns, neutral header | Core horizontal scroll; table inside two-column grid |
| Chart | Quantitative data pattern | Figure title, chart, nearby conclusion, source if needed | ECharts, one active chart palette, chart tokens on marks, neutral figure surface | Inline chart JS; hardcoded palette; mixed palettes; chart without title |
| Diagram | Structure, process, architecture | Caption, readable nodes, clear connectors | SVG for simple, Graphviz/PlantUML for complex | AI bitmap as primary architecture diagram |
| Tag / badge | State, category, owner, or priority | Short label, clear meaning | Small, restrained, semantic only when meaningful | Decorative tag clouds; status color for ordinary category |
| Icon | Clarify type, state, or action | Paired with label or clear context | 14-16px default, currentColor or semantic token | Random colored icons; icons replacing essential text |
| Image / screenshot | Real product, place, artifact, or restrained film/media, product, or brand Intro context | Evidence: descriptive alt, caption/source, relative asset path. Decorative Intro media: `alt=""`, `aria-hidden="true"`, relative path | Neutral 1px border for evidence screenshots; qualified Intro media may fill an `integrated` or media-backed `stage` surface behind a functional page-token scrim | Text baked into generated images; blurred filler imagery; decoration presented as evidence; media without source, focal point, or text-safe area |

## Report Intro

- Choose one layout mode before styling: no modifier means `contained`;
  `.report-intro--integrated` and `.report-intro--stage` are mutually exclusive.
  `.report-intro--with-media` describes media presence and
  `.report-intro--plain` removes optional decoration; neither chooses layout.
- Formal research, PRD, data, and technical reports default to `contained`.
  Generic, multi-subject, explicitly image-free, and reports outside the named-
  subject trigger normally use this image-free mode.
- Use `integrated` only when one qualified subject image can cover the Intro
  surface, preserve an explicit desktop and mobile text-safe area, and support
  the report's narrative. It still includes the conclusion summary in the Intro.
- Use `stage` for a justified topic, brand, film, portfolio, or explicit Landing
  Cover treatment. It may be media-backed or purely typographic. If its summary
  is omitted from the Intro, the immediately following
  `main > section#report-overview` places a one- or two-sentence
  `.report-overview__summary` immediately after its heading and before evidence.
- For one explicitly named film or media work, product, or brand, apply the core
  bounded lookup and use accepted official media;
  it must not contain required evidence, labels, or conclusions.
- Multi-item comparisons default to a neutral no-media Intro unless every subject
  can be represented with equal visual weight.
- In the default image-free `contained` mode, up to two optional low-emphasis
  flat CSS geometric shapes
  may support composition. They use page tokens, stay outside normal flow, and
  do not encode evidence, category, status, or hierarchy. Do not combine them
  with accepted Intro media; omit them for integrated, stage, plain, explicitly
  minimal, or formal treatments.
- Put evidentiary product screenshots in a body `<figure>` with descriptive alt,
  caption, and source. If `integrated` media is missing or unsuitable, remove it
  and fall back to `contained`. A `stage` may instead remain as a typographic
  cover. Never add a placeholder or block the report on optional media.

## Metric Cards

- Use for top-line KPI, risk count, progress, cost, time, or volume.
- A metric card must tell the reader what the number means.
- Use tabular numerals when values align across cards.
- Keep one row visually balanced; if a metric row leaves 25% or more empty
  width, rebalance or make the final item full width.
- Do not use chart series colors as card backgrounds.

## Cards And Surfaces

- Cards are containers for conclusions, evidence, or actions.
- Default card surface is white or `--page-surface` with `--page-border`.
- Use `12px` radius for report modules and cards.
- Avoid shadows; use borders and whitespace first.
- Do not put cards inside cards. If hierarchy is needed, use headings, dividers,
  definition rows, or nested lists inside one card.

## Callouts And Quotes

- Use callouts sparingly for risk, decision, caveat, recommendation, or
  important context.
- A callout should not repeat the paragraph immediately before it.
- Use semantic color only when the callout has semantic state.
- Quotes should preserve source context and should not become a generic
  decoration style.
- Cards, callouts, quotes, and recommendation blocks may use a neutral border,
  but not an accent top, left, or full border, a border gradient, or a colored
  decorative strip. Controls and focus states are outside this container rule.

## Tables

- A table needs a visible title or caption.
- Use tables for exact values, structured comparisons, definitions, schedules,
  risks, and source lists.
- When the first cell is a row label, use `<th scope="row">` and emphasize that
  semantic header. Do not bold every first column by position.
- 1-4 columns: normal table with wrapping cells.
- 5-8 columns: full-width table with compact copy and consistent alignment.
- More than 8 columns: split, simplify, convert to label/value cards, or move raw
  detail to an appendix.
- On mobile, important tables should become stacked cards or definition lists.

## Charts

- Use ECharts for quantitative charts.
- Every chart needs a figure title and a nearby one-sentence takeaway.
- Follow `references/chart-contract.md` for palette, geometry, tooltip, legend,
  and edge-case rules.
- All charts in one report use the same active chart palette.
- Use chart tokens only on marks, legends, tooltip markers, and chart focus
  states.
- Use `--chart-positive`, `--chart-warning`, and `--chart-negative` only when the
  metric is truly directional or status-based.
- If data is missing, show an explicit empty state instead of a blank container.

## Diagrams

- Use diagrams for relationships, flow, architecture, process, or hierarchy.
- Node labels should be short and readable at normal report width.
- Use one shape language per diagram unless shapes encode different semantics.
- Reserve accent color for the primary path or selected node.
- Split diagrams when crossing connectors or dense labels reduce readability.

## Tags, Icons, And Labels

- Tags should be short and meaningful.
- Icons should support recognition, not replace required explanatory text.
- Dense reports default to 14-16px icons.
- Avoid introducing new icon colors outside the current token system.

## Acceptance Gates

- No decorative card grid without information hierarchy.
- No card-inside-card layouts.
- No core table in a narrow column or multi-column card grid.
- No chart, evidence image, diagram, or table without title/caption. Decorative
  Intro media instead requires empty alt text and no informational dependency.
- No full-card color fill unless the element is explicitly a status banner.
- No chart, status, or saturated color across a large surface; the only opening
  exceptions are the selected Intro mode's quiet page-token surface or qualified
  full-surface media with a functional page-token scrim.
- Permitted Intro CSS shapes belong only to the default image-free `contained`
  mode, are optional and non-informational, use only page tokens, and must not
  use gradients, shadows, or animation.
- No icons or tags that do not encode type, state, category, owner, or priority.

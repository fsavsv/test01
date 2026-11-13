# Layout Contract

This contract covers file-like HTML reports: PRDs, research reports,
whitepapers, proposals, and analysis documents. The goal is readable documents,
not demo dashboards.

## Page Rhythm

- Pick one report rhythm: single centered column, content plus sidebar TOC, or
  content plus margin notes.
- Do not mix multiple layout systems in the same report.
- Long-form content defaults to a max width of 880px to 1080px. Wider bands are
  allowed for charts, image galleries, and full-width tables.
- A full-width Intro shell is an opening exception, not a second body rhythm. Its
  real HTML content still aligns to the reading grid; do not create full bleed
  with `100vw`, negative margins, or another technique that risks page overflow.

## Report Type To Structure

Choose the structure before placing content:

| Report Type | Default Structure | Notes |
|---|---|---|
| PRD / research report / whitepaper | Single centered column | Prose and evidence readability come first |
| Data insight / retrospective | Single column with occasional wide figures | Use local full-width bands for major charts only |
| Dashboard-like summary | Summary strip, metric grid, then chart/table sections | Keep it report-like, not a dense workspace |
| Long multi-chapter document | Content plus sidebar TOC | TOC is navigation, not a second content system |
| Editorial / portfolio / named media or brand feature | Centered body after a controlled Intro mode | Use `integrated` or `stage` only when the mode criteria are met |
| Appendix / raw detail | Full-width tables or split detail sections | Label raw data appendices explicitly |

Do not default every report to a card grid. Use cards only when they improve
scanning, comparison, or emphasis.

## Opening Intro Modes

Start report-like outputs with one Intro that uses landing-page clarity without
adopting promotional copy or calls to action. Core selects one mode by content
purpose and usable material; Style controls the mode's typography, alignment,
surface detail, focal position, and functional scrim values.

### Shared Interface And Semantics

Use the mode-ready scaffold structure:

```html
<article class="page">
  <header class="report-intro">
    <div class="report-intro__surface">
      <div class="report-intro__content">
        <h1>Report title</h1>
        <p class="report-intro__summary">Conclusion-led summary.</p>
      </div>
    </div>
  </header>
  <div class="page__content">
    <main>...</main>
    <footer>...</footer>
  </div>
</article>
```

- No layout modifier means `contained`. Add at most one of
  `.report-intro--integrated` or `.report-intro--stage` to the outer `header`.
- `.report-intro--with-media` and `.report-intro--plain` are independent state
  modifiers. They do not select layout and may not make `integrated` and `stage`
  coexist.
- Keep the page's single `h1`, metadata, and every conclusion as real HTML.
  Media never carries the only title, label, evidence, or conclusion.
- `contained` and `integrated` require `.report-intro__summary` in the Intro.
  `stage` may omit it only when the first direct section in `main` is the
  immediate Overview:

```html
<main>
  <section id="report-overview">
    <h2>Overview</h2>
    <p class="report-overview__summary">Conclusion-led summary.</p>
  </section>
  <!-- detailed evidence follows -->
</main>
```

- The outer Intro shell may span the page; `.report-intro__content` still aligns
  to the report grid. Removing media must preserve correct reading order.
- Include only the CSS for the selected non-default mode. Do not copy unused
  mode blocks into every generated report.

### Mode Selection

| Mode | Select when | Required fallback |
|---|---|---|
| `contained` | Formal research, PRD, data, technical, long-title, dense-metadata, or no strong opening cue | This is the no-modifier default |
| `integrated` | A narrative or single-subject report has accepted media, a declared text-safe region, and benefits from a full-width background composition | Missing or unsafe media becomes `contained` |
| `stage` | Editorial, portfolio, film/media, brand feature, or an explicit landing-cover direction benefits from a deliberate opening floor | It may remain as a no-media typographic stage |

An explicit user request or supplied visual direction overrides automatic
selection when shared semantics and accessibility remain valid. Otherwise use
the table; do not randomize modes or let Style select a different content mode.

### Contained

- Preserve the scaffold's centered surface, 48px desktop padding, 24px mobile
  padding, content-driven height, and normal reading emphasis.
- An image-free contained Intro may use up to two optional flat CSS shapes outside
  normal flow. Suppress them for plain, media, integrated, and stage states.
- `contained + with-media` may use an edge, split, or subdued background treatment
  suited to the asset. Do not impose one global content/media percentage. Declare
  the crop and keep the summary readable after the media is removed.

### Integrated

`integrated` requires `.report-intro--with-media`. The accepted media may cover
the entire Intro surface and participate in the composition rather than remain a
fixed side image. Use the following geometry contract, adapting direction and
stops to the declared text-safe region:

```css
.report-intro--integrated .report-intro__surface {
  position: relative;
  isolation: isolate;
  overflow: hidden;
  inline-size: 100%;
  max-inline-size: none;
  margin: 0;
  border-radius: 0;
  padding: 0;
  background: var(--page-brand-soft, var(--page-surface-muted, var(--bg2)));
}
.report-intro--integrated .report-intro__content {
  position: relative;
  z-index: 2;
  inline-size: min(calc(100% - 2rem), var(--max));
  margin-inline: auto;
  padding-block: clamp(3rem, 9vw, 8rem);
}
.report-intro--with-media:is(
  .report-intro--integrated,
  .report-intro--stage
) .report-intro__media {
  position: absolute;
  inset: 0;
  z-index: 0;
  inline-size: 100%;
  block-size: 100%;
  object-fit: cover;
  object-position: var(--intro-media-position, center);
  pointer-events: none;
}
.report-intro--with-media:is(
  .report-intro--integrated,
  .report-intro--stage
) .report-intro__surface::after {
  content: "";
  position: absolute;
  inset: 0;
  z-index: 1;
  background: linear-gradient(
    90deg,
    var(--page-brand-soft, var(--page-surface-muted, var(--bg2))) 0%,
    var(--page-brand-soft, var(--page-surface-muted, var(--bg2))) 42%,
    transparent 82%
  );
  pointer-events: none;
}
```

The gradient is a functional contrast scrim, not decoration. It must use page
tokens, cover the actual text region with a near-solid surface, and change
direction or stops when the safe region moves. Declare desktop and mobile
`object-position`; when no crop protects both subject and text, use a separate
mobile composition, hide the media, or fall back to `contained`.

### Stage

`stage` is a deliberate first floor, not a fixed-height slide. It may be
typographic or combine with accepted media. Use this bounded, growable geometry:

```css
.report-intro--stage .report-intro__surface {
  position: relative;
  isolation: isolate;
  overflow: hidden;
  inline-size: 100%;
  max-inline-size: none;
  margin: 0;
  border-radius: 0;
  padding: 0;
  block-size: auto;
  min-block-size: clamp(36rem, 88svh, 58rem);
  display: grid;
  align-items: center;
  background: var(--page-brand-soft, var(--page-surface-muted, var(--bg2)));
}
.report-intro--stage .report-intro__content {
  position: relative;
  z-index: 2;
  inline-size: min(calc(100% - 2rem), var(--max));
  margin-inline: auto;
  padding-block: clamp(4rem, 10vw, 9rem);
}
@supports not (height: 1svh) {
  .report-intro--stage .report-intro__surface {
    min-block-size: clamp(36rem, 88vh, 58rem);
  }
}
```

- Never use `height: 100vh`, `height: 100dvh`, or `height: 100svh`. Long titles,
  metadata, text zoom, and translations must increase the surface height.
- When stage media is present, use the same full-surface media stack and
  functional text scrim as `integrated`; do not make essential content depend on
  the image.
- A continue cue is optional. If actionable, use a real link to
  `#report-overview` with visible focus and a text label; if decorative, hide it
  from assistive technology and do not style it as a control.

### Responsive, Motion, And Print Fallbacks

Every selected non-default mode declares these source-level fallbacks:

```css
@media (max-width: 768px) {
  .report-intro--integrated .report-intro__content,
  .report-intro--stage .report-intro__content {
    inline-size: min(calc(100% - 2rem), var(--max));
  }
}
@media (max-height: 600px) and (orientation: landscape) {
  .report-intro--stage .report-intro__surface { min-block-size: auto; }
}
@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; }
  .report-intro *, .report-intro *::before, .report-intro *::after {
    animation: none !important;
    transition: none !important;
  }
}
@media print, (forced-colors: active) {
  .report-intro--stage .report-intro__surface { min-block-size: auto; }
  .report-intro__media,
  .report-intro__continue,
  .report-intro--with-media:is(
    .report-intro--integrated,
    .report-intro--stage
  ) .report-intro__surface::after { display: none !important; }
}
```

At narrow widths, preserve title-first source order, stack metadata, allow text
to wrap, and change or remove media rather than shrinking the desktop composition.
Static QA confirms that these rules exist; rendered crop, contrast, and viewport
readability remain `NOT RUN` unless separately authorized.

### Ownership Boundary

- Core owns mode selection, semantic slots, summary placement, local source and
  fallback integrity, accessibility, reading order, and responsive escape paths.
- Style owns typography, alignment within the safe region, spacing values within
  the mode envelope, surface texture, focal position, and functional scrim
  direction or strength. Style may not switch modes or remove Core information.

## Heading Hierarchy

- `h1`: report title, once per page.
- `h2`: chapter or major section.
- `h3`: subsection.
- `h4`: local module title inside a section.
- Card titles must not visually exceed normal `h3` scale.
- A single visible component should use no more than two text-size roles unless
  it contains a chart or table with labels.
- Do not use opening-title scale type inside metric cards, callouts, or ordinary
  content modules.

## Spacing Rhythm

- Major sections: 48px or more between sections.
- Modules inside a section: 24px to 32px.
- Groups inside cards: 12px to 16px.
- Tight inline groups: 4px to 8px.
- Captions stay close to the figure they describe.
- Use whitespace before borders; use borders before shadows.

## Grid Rules

- Use a 12-column mental model.
- Allowed spans are 12, 6, 4, and 3.
- Avoid 5/7, 3/9, or 2/10 layouts unless the content has a clear reason.
- Rebalance any row that leaves 25% or more empty width.
- Do not place unrelated element types in one row only to fill space.
- Metric grids should keep card heights stable and collapse to one column on
  mobile.

## Tables

- Core reading tables should not force horizontal scrolling.
- Tables with 1-4 columns can remain normal tables with wrapping cells.
- Tables with 5-8 columns must be full-width and use compact copy, wrapping
  cells, and consistent alignment.
- Tables with more than 8 columns must be restructured: split by topic, merge
  nearby columns, move raw detail to an appendix, or convert to label/value
  cards.
- On mobile, important tables become stacked cards or definition lists. Do not
  hide essential columns behind horizontal scroll.
- If a raw data appendix truly needs horizontal scroll, name it as raw data,
  place it full-width, and keep it out of narrow card/grid slots.

## Figure Layout

- Every chart, diagram, evidence image, and table needs a visible title or
  caption. Purely decorative Intro media is the exception: it uses empty alt
  text, needs no caption, and must not carry report evidence.
- Figure captions sit close to the visual they describe.
- Side-by-side figures must be comparable in size and visual weight.
- Screenshots keep their original colors and use only a neutral 1px border.

## Mobile Rules

- Collapse multi-column grids to one column at small widths.
- Keep body padding at least 16px.
- Use 24px padding inside the opening Intro on mobile and preserve the title-first
  reading order when optional media moves or crops.
- Do not let long URLs, IDs, or table labels overflow the viewport.
- Preserve the reading order; do not move critical evidence after appendix-only
  content.

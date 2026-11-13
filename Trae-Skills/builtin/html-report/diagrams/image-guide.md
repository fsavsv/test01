# Image & Diagram Guide

This directory provides the following drawing and image generation capabilities. All output is ultimately embedded in the HTML (inline `<svg>`, external `assets/charts.js` for ECharts, or `<img src="assets/...">` for rendered images), with no external CDN references.

Static image QA verifies local file integrity, metadata, paths, source records, and responsive rules. Rendered crop, contrast, narrow-width readability, and offline loading remain `NOT RUN` unless the user explicitly requests the optional isolated rendered QA in `references/qa-checklist.md`. Do not open or control the user's browser for image QA.

***

## 1. Inline SVG Diagrams (Default for Simple/Medium Diagrams)

Hand-draw SVG directly in the HTML for structural diagrams with ≤ 10 nodes. This gives full control over aesthetics and integrates with the report's design system (CSS variables for colors, responsive viewBox).

### When to Use

- Architecture diagrams, flowcharts, process diagrams with ≤ 10 nodes
- Any diagram where you want full visual control and theme integration

### Usage

1. Use CSS variables for all colors. Page containers use page/report variables such as `var(--bg2)`, `var(--ink)`, and `var(--rule)`; data marks use chart variables such as `var(--chart-series-1)` and `var(--chart-accent)`.
2. Use rounded rectangles (`rx="6"`) for nodes, clean paths for edges
3. Add arrow markers via `<defs><marker>`
4. Set `viewBox` and `width="100%"` for responsive scaling
5. Wrap in `<figure class="diagram">` with `<figcaption>`

***

## 2. Graphviz (Default for Complex Diagrams)

Use Graphviz for diagrams with > 10 nodes, dense relationships, or complex layout needs. Output is rendered to PNG via `render_graphviz.py`.

### When to Use

- Dependency graphs, large architecture maps, dense directed relationships
- Any diagram too complex for hand-drawn SVG

### Usage

1. Write a `.dot` file
2. Run: `python <skill-dir>/diagrams/render_graphviz.py input.dot <report-dir>/assets/diagram_name.png`
3. Reference via `<img src="assets/...">`. Add `data-lightbox` only when the
   rendered details are unreadable at normal report width, as described below.

***

## Optional Image Lightbox

Do not add Lightbox code merely because a report contains an image. Use it only
when at least one detailed `<img>` needs click-to-enlarge. Mark only those images
with `data-lightbox`; ordinary illustrations, decorative Intro media, ECharts,
and inline SVG do not trigger it. When needed, add the following HTML, CSS, and
script once per report. Place the script near the end of `<body>`.

```html
<img src="assets/detail.png" alt="Detailed diagram" data-lightbox>

<dialog class="image-lightbox" id="image-lightbox" aria-label="Image preview">
  <button class="image-lightbox__close" type="button" aria-label="Close image preview">&times;</button>
  <img alt="">
</dialog>
```

```css
img[data-lightbox] { cursor: zoom-in; }
.image-lightbox {
  width: 100vw;
  height: 100vh;
  max-width: none;
  max-height: none;
  padding: 2rem;
  border: 0;
  background: transparent;
}
.image-lightbox[open] { display: grid; place-items: center; }
.image-lightbox::backdrop { background: var(--ink); opacity: 0.85; }
.image-lightbox img { max-width: 90vw; max-height: 90vh; object-fit: contain; }
.image-lightbox__close {
  position: fixed;
  top: 1rem;
  right: 1rem;
  border: 0;
  background: transparent;
  color: var(--bg);
  font: 2rem/1 sans-serif;
  cursor: pointer;
}
```

```javascript
(function () {
  var box = document.getElementById('image-lightbox');
  if (!box) return;

  var preview = box.querySelector('img');
  document.querySelectorAll('img[data-lightbox]').forEach(function (image) {
    image.addEventListener('click', function () {
      preview.src = image.currentSrc || image.src;
      preview.alt = image.alt;
      if (!box.open) box.showModal();
    });
  });

  box.querySelector('.image-lightbox__close').addEventListener('click', function () {
    box.close();
  });
  box.addEventListener('click', function (event) {
    if (event.target === box) box.close();
  });
})();
```

The native dialog handles Escape. Localize the two accessible labels to match
the report language. Multiple zoomable images must share this one dialog and
script; do not duplicate the Lightbox per image.

***

## 3. ECharts (Recommended — Primary Choice for Data Visualization)

Reference `echarts.min.js` via `<script src>` in the HTML, and write all chart initialization logic in a separate external JS file (`assets/charts.js`). Charts render to SVG at runtime. No external CDN needed.

> **Use ECharts for all quantitative data visualization.** Colors must be derived from the report `:root` CSS variables. Page containers inherit page/report tokens; data marks use the chart token layer. Apply `references/chart-contract.md` before authoring charts.

### Report Token Inheritance

- Keep the chart panel/card surface neutral: use `--bg`, `--bg2`, and `--rule` for containers and figure frames.
- Use one active chart palette per report. All charts in the report must read
  and reuse the same `--chart-*` values from `:root`.
- Use `--chart-grid`, `--chart-axis`, and `--chart-label` for chart grid lines, axis lines, axis labels, and secondary chart text when available.
- Put color on the data marks: bars, lines, points, slices, heat cells, legend dots, and tooltip markers.
- Single-series charts use `--chart-series-1`.
- Peer multi-series charts use `--chart-series-1` through `--chart-series-4`.
- Long-tail or residual groups use `--chart-other`.
- `--chart-accent` and `--chart-accent-2` are reserved for genuinely different secondary categories.
- `--chart-positive`, `--chart-warning`, and `--chart-negative` are reserved for real semantic state; do not use them for ordinary categories.
- If there are more than 4 peer series, use Top N + Other, small multiples, or a table instead of extending into rainbow colors.
- If no data is available, render a visible empty state in the figure rather than a blank chart container.

### Supported Chart Types

| Type | Description |
|------|------|
| Bar / Diverging Bar | Category comparison, ranking |
| Line / Area | Time trends, multi-series comparison |
| Pie / Donut | Proportional distribution |
| Radar | Multi-dimensional comparison |
| Scatter | Distribution, correlation |
| Heatmap | Matrix density distribution |
| Sankey | Flow/conversion paths |
| Funnel | Funnel conversion |
| Gauge | Single KPI dashboard |
| Tree / Treemap | Hierarchical structure |
| Graph | Relationship network |

### Usage

1. Reference `echarts.min.js` in HTML via `<script src="./_shared/js/echarts.min.js"></script>`
2. Create container `<div>` elements in HTML
3. Write all chart logic in `assets/charts.js` (external file, NOT inline `<script>` blocks):

**HTML (index.html):**
```html
<figure class="chart-figure">
  <div id="chart-revenue" style="width:100%; min-height:400px;"></div>
  <figcaption>Quarterly Revenue</figcaption>
</figure>

<!-- At the end of <body> -->
<script src="./_shared/js/echarts.min.js"></script>
<script src="assets/charts.js"></script>
```

**External JS (assets/charts.js):**
```javascript
(function() {
  // Read theme colors once, reuse across all charts
  var style = getComputedStyle(document.documentElement);
  var ink = style.getPropertyValue('--ink').trim();
  var muted = style.getPropertyValue('--muted').trim();
  var rule = style.getPropertyValue('--rule').trim();
  var bg2 = style.getPropertyValue('--bg2').trim();
  var chartGrid = style.getPropertyValue('--chart-grid').trim() || rule;
  var chartAxis = style.getPropertyValue('--chart-axis').trim() || muted;
  var chartLabel = style.getPropertyValue('--chart-label').trim() || muted;
  var chartAccent = style.getPropertyValue('--chart-accent').trim();
  var chartAccent2 = style.getPropertyValue('--chart-accent-2').trim();
  var chartPositive = style.getPropertyValue('--chart-positive').trim() || style.getPropertyValue('--success').trim();
  var chartWarning = style.getPropertyValue('--chart-warning').trim() || style.getPropertyValue('--warning').trim();
  var chartNegative = style.getPropertyValue('--chart-negative').trim() || style.getPropertyValue('--danger').trim();
  var chartSeries = [
    style.getPropertyValue('--chart-series-1').trim(),
    style.getPropertyValue('--chart-series-2').trim(),
    style.getPropertyValue('--chart-series-3').trim(),
    style.getPropertyValue('--chart-series-4').trim()
  ];
  var chartOther = style.getPropertyValue('--chart-other').trim() || muted;

  // --- Chart: revenue ---
  var el = document.getElementById('chart-revenue');
  var chart = echarts.init(el, null, { renderer: 'svg' });
  chart.setOption({
    color: chartSeries,
    tooltip: { trigger: 'axis', appendToBody: true },
    xAxis: {
      type: 'category',
      data: ['Q1', 'Q2', 'Q3', 'Q4'],
      axisLine: { lineStyle: { color: chartGrid } },
      axisLabel: { color: chartAxis }
    },
    yAxis: {
      type: 'value',
      axisLine: { lineStyle: { color: chartGrid } },
      axisLabel: { color: chartAxis },
      splitLine: { lineStyle: { color: chartGrid, opacity: 0.3 } }
    },
    series: [{
      type: 'bar',
      data: [120, 200, 150, 80]
    }],
    animation: false
  });
  window.addEventListener('resize', function() { chart.resize(); });
})();
```

### Theme Color Integration

Chart colors **must** be read from the page `:root` CSS variables — no hardcoded color values:

| CSS Variable | Chart Usage |
|----------|----------|
| `--chart-series-1` ... `--chart-series-4` | Peer data series colors |
| `--chart-other` | Long-tail / residual category color |
| `--chart-accent` / `--chart-accent-2` | Distinct secondary category colors |
| `--chart-positive` / `--chart-warning` / `--chart-negative` | Real semantic state colors only |
| `--ink` | Title, legend text |
| `--muted` | Axis labels, secondary text |
| `--rule` | Axis lines, split lines |
| `--bg2` | Neutral tooltip or panel background |
| `--chart-grid` / `--chart-axis` / `--chart-label` | Chart grid, axis, and label colors when available |

Legend dots, tooltip dots, and visible chart marks must use the same token for the same series. Multi-series expansion stops at four peer series; beyond that, group the tail as `Other`, split into small multiples, or move the comparison into a table. Do not use different preset palettes for different charts in the same report.

### Notes

- Use SVG renderer: `echarts.init(el, null, { renderer: 'svg' })`
- **Derive colors from CSS variables** (`getComputedStyle`); hardcoded color values are forbidden
- Reuse one active chart palette for all charts in the report
- `animation: false` — reports are static documents
- `tooltip.appendToBody: true` — prevents container overflow clipping
- Add a resize listener for each chart: `window.addEventListener('resize', ...)`
- All chart logic goes in external `assets/charts.js`; do NOT use inline `<script>` blocks for chart config
- `echarts.min.js` is referenced via `<script src>`; do not use a CDN
- Keep card/panel backgrounds neutral; chart colors belong on marks, not surfaces

***

## 3. SVG Mini Charts (Extremely Simple Scenarios Only)

> ⚠️ **SVG charts are discouraged. Use ECharts for data visualization (see Section 2).** Only consider hand-written SVG when the graphic elements are extremely simple (e.g., a single progress bar, sparkline trend line, donut percentage) and data points ≤ 3. Use ECharts for any scenario involving axes, legends, or multi-series comparison.

Pure hand-written `<svg>` tags inlined directly in HTML with no external dependencies. All colors use CSS variables for theme compatibility.

### Supported Chart Types

| File | Type |
|------|------|
| `svg/mini_charts.md` | Horizontal bar, donut, progress bar, gauge, stacked column |
| `svg/sparkline.md` | Line/area/bar mini trend charts |
| `svg/world_map.md` | Geographic distribution map |

### Usage

1. Read the corresponding reference file for SVG templates and calculation formulas
2. Replace data values and inline `<svg>` tags directly in HTML
3. All `fill`/`stroke` values use CSS variables. Page containers use `var(--bg2)` / `var(--rule)`; data marks use `var(--chart-series-1)`, `var(--chart-accent)`, `var(--chart-positive)`, etc.

### Notes

- Keep the `viewBox` aspect ratio consistent with the actual rendered dimensions
- `stroke-linecap="round"` and `stroke-linejoin="round"` make lines smoother

***

## 4. Graphviz

Renders DOT language descriptions to PNG via `render_graphviz.py`, then saves the asset under the report's `assets/` directory.

### Usage

1. Write a `.dot` format graph description file
2. Call the render script to generate PNG:

```bash
python3 diagrams/render_graphviz.py input.dot output.png
```

3. Move or render the output PNG into the report's `assets/` directory.
4. Embed it via a relative path:

```html
<figure class="diagram">
  <img src="assets/dependency_graph.png" alt="Dependency Graph">
  <figcaption>Figure 2: Module Dependencies</figcaption>
</figure>
```

### Capabilities

- Directed / undirected graphs
- Automatic layout algorithms: dot (hierarchical), neato (spring), fdp (force-directed), circo (circular), twopi (radial)
- Subgraphs (subgraph / cluster)
- Rich node shapes and edge styles
- Automatic syntax error detection and location

***

## 5. PlantUML

Renders PlantUML format descriptions to PNG via `render_plantuml.py`, then saves the asset under the report's `assets/` directory.

### Usage

1. Write a `.puml` format diagram description file
2. Call the render script to generate PNG:

```bash
python3 diagrams/render_plantuml.py input.puml output.png
```

3. Move or render the output PNG into the report's `assets/` directory and embed it via a relative path, same as Graphviz.

### Capabilities

- Sequence, class, activity, component, deployment, object, and use case diagrams
- C4 model (Context / Container / Component / Code)
- Icon library support (AWS, Azure, K8s, etc.)
- Swimlanes, parallel branches, grouping
- Automatic syntax error detection and location

***

## 6. Opening Intro Media (Conditional)

This guide owns media source, local-file quality, focal point, text-safe area,
accessibility, and fallback decisions. `references/layout-contract.md` owns the
geometry of the `contained`, `integrated`, and `stage` Intro modes. Do not turn
one example crop into a global media width, text width, opacity, or placement.
Before palette lock, pass the compact intended-crop cue defined in
`references/color-system.md`.

Layout mode and media state are separate axes:

- No layout modifier means `contained`; it may be image-free or may use qualified
  media with `.report-intro--with-media`.
- `.report-intro--integrated` requires qualified full-surface media and therefore
  also uses `.report-intro--with-media`.
- `.report-intro--stage` may use qualified media or remain purely typographic.
- `.report-intro--plain` suppresses optional decoration without choosing a
  layout mode. It and `.report-intro--with-media` are not layout modifiers.

Generic, multi-subject, explicitly image-free, or reports outside the named-
subject trigger normally use a text-first, no-image `contained` Intro. An
explicitly selected and justified typographic `stage` remains valid. Do not
search or generate an image merely to fill either treatment.

For one explicitly named film or media work, product, or brand, suitable official
Hero media is the default. Prefer a suitable user-provided asset; otherwise
perform one bounded first-party lookup. Multi-item comparisons default to a
neutral no-image Intro unless official assets can show every subject with equal
prominence, crop quality, and visual weight.

### Source And Asset Rules

- Use, in order of preference, a suitable user-provided asset, then official key
  art, still, product or lifestyle image, or brand imagery from an owner-
  controlled title, studio, distributor, broadcaster, streaming, product, brand,
  newsroom, media-kit, channel, or official static domain.
- A standalone logo does not satisfy this check unless the logo is the subject or
  the user explicitly requests a logo-led Hero. Native title or logo treatment
  inside official artwork may remain, but it never replaces the HTML title.
- Honor explicit license, usage terms, and access controls; attribution does not
  grant reuse rights. For external publication or distribution with unclear
  rights, use an authorized user asset or the no-image fallback. Record the asset
  owner, source page (or `user provided`), and access date in the source list.
- Download the selected file into `assets/` and use a relative path. Do not
  remote-hotlink it or embed a search-result thumbnail.
- Reject assets from aggregators or reposting sites, and reject watermarked,
  blurred, visibly compressed, undersized, or otherwise low-quality files.
- Confirm with deterministic file inspection that the local asset decodes. Add
  responsive sizing, explicit desktop and mobile focal-point rules, and a
  declared text-safe area in source. Actual desktop and mobile crop usefulness
  remains `NOT RUN` by default.

A source entry may use this compact form:

```html
<li>Intro image: Subject Name — Owner; source: <a href="https://official.example/subject">official source page</a>; accessed YYYY-MM-DD.</li>
```

### Focal Point And Text-Safe Area

- Inspect the asset dimensions and subject placement before choosing a mode.
  Record an intentional `object-position` or equivalent focal rule for desktop
  and mobile; do not rely on the browser's default center crop.
- Declare the text-safe area from the actual composition: which region may hold
  the title, summary, metadata, and highlights without covering the subject or
  losing legibility. Keep those elements in the normal HTML reading order.
- `integrated` media may cover the entire Intro surface. Protect its text-safe
  area with a functional scrim derived from the active page background, surface,
  text, or brand-soft tokens. A scrim exists to support contrast and may not be
  added as an atmospheric or decorative gradient.
- A media-backed `stage` follows the same focal-point, safe-area, and functional-
  scrim requirements. A typographic `stage` has no image or placeholder.
- Source declarations, opacity, and a scrim do not prove the real pixels meet
  contrast requirements. Rendered crop, subject visibility, text collision,
  first-screen balance, and contrast remain `NOT RUN` without explicitly
  requested rendered QA.
- If the mobile crop cannot keep the subject and text-safe area predictably
  separate, omit the media on mobile only when the selected layout remains
  coherent, or apply the mode-level fallback below.

### Structure And Accessibility

Keep the full-width shell, mode-ready surface, and ordered content layer. This
example shows `integrated`; it is not a fixed visual recipe:

```html
<header class="report-intro report-intro--integrated report-intro--with-media">
  <div class="report-intro__surface">
    <img class="report-intro__media" src="assets/product-intro.webp" alt="" aria-hidden="true">
    <div class="report-intro__content">
      <h1>Report title</h1>
      <p class="report-intro__summary">Opening summary and main conclusion.</p>
    </div>
  </div>
</header>
```

A typographic `stage` may move its conclusion summary to the next Overview. In
that case, use the following semantic placement rather than leaving the report
without an opening conclusion:

```html
<header class="report-intro report-intro--stage">
  <div class="report-intro__surface">
    <div class="report-intro__content">
      <h1>Report title</h1>
      <p class="report-intro__meta">Source-backed metadata.</p>
    </div>
  </div>
</header>
<div class="page__content">
  <main>
    <section id="report-overview">
      <h2>Overview</h2>
      <p class="report-overview__summary">Opening summary and main conclusion.</p>
      <!-- Evidence follows the summary. -->
    </section>
  </main>
</div>
```

- Keep the title, required summary, metadata, and key points as real HTML. Never
  bake essential copy into the image.
- The scaffold's default decorative pseudo-elements apply only to the image-free
  default `contained` mode. `.report-intro--with-media`,
  `.report-intro--plain`, `.report-intro--integrated`, and
  `.report-intro--stage` suppress them; do not layer those shapes over media.
- Use `alt=""` and `aria-hidden="true"` for decorative Intro media. If an image
  is evidence or conveys necessary product detail, move it into the report body
  as a `<figure>` with meaningful alt text, a caption, and its source.
- Do not use media DOM order, absolute positioning, or responsive cropping to
  change the title-first reading order.

### Fallback

If the user requests no image, access is prohibited, or one bounded first-party
lookup cannot produce an asset that can be downloaded, decoded, cited, cropped,
and displayed without harming readability, remove the media element and
`.report-intro--with-media`.

- For `integrated`, also remove `.report-intro--integrated` and deliver the
  standard no-image `contained` Intro with its summary inside the Intro.
- For `stage`, retain `.report-intro--stage` only when the typographic cover is
  still justified and its summary is either inside the Intro or first in the
  immediate `main > section#report-overview` after its heading; otherwise fall
  back to `contained`.
- For optional `contained` media, remain `contained` and remove only the media
  state and element.

If media is rejected, removed, replaced, or falls back, re-resolve the final
palette from the replacement Hero or the no-Hero content cue before delivery.

Do not add an empty frame, placeholder, low-quality substitute, or repeated
search/generation loop. Do not call ImageGen automatically as a fallback. Record
the delivery result outside the report body as
`Intro media: USED — <owner/source>` or
`Intro media: FALLBACK — <short reason>`.

***

## 7. GenerateImage (AI Image Generation)

Use AI image generation only when the user explicitly requests an AI-generated
image or illustration. It is not a default step for an Opening Intro and must not
be used to imitate official product imagery or imply brand endorsement. Save
each accepted result under the report's `assets/` directory.

### Usage

1. **Write a detailed prompt** describing the scene, style, color palette, and mood.
2. **Choose an aspect ratio** appropriate to the actual placement.
3. **Generate and review each required image independently**, saving it with a
   descriptive filename.
4. **Embed via a relative path**:

```html
<figure class="diagram">
  <img src="assets/conceptual-overview.png" alt="Conceptual illustration of the system overview">
  <figcaption>Figure 3: System Overview</figcaption>
</figure>
```

### Prompt And Review Rules

- Be explicit about style, palette, composition, and mood.
- Keep all titles, labels, logos, and report copy out of the generated bitmap;
  render required text separately as HTML.
- Compose for the image's own subject and crop, not for text overlay.
- Reject generated watermarks, accidental text, malformed logos, or visible
  artifacts before embedding the result.
- If an explicitly requested generated image fails review, report the issue or
  revise it within the user's request; do not silently use it as a required
  Intro asset.

***

## 8. Web Search Image Lookup

Search is conditional, not part of a generic no-image Intro. When the official-
Hero trigger applies, make one bounded lookup on the subject's or rightsholder's
official pages, channels, and static domains. For evidence images in the report
body, use an authoritative source appropriate to the claim and cite it next to
the figure or in the source list.

### Usage

1. Identify the asset owner and authoritative source page before downloading.
2. Download the original usable asset into `assets/`; do not save a search
   thumbnail, aggregator preview, or watermarked/low-resolution copy.
3. Record owner, source page, and access date.
4. Embed the local file via a relative path. Statically check the path, local file
   existence, dimensions, alt behavior, and absence of remote dependencies; keep
   desktop/mobile crop, readability, and runtime offline loading as `NOT RUN`.
5. Do not narrate the lookup in the report body; cite only the accepted asset.

If the required source or quality cannot be verified, omit the optional image.

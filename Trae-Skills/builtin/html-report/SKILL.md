---
name: html-report
description: Create any self-contained HTML deliverable except slides — research reports, whitepapers, PRDs, dashboards, portfolios, resumes, email templates, data visualizations, and more. Use when the user wants to produce a polished, visually designed HTML page or multi-page site for any purpose. Route special sub-scenarios such as prototype-centered interactive PRDs to references/ for extra structure and style requirements. The final deliverable is a self-contained directory (<name>.html + assets + _shared) deployed to the user's workspace with zero external dependencies.
---

# HTML Report

Create a self-contained report directory with zero runtime CDN dependencies. Preserve content quality and visual consistency while avoiding unused components, repeated style specifications, and unnecessary generated code.

## Core Contract

- Match the user's language, audience, report type, tone, and evidence needs.
- Open with a concise summary and make the main conclusion visible before detailed evidence.
- Use clear headings and a deliberate narrative sequence: context, evidence, interpretation, conclusion, and action when applicable.
- Choose one active report palette from `references/color-system.md`. Explicit user or brand direction wins; otherwise use an accepted Hero as the visual cue, then prompt and content cues when no Hero is used.
- Keep page/report colors and chart/data colors in separate token layers derived from that same palette.
- Use neutral reading surfaces, restrained cards, readable typography, and intentional whitespace.
- Keep normal content to at most two font families: one Sans and one Mono. Include CJK system fallbacks for Chinese.
- Give every chart, diagram, table, and meaningful evidence image a title or caption. Decorative Intro media is exempt and must carry no essential information.
- Keep core tables readable on mobile without relying on a narrow embedded horizontal scrollbar. Restructure important wide tables when necessary.
- Keep evidence, inline citations, source links, and local offline assets complete.
- Run final QA through static source, syntax, asset, and contract checks.
- Do not open, navigate, inspect, or control the user's browser for report QA.
- Rendered browser validation is outside the default workflow and requires an explicit request for the current report.
- Every report-like deliverable MUST include one clear opening Intro. Determine the official-Hero trigger in Step 1, resolve eligible media in Step 4, then lock the palette and Intro mode; generic reports still use the no-image path.

The full color token block lives only in `references/color-system.md`. Do not restate the full token set in this file, other references, or the scaffold. Inject the selected active palette once by replacing the scaffold's top-level `/* ACTIVE_PALETTE_TOKENS */` marker with one complete `:root` block.

## Progressive Reference Routing

Read references only after the report plan shows that they are needed. Do not preload the complete reference directory.

| Reference | Read when |
|---|---|
| `references/color-system.md` | Every report, when selecting and injecting the single active palette |
| `references/default-theme.md` | Every report-like deliverable before styling; explicit user style may override its default values, not the Core Contract or final gates |
| `references/chart-contract.md` | Only when the report contains quantitative charts |
| `references/diagram-contract.md` | Only when the report contains structural diagrams |
| `references/layout-contract.md` | The Intro uses `integrated`, `stage`, or media, or the report uses a dashboard, sidebar, complex grid, wide table, or unusual page rhythm |
| `references/element-usage.md` | The report contains any card, metric, callout, quote, recommendation, feature list, tag, or mixed component type |
| `references/visual-badcase-gates.md` | At final static review, to apply source-checkable visual gates and label rendered-only checks as not verified |
| `references/qa-checklist.md` | At final QA, after the report is otherwise complete; use its static path by default |
| `references/interactive-prd.md` | Only for prototype-centered interactive PRDs |
| `diagrams/image-guide.md` | When the official-Hero trigger applies, or when any other image is planned; never for a generic no-image Intro |
| `diagrams/mermaid/*.md` | Only for the selected Mermaid diagram type and only when syntax guidance is needed |
| `diagrams/svg/*.md` | Only when the user explicitly requests a custom inline SVG or a tiny SVG data mark is the cheapest correct representation |

## Workflow

### 1. Plan

Before writing HTML, decide:

- report type, topic, audience, language, and desired decision;
- evidence and source requirements;
- opening summary, main conclusion, section order, and final action;
- whether the official-Hero trigger applies; when it does, defer the final palette until Step 4 resolves to an accepted Hero or valid no-image fallback;
- whether the report needs charts, structural diagrams, optional images, complex layouts, or interactive behavior;
- the opening Intro's title, summary, main conclusion, and whether it centers on one explicitly named film or media work, product, or brand; lock its mode after Step 4 when media is eligible.

If a plan is written, record its two visual choices as exactly these compact lines:

`Color preset: <canonical preset name> — cue: <resolved visual cue>`

`Intro mode: <contained|integrated|stage> — cue: <content/material cue>`

Use an exact catalog name from `references/color-system.md`; use `Custom:<stable-id>` for a custom palette. Choose the Intro mode by content purpose and usable material, not decorative variety. Keep both cues short. Do not copy CSS, token values, the default Design Style rules, or their implementation details into the plan. Read the applicable references and apply them directly to the final HTML.

For a media-backed Intro, unless explicit user/brand direction overrides it, fill the existing `Color preset` line after Step 4 and name the accepted Hero's overall visual direction in its cue. Do not add a separate palette-analysis block.

Apply this information-format gate before adding optional visuals:

- Do not use a universal text-to-chart ratio; match visual density to the report type and reading task.
- Start with zero optional evidence visuals. Add each one only when it answers a distinct question more clearly than a simpler format.
- For each claim, use the least complex format that preserves the meaning: prose for explanation or causality, an inline metric for one number, a compact table for exact values, and a chart for a pattern that must be seen.
- Keep PRDs, research reports, and whitepapers prose/table-led. Data-insight reports and dashboards may be chart-led when each chart supports a distinct analytical question.
- Treat the opening Intro and any purely decorative Intro media as cover context, not evidence and not part of analytical visual density. Evidence-bearing images still count as analytical visuals.

For reports with five or more chapters or several visuals, write a short `plan.md`; otherwise keep the plan concise in reasoning. Do not emit a large design specification as part of the plan.

### 2. Write Content

- Write concise but sufficient explanatory prose; do not replace analysis with visual blocks.
- Make every paragraph advance the argument.
- Use one emphasis method consistently: `<strong>` for formal reports or `<mark class="key">` for visual reports.
- Keep fact, inference, recommendation, and uncertainty distinguishable.
- For data comparisons, keep year, definition, population, and source scope comparable.

### 3. Scaffold the Deliverable

Run the matching scaffold in the user's output directory:

```bash
bash <skill-dir>/scripts/new-report.sh <report-name> <output-dir>
```

```powershell
pwsh -File <skill-dir>/scripts/new-report.ps1 <report-name> <output-dir>
```

The scaffold creates:

```text
<report-name>/
├── <report-name>.html
├── assets/
└── _shared/
    ├── js/
    └── fonts/
```

Preserve the existing script interfaces. Every HTML file must start with:

```html
<!-- Generated by Trae Work -->
```

### 4. Resolve Opening Intro Media — Conditional

Generic, multi-subject, explicitly image-free, or reports outside the named-subject trigger use a no-image Intro. Do not read `diagrams/image-guide.md`, search for images, call an image-generation tool, or emit an image placeholder for this path; it is a valid no-image fallback.

For a report centered on one explicitly named film or media work, product, or brand, prefer a suitable user-provided asset; otherwise perform one bounded first-party lookup. The lookup is required, while use of the image remains conditional on source quality, local download, crop, and readable contrast. Read `diagrams/image-guide.md`, save accepted media under `assets/`, and record its source. If the user requests no image or the lookup fails, use the no-image fallback. Do not call AI image generation unless the user explicitly requests it.

Before final palette selection, reduce an accepted Hero to one compact visual cue from its intended crop: overall temperature, dominant color family, and light/dark value. Do not add automated pixel extraction or a separate analysis artifact. If the Hero is removed, rejected, or replaced, invalidate any Hero-led palette and re-resolve it before delivery.

### 5. Inject One Palette

Read `references/color-system.md`, select one active palette, and replace the scaffold's exact top-level `/* ACTIVE_PALETTE_TOKENS */` marker with one complete concrete `:root` token block.

- Keep backward-compatible variables such as `--bg`, `--bg2`, `--ink`, `--muted`, `--rule`, `--accent`, `--accent2`, `--success`, `--warning`, and `--danger`.
- Keep JavaScript-read values concrete; do not define chart colors as aliases to other CSS variables.
- Do not add local hardcoded component colors outside the selected token block.
- When charts are present, all charts must reuse the same chart palette.

### 6. Build the Opening Intro

Report-like deliverables such as reports, whitepapers, PRDs, proposals, research, and analysis pages MUST open with one clear Intro. Email templates, resumes, standalone visualizations, and dense operational dashboards may follow their native opening pattern instead.

Opening Intro requirements:

- include the page's single `h1`;
- for `contained` and `integrated`, include a one- or two-sentence Intro summary that states the main conclusion before detailed evidence;
- for `stage`, include that summary in the Intro or as `.report-overview__summary` in the first `main > section#report-overview` immediately after it;
- use the active palette's `--page-brand-soft`, falling back to `--page-surface-muted` when the softer surface does not provide sufficient contrast;
- keep the title, summary, and any supporting information as real HTML;
- include subtitle, date, version, author, or up to three highlights only when the report has real content for them;
- use content-driven `block-size`; only a selected `stage` may add the bounded `min-block-size` from `references/layout-contract.md`, and long titles or mobile layouts must still grow naturally;
- remain report-like: borrow the hierarchy of a landing-page opening without marketing slogans or strong calls to action. Intentional stage space must follow the mode-selection rules rather than act as generic decoration.

Use one layout mode and keep it separate from media state:

- `contained` is the backward-compatible default and uses no layout modifier class. Prefer it for formal research, PRDs, data or technical reports, long titles, dense metadata, and any case without a strong opening cue.
- `integrated` uses `.report-intro--integrated` and is eligible only when a narrative or single-subject report has accepted media, an explicit text-safe region, and a composition that benefits from a full-width background. If that media is missing or unsafe, fall back to `contained`.
- `stage` uses `.report-intro--stage` for an editorial, portfolio, film/media, brand feature, or explicitly requested landing-cover opening. It may remain as a typographic stage without media, but its conclusion must appear in the Intro or the immediate Overview.
- An explicit user mode or supplied visual direction overrides automatic selection when it preserves the shared semantic and accessibility rules. Otherwise select by the criteria above; do not randomize modes or let Style alone change the content decision.
- `.report-intro--with-media` means media is present and `.report-intro--plain` removes optional decoration. These state modifiers are independent of layout; never combine `integrated` and `stage`.

Read `references/layout-contract.md` for non-default modes or any Intro media. It owns mode geometry, the mode-ready `.report-intro__surface`, responsive and print fallbacks, and the boundary between Core decisions and Style values.

The scaffold may add at most two low-emphasis CSS-only geometric accents to the default `contained` mode using page tokens. They carry no information, do not count as images, and do not trigger image routing. `.report-intro--plain`, `.report-intro--with-media`, `.report-intro--integrated`, and `.report-intro--stage` suppress them. Omitting these accents is never a delivery failure.

### 7. Build Semantic HTML

- Use semantic `header`, `main`, `section`, `figure`, `table`, and `footer` structure.
- Use the opening Intro as the page `header` for report-like deliverables.
- Keep the Intro outer shell separate from the centered reading content so selected `integrated` and `stage` modes can span the page without `100vw` or negative-margin overflow tricks.
- Keep the normal reading width between 880px and 1080px unless the report type requires a wider data surface.
- Do not apply a second width cap inside that reading container: ordinary prose, including text in full-width cards and callouts, uses its available width. Narrower measures are only for Intro summaries, explicit split/media columns, and margin notes.
- Use neutral surfaces and whitespace before adding cards.
- Cards must contain a conclusion, metric, evidence, risk, recommendation, or action; do not nest cards inside cards.
- Copy only the selected font files into `_shared/fonts/`.
- Use relative paths only. Do not use absolute local paths, remote CDN URLs, or base64 blobs for normal assets.

### 8. Citations

For sourced claims, use sequential superscript links:

```html
<sup><a href="#cite-1">[1]</a></sup>
```

Add a matching ordered source list in the footer. Each source entry must have `id="cite-N"`, a concise source description, and a clickable URL with `target="_blank"` and `rel="noopener"`. Use a plain source label for user-provided documents without a URL. Do not expose raw model citation markers.

### 9. Quantitative Charts — Conditional

If no quantitative chart is planned, do not read `references/chart-contract.md`, copy ECharts, or create `assets/charts.js`.

When charts are planned:

1. Read `references/chart-contract.md`.
2. Copy `assets/js/echarts.min.js` to the report's `_shared/js/` directory.
3. Put chart initialization in `assets/charts.js`, not inline in the HTML.
4. Use `renderer: 'svg'`, `animation: false`, a tooltip with `appendToBody: true`, and resize listeners.
5. Show a visible empty state for missing data and preserve data integrity.
6. Reuse the report's one active chart palette across every chart.
7. Place a concise interpretation near each chart, not only a caption.

### 10. Structural Diagrams — Conditional

If no structural diagram is planned, do not read diagram references or copy diagram libraries.

When a diagram is planned, read `references/diagram-contract.md` and use the cheapest correct representation:

- use Mermaid for ordinary flows, sequences, states, relationships, timelines, and other compact structural diagrams;
- use Graphviz for dense graphs or relationships that benefit from automatic layout;
- use HTML/CSS for very small linear processes that are naturally expressed as content blocks;
- use hand-written inline SVG only when the user explicitly requests custom vector art or the diagram cannot be expressed adequately by the compact tools.

Do not make hand-written SVG the default for all simple diagrams. Do not use AI-generated bitmap art as the primary architecture or process diagram.

### 11. Images — Conditional

The generic no-image Intro does not trigger the illustration workflow. Read `diagrams/image-guide.md` when the official-Hero trigger applies or when any other image is actually planned.

Lightbox behavior is optional. An `<img>` is required but is not enough by itself: add the shared Lightbox from `diagrams/image-guide.md` only when a large diagram, screenshot, map, or detailed image is unreadable at normal report width. Do not add it for ordinary or decorative images.

### 12. Mobile and Print

- Collapse multi-column layouts to one column at narrow widths.
- Preserve reading order and keep critical evidence before appendices.
- Keep important tables readable by wrapping, splitting, simplifying, or converting them to label/value cards. Allow horizontal scrolling only for full-width raw-data appendices explicitly labeled as such.
- Prevent long URLs, IDs, and labels from overflowing.
- Use at least 14px for main body/table content and 12px for captions or footnotes.
- Add print rules when the report is expected to be printed or exported to PDF.

### 13. Final QA and Delivery

After content, the opening Intro when required, assets, charts, diagrams, and responsive styles are complete:

1. Read `references/visual-badcase-gates.md` and `references/qa-checklist.md`.
2. Run the default static QA: inspect HTML/CSS/JavaScript, local asset existence, relative paths, required structure, citations, and the source-checkable gates for every used feature.
3. Do not start local HTTP, capture screenshots, inspect browser state, or invoke browser-control tools or plugins as part of the default workflow.
4. Fix blocking static failures and rerun only the affected checks.
5. Deliver the complete report directory, not the HTML file alone, with a concise QA boundary.

When the official-Hero trigger applies, add exactly one compact delivery line outside the report: `Intro media: USED — <owner/source>` or `Intro media: FALLBACK — <short reason>`.

A request to create, update, restyle, or deliver a report does not authorize browser validation. Only when the user explicitly requests rendered browser testing for the current report may that separate optional check run, and it must use an isolated test browser rather than the user's existing browser, tabs, or session.

Do not claim rendered visual, viewport, console, network-resource, or interaction QA passed when only static QA ran. Do not block default delivery merely because browser tooling is unavailable. Do not deliver if the required opening Intro, referenced local resources, citations, or another source-checkable priority-zero gate fails. Missing or invalid optional Intro media must be fixed or removed; the no-image Intro remains a valid fallback.

## Compatibility

- Preserve the report folder interface: `<name>.html + assets + _shared`.
- Preserve existing `.report-intro--with-media` and `.report-intro--plain` state meanings; absence of a new layout modifier remains `contained`.
- Preserve existing legacy CSS variable names used by downstream chart code.
- Keep ECharts and Mermaid local and copy them only when used.
- Do not rewrite existing user reports merely to adopt this Skill unless the user requests a restyle or migration.

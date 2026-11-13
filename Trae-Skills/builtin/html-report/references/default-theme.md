# Default Design Style Contract

Contract ID: `report-default-v1`

Read this reference before styling every report-like deliverable. It is the
neutral reading baseline for TraeWork HTML Preview and html-report outputs. An
explicit user style may override its default visual values, but never the Core
Contract, content semantics, accessibility, or final quality gates.

Do not reproduce this contract in `plan.md`. The plan records only the compact
`Color preset:` line defined in `references/color-system.md` and the compact
`Intro mode:` line defined by the Core Contract; apply the detailed rules
directly to the final HTML.

## Reference Rules

### DS-01 — Scope And Personality

Design for one-time reading, presentation, review, and result display rather
than a back-office workspace or marketing landing page. The default should feel
light, clear, orderly, and quietly professional. Make the topic and conclusion
clear first, then present evidence and actions.

### DS-02 — Opening Intro

Use one of the three Intro modes defined in `references/layout-contract.md`:
`contained`, `integrated`, or `stage`. No layout modifier means `contained`;
`.report-intro--integrated` and `.report-intro--stage` are mutually exclusive.
The media modifier `.report-intro--with-media` and minimal-treatment modifier
`.report-intro--plain` are orthogonal to layout mode.

All modes keep the page's single `h1`, metadata, and essential copy as real HTML.
`contained` and `integrated` keep a one- or two-sentence conclusion summary in
the Intro. A `stage` may keep that summary in the Intro or place it before
evidence in the immediately following `main > section#report-overview`, using
`.report-overview__summary`. Formal research, PRD, data, and technical reports
default to `contained`. Use `integrated` only with qualified media, an explicit
text-safe area, and a functional page-token scrim. Use `stage` for a justified
cover-like opening; it may remain typographic without media.

Apply the bounded official-Hero lookup in the Core Contract when its named-
subject trigger applies. Media never carries essential information. If
`integrated` media is unavailable or unsuitable, fall back to `contained`; a
`stage` may instead remove the media and retain its typographic composition. A
default image-free `contained` Intro may use up to two optional low-emphasis
flat CSS shapes that convey no information and are suppressed by media, plain,
integrated, and stage treatments.

### DS-03 — Layout

Default to one centered reading column between 880px and 1080px. Use a sidebar,
dashboard grid, wide table band, or another rhythm only when the content needs
it; then read `references/layout-contract.md`. Preserve reading order and
collapse multi-column content on mobile. Treat `header.report-intro` as a
full-width mode shell and `.report-intro__content` as its centered, ordered text
layer; the selected mode determines whether `.report-intro__surface` is bounded
or spans the opening width.

### DS-04 — Palette And Backgrounds

Obtain all colors from `references/color-system.md`. Keep the page on neutral
reading surfaces. A `contained` Intro may use one soft page-token floor;
`integrated` and `stage` may use a qualified opening surface as specified in the
color contract. Page tokens style content surfaces, permitted Intro geometry,
and any functional media scrim; chart tokens style data marks. Do not turn chart,
semantic, or saturated brand colors into card or section fills.

### DS-05 — Typography

Use `14px / 20px` as the ordinary body, list, form, card, and table baseline.
Reserve smaller sizes for labels, notes, legends, metadata, and captions. Use no
more than two normal font families: one Sans and one Mono, with CJK system
fallbacks for Chinese. Opening-title scale type does not belong in ordinary
cards.

### DS-06 — Radius

Use restrained radii: 8px for controls, tags, and lightweight containers; 12px
for cards and report modules; 999px only for avatars, pills, and progress dots.
Avoid oversized consumer-card rounding.

### DS-07 — Spacing Rhythm

Use 4–8px for tight groups, 12–16px inside information groups, 20px for normal
card padding, 24–32px between modules, and about 48px between major sections.
Create hierarchy with consistent pauses. Do not create an unexplained empty
opening; a selected `stage` uses the bounded, content-safe geometry and fallback
rules in `references/layout-contract.md`.

### DS-08 — Separation And Surfaces

Use whitespace first, neutral rules second, and shadows only for true floating
layers such as tooltips. Content containers use neutral borders when needed. Do
not use an accent top, left, or full border, a border gradient, or a colored
decorative strip on cards, callouts, quotes, chart panels, or recommendation
blocks. This does not prohibit button, input, selection, or focus states.

### DS-09 — Tables

Use a neutral header surface, fine row rules, aligned values, wrapping cells,
and a visible title or caption. Emphasize the first column only when it is truly
a row label; encode that meaning with `<th scope="row">` instead of styling every
first cell by position. Restructure important wide tables for mobile rather than
hiding core content behind a narrow scrollbar.

### DS-10 — Quotes, Feature Lists, And Recommendations

Use quotes only as sourced evidence, on a neutral surface with optional italic
text and no decorative accent strip. Present feature lists as border-bottom rows
or a compact grid rather than a stack of heavy cards. A recommendation must
include its reason, impact, and next step; use two responsive columns only when
the items are genuinely comparable, and collapse them on mobile. Read
`references/element-usage.md` whenever any of these elements appears.

### DS-11 — Links And Emphasis

Use `--accent` / `--page-brand` for links and restrained key emphasis. A visual
report may use `mark.key { background: none; color: var(--accent); font-weight: 600; }`;
a formal report should use `<strong>` instead. Choose one method and do not
scatter colored copy through the page.

### DS-12 — Data, Status, And Icons

Align numeric values clearly and give every chart a nearby one-sentence
takeaway. Read `references/chart-contract.md` only when charts are present. Use
semantic colors only for real status or direction. Icons default to 14–16px,
clarify type/state/action, and do not introduce unrelated colors or replace
essential text.

## Implementation Boundary

Express spacing, radius, and font roles through structural CSS variables. Inject
the one complete concrete color block from `references/color-system.md` at the
scaffold's `ACTIVE_PALETTE_TOKENS` marker. Preserve legacy aliases used by
downstream report and chart code, and keep values read by JavaScript concrete
rather than `var(...)` aliases.

The Core Contract owns Intro semantics, mode selection, accessibility, source
requirements, and fallback behavior. A selected Style may vary typography,
alignment, texture, media focal crop, and scrim strength within that mode, but
must not remove those invariants or silently change the selected mode. Style must
not select, override, or remap the resolved palette. If a Style crop materially
changes the resolved cue, re-resolve the palette before delivery.

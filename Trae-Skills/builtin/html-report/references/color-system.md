# Color System Contract

Use this contract for all HTML report color decisions before writing CSS. HTML
reports do not use one fixed hue as the default visual effect. Every report
chooses one active palette after any Intro Hero is accepted or rejected, then
keeps page and chart colors matched inside that palette.

## Decision Order

1. Capture explicit user or brand direction before choosing colors.
2. When there is an accepted Hero, use its overall visual direction next.
3. When no Hero is used, use prompt and content cues from the report.
4. Select one catalog palette or define a custom palette. No named palette is a
   universal fallback.
5. Keep page/report and chart/data colors separate while deriving both from that
   palette.
6. Prefer curated colors and reserve semantic colors for real meaning.

If an accepted Hero is rejected, removed, replaced, or falls back, re-resolve the
final palette from the replacement Hero or the no-Hero content cue.

## Visual Cue Selection

An accepted Hero is a visual cue, not a source for automated pixel extraction.
Use its overall temperature, dominant color family, and light/dark value; ignore
skin tones, logos, and incidental highlights. The table below supplies
prompt/content fallbacks when no stronger visual cue exists.

| Prompt Cue | Recommended Palette | Reason |
|---|---|---|
| Explicit TraeWork, purple brand direction, existing purple brand asset | TraeWork Purple | Preserves brand alignment only when requested |
| Cute, romantic, celebratory, lifestyle, soft consumer, emotional or playful topic | Rose Pink | Soft red-pink tone fits cute, romantic, and expressive scenes |
| Retrospective, narrative summary, customer story, culture, workshop, human-centered topic | Warm Editorial | Warm orange-gray tone for reflective or people-centered content |
| Strategy, executive summary, business analysis, market sizing, finance, governance | Business Blue | More formal and institutional |
| Product review, UX analysis, feature comparison, adoption, workflow, product metrics | Product Teal | Product-focused and modern without feeling branded |
| No strong brand, weak style signal, general mixed-content report | Custom content-derived palette after the outline is known | Derive color from the content, audience, and evidence type instead of falling back to a named preset |

If multiple cues conflict, prefer the user's explicit brand/style request over
the inferred report type. If there is still ambiguity, use the internal scaffold
tokens only while drafting, keep accent usage sparse, and revisit the palette
after the content outline is known. Do not choose Rose Pink just because the
prompt is generic, and do not record scaffold tokens as the selected palette.
When an accepted Hero has no compatible catalog preset, use `Custom:<stable-id>`;
do not fall back to the content table.

## Compact Plan Record

When a plan is written, record the color decision as one compact line:

`Color preset: <canonical preset name> — cue: <resolved visual cue>`

Use an exact catalog name. For a custom palette, use `Custom:<stable-id>` so the
decision remains identifiable across steps. Without explicit user/brand
direction, an accepted Hero cue names temperature, dominant family, and
light/dark value; without a Hero, use the prompt/content cue. Do not copy CSS,
token values, chart arrays, remap instructions, or the Design Style checklist
into the plan. The final HTML remains the authority for the resolved concrete
token values.

## Token Layers

| Layer | Role | Use For | Do Not Use For |
|---|---|---|---|
| Neutral scale | Reading shell | Page background, text, borders, tables, quiet cards | Data series |
| Accent scale | Report emphasis | Links, key numbers, small markers, primary actions, quiet Intro surfaces, functional Intro scrims | Saturated or repeated large decorative surfaces |
| Semantic colors | Meaning | Status tags, risk notes, success/error direction | Ordinary categories |
| Chart colors | Data marks | Bars, lines, points, slices, heat cells, legend dots | Page cards, quotes, section backgrounds |

## Curated Palette Rule

Preset colors must come from the curated palette set, then be mapped into this
report token model. Do not invent yellow-brown, olive, muddy teal, or gray-heavy
business palettes by hand. Use only the colors needed for the current token
roles. Do not paste a full rainbow palette into one report.

## Canonical Token Block

This is the only full color token block in the Skill. Copy it exactly once into
the scaffold's `ACTIVE_PALETTE_TOKENS` marker, then remap both page/report and
chart/data layers to the resolved visual cue. Keep reading surfaces neutral, but
align their warm/cool temperature and light/dark value hierarchy instead of
leaving the warm baseline unchanged. Do not duplicate the full block in
`SKILL.md`, another reference, or a scaffold script. Keep all values concrete
because chart code and rendered diagram helpers may read them at runtime.

The values below are a warm-neutral drafting baseline, not a final preset name.
Never inject or deliver it unchanged. Before delivery, record the selected
palette and replace both token layers from explicit user/brand direction, an
accepted Hero, or the no-Hero prompt/content fallback.

```css
:root {
  /* Page / report tokens */
  --page-bg: #FFFFFF;
  --page-surface: #F8F6F3;
  --page-surface-muted: #F1EDE8;
  --page-text: #24201D;
  --page-text-secondary: #463F3A;
  --page-text-muted: #6F6660;
  --page-text-disabled: #9A8F87;
  --page-border: #DDD6CF;
  --page-brand: #6B5E57;
  --page-brand-hover: #574B45;
  --page-brand-active: #3F3631;
  --page-brand-soft: #F5F2EF;
  --page-brand-soft-strong: #EAE2DB;
  --page-brand-text: #3F3631;

  /* Backward-compatible report variables */
  --bg: #FFFFFF;
  --bg2: #F8F6F3;
  --rule: #DDD6CF;
  --ink: #24201D;
  --muted: #6F6660;
  --text-secondary: #463F3A;
  --text-disabled: #9A8F87;
  --accent: #6B5E57;
  --accent-hover: #574B45;
  --accent-active: #3F3631;
  --accent-soft: #F5F2EF;
  --accent2: #8A7668;

  /* Chart / data tokens */
  --chart-series-1: #6B5E57;
  --chart-series-2: #8A7668;
  --chart-series-3: #A1826D;
  --chart-series-4: #6F7772;
  --chart-other: #DDD6CF;
  --chart-accent: #8A7668;
  --chart-accent-2: #A1826D;
  --chart-positive: #52C41A;
  --chart-warning: #FAAD14;
  --chart-negative: #FF4D4F;
  --chart-grid: rgba(36, 32, 29, 0.12);
  --chart-axis: #6F6660;
  --chart-label: #6F6660;
  --chart-tooltip-bg: #FFFFFF;

  /* Semantic compatibility tokens */
  --success: #52C41A;
  --info: #6B5E57;
  --reminder: #FF7A45;
  --warning: #FAAD14;
  --danger: #FF4D4F;
  --positive: #52C41A;
  --negative: #FF4D4F;
}
```

## Preset Catalog

Each preset must define both page/report tokens and chart/data tokens. Do not
change one layer without checking the other, and do not mix chart palettes from
different presets inside one report.

| Preset | Best For | Page Accent | Chart Series |
|---|---|---|---|
| TraeWork Purple | Explicit TraeWork brand scenes only | `#4B3FE3` | `#4B3FE3`, `#22A5F7`, `#A463F2`, `#6CC5B0` |
| Warm Editorial | Retrospectives, narratives, human-centered reports | `#B8551D` | `#B8551D`, `#F59E42`, `#D97757`, `#8E6E63` |
| Business Blue | Strategy, business analysis, executive summaries | `#0969DA` | `#0969DA`, `#8250DF`, `#06B6D4`, `#BF3989` |
| Product Teal | Product insight, UX review, feature analysis | `#12B886` | `#12B886`, `#228BE6`, `#7950F2`, `#E64980` |
| Rose Pink | Cute, romantic, lifestyle, soft consumer, celebratory, or playful reports | `#D61F69` | `#D61F69`, `#E11D48`, `#C026D3`, `#F97316` |

## Preset Rules

- TraeWork Purple requires an explicit brand reason.
- Warm Editorial uses a clear warm orange-gray family: terracotta, soft orange,
  clay, and warm gray. Do not mix it with bright pink, purple, or green
  peer-series colors.
- Rose Pink requires cute, romantic, lifestyle, soft consumer, celebratory, or
  playful cues. It is not the fallback for general PRDs, research, analysis,
  proposals, or internal reports.
- A preset changes token values, not the report component model.
- Every preset value must come from the curated palette set or an explicit
  brand color.
- One report uses one active preset for all charts. Do not let one chart use
  Rose Pink colors while another chart uses Product Teal, Warm Editorial,
  or TraeWork Purple colors.
- Page accents should stay sparse: links, anchors, section markers, key numbers,
  small primary actions, and the single opening Intro surface.
- Chart colors should stay on data marks. If a chart has more than four peer
  series, use Top N + Other, small multiples, or a table.
- Do not invent ad-hoc colors inside one component. If a new color role is
  needed, add it to the token layer first.

## Semantic Color Rules

Semantic colors explain meaning; they do not decorate the page.

| Role | Default | Use For |
|---|---:|---|
| Info | `#6B5E57` | Neutral informational notes |
| Success | `#52C41A` | Completed, healthy, positive states |
| Reminder | `#FF7A45` | Attention, follow-up, time-sensitive notes |
| Warning | `#FAAD14` | Risk, degradation, caution |
| Danger | `#FF4D4F` | Failure, blocker, negative state |

Use semantic colors for tags, icons, thin borders, small soft backgrounds, and
chart direction only when the encoded value is actually semantic.

## Opening Intro Surface

- A default `contained` Intro may use `--page-brand-soft` as its single shallow
  color floor. If text contrast is insufficient, use `--page-surface-muted`.
- An `integrated` Intro may place qualified media across its full surface. Add a
  functional scrim derived only from the active `--page-*` background, surface,
  text, or brand-soft tokens wherever needed to protect the declared text-safe
  area. The scrim may be solid or graduated, but its shape and strength must
  serve legibility rather than atmospheric decoration.
- A `stage` may use a quiet full-width page-token surface, a typographic
  treatment, or qualified media with the same functional scrim rule. The mode
  does not authorize chart, semantic, or saturated status colors as a large fill.
- These are opening-section exceptions, not permission to repeat large colored
  or media bands through the report. Never use `--chart-*` or semantic status
  colors as Intro surfaces or scrims.
- The default image-free `contained` Intro may draw at most two low-emphasis flat
  CSS shapes. Fill them only with quiet `--page-*` surface or brand-soft tokens;
  do not introduce ad-hoc, chart, or semantic colors for decoration. Suppress
  them for integrated, stage, media-backed, and plain treatments.
- Source-level token use and a declared scrim are not proof of rendered contrast;
  actual crop and contrast remain `NOT RUN` unless optional rendered QA is
  explicitly requested.

## Implementation Rules

- Define colors through `:root` CSS variables.
- Keep legacy aliases such as `--bg`, `--bg2`, `--ink`, `--muted`, `--rule`,
  `--accent`, `--accent2`, `--success`, `--warning`, and `--danger`.
- Values read by JavaScript must be concrete values, not aliases like
  `--chart-series-1: var(--accent)`.
- Follow `references/chart-contract.md` for chart palette consistency, shape,
  tooltip, legend, and edge-case rules.
- Mermaid, Graphviz, and PlantUML examples must use resolved colors from the
  selected preset because rendered images cannot inherit CSS variables.

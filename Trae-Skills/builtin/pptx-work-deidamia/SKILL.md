---
name: pptx
description: "Presentation creation, editing, and analysis. When you need to work with presentations (.pptx files) for: (1) Creating new presentations, (2) Modifying or editing content, (3) Working with layouts, (4) Adding comments or speaker notes, or any other presentation tasks"
license: Proprietary. LICENSE.txt has complete terms
supported_os:
  - macos
  - linux
---

# PPTX Skill

## Quick Reference

| Task | Guide |
|------|-------|
| Read/analyze content | `python3 -m markitdown presentation.pptx` |
| Edit or create from template | Must Read [editing.md](editing.md) |
| Create from scratch | **Step 1:** Generate design system → **Step 2:** Must Read [pptxgenjs.md](pptxgenjs.md) |
| Generate design system | `python3 skills/pptx/scripts/design/search.py "<topic>" --design-system` |

⛔ **NEVER use `python-pptx` to generate presentations directly**

## Reading Content

```bash
# Text extraction
python3 -m markitdown presentation.pptx

# Visual overview
python3 scripts/thumbnail.py presentation.pptx

# Raw XML
python3 scripts/unpack.py presentation.pptx unpacked/
```

---

## Editing Workflow

**Read [editing.md](editing.md) for full details.**

1. Analyze template with `thumbnail.py`
2. Unpack → manipulate slides → edit content → clean → pack

---

## Creating from Scratch

⚠️ **Required workflow — do not skip steps:**

1. **Generate design system first**: `python3 skills/pptx/scripts/design/search.py "<topic>" --design-system`
2. **Then use PptxGenJS**: Read [pptxgenjs.md](pptxgenjs.md) for implementation

Use when no template or reference presentation is available.

---

## Design Ideas

**Don't create boring slides.** Plain bullets on a white background won't impress anyone. Consider ideas from this list for each slide.

### Generate Design System (Recommended)

For professional presentations, generate a comprehensive design system tailored to your topic:

```bash
python3 skills/pptx/scripts/design/search.py "<topic> <industry> <keywords>" --design-system -p "Presentation Name"
```

⚠️ **IMPORTANT: Always use English keywords for search queries.** The design system database contains English keywords only. Using non-English queries will result in poor matches and default/boring designs.

| Instead of | Use |
|------------|-----|
| 科技公司 | tech startup, SaaS |
| 奢侈品牌 | luxury brand, premium |
| 医疗健康 | healthcare, medical |
| 金融科技 | fintech, blockchain |
| 教育培训 | education, e-learning |
| 电商平台 | e-commerce, retail |
| 创意设计 | creative agency, portfolio |
| 企业服务 | B2B service, enterprise |

**Example:**
```bash
python3 skills/pptx/scripts/design/search.py "fintech blockchain startup pitch" --design-system -p "CryptoVenture Pitch"
```

This gives you:
- **Recommended style** (glassmorphism, minimalism, etc.)
- **Color palette** with primary, secondary, accent colors
- **Typography** with font pairings
- **Visual effects** (gradients, shadows, etc.)
- **Anti-patterns** to avoid

For additional design details:
```bash
# Get more color palette options
python3 skills/pptx/scripts/design/search.py "fintech crypto" --domain color

# Get typography alternatives
python3 skills/pptx/scripts/design/search.py "professional modern" --domain typography

# Get chart recommendations for data slides
python3 skills/pptx/scripts/design/search.py "comparison trend" --domain chart
```

### Before Starting

- **Pick a bold, content-informed color palette**: The palette should feel designed for THIS topic. If swapping your colors into a completely different presentation would still "work," you haven't made specific enough choices.
- **Dominance over equality**: One color should dominate (60-70% visual weight), with 1-2 supporting tones and one sharp accent. Never give all colors equal weight.
- **Dark/light contrast**: Dark backgrounds for title + conclusion slides, light for content ("sandwich" structure). Or commit to dark throughout for a premium feel.
- **Commit to a visual motif**: Pick ONE distinctive element and repeat it — rounded image frames, icons in colored circles, thick single-side borders. Carry it across every slide.

### Color Palettes

Get color palette recommendations tailored to your topic:

```bash
python3 skills/pptx/scripts/design/search.py "<topic> <industry>" --domain color
```

### For Each Slide

**Every slide needs a visual element** — image, chart, icon, or shape. Text-only slides are forgettable.

**Layout options:**
- Two-column (text left, illustration on right)
- Icon + text rows (icon in colored circle, bold header, description below)
- 2x2 or 2x3 grid (image on one side, grid of content blocks on other)
- Half-bleed image (full left or right side) with content overlay

**Data display:**
- Large stat callouts (big numbers 60-72pt with small labels below)
- Comparison columns (before/after, pros/cons, side-by-side options)
- Timeline or process flow (numbered steps, arrows)

**Visual polish:**
- Icons in small colored circles next to section headers
- Italic accent text for key stats or taglines

### Typography

**Choose an interesting font pairing** — don't default to Arial. Pick a header font with personality and pair it with a clean body font.

For more typography options: `python3 skills/pptx/scripts/design/search.py "elegant professional" --domain typography`

| Header Font | Body Font |
|-------------|-----------|
| Georgia | Calibri |
| Arial Black | Arial |
| Calibri | Calibri Light |
| Cambria | Calibri |
| Trebuchet MS | Calibri |
| Impact | Arial |
| Palatino | Garamond |
| Consolas | Calibri |

| Element | Size |
|---------|------|
| Slide title | 36-44pt bold |
| Section header | 20-24pt bold |
| Body text | 14-16pt |
| Captions | 10-12pt muted |

### Spacing

- 0.5" minimum margins
- 0.3-0.5" between content blocks
- Leave breathing room—don't fill every inch

### Avoid (Common Mistakes)

- **Don't repeat the same layout** — vary columns, cards, and callouts across slides
- **Don't center body text** — left-align paragraphs and lists; center only titles
- **Don't skimp on size contrast** — titles need 36pt+ to stand out from 14-16pt body
- **Don't default to blue** — pick colors that reflect the specific topic
- **Don't mix spacing randomly** — choose 0.3" or 0.5" gaps and use consistently
- **Don't style one slide and leave the rest plain** — commit fully or keep it simple throughout
- **Don't create text-only slides** — add images, icons, charts, or visual elements; avoid plain title + bullets
- **Don't forget text box padding** — when aligning lines or shapes with text edges, set `margin: 0` on the text box or offset the shape to account for padding
- **Don't use low-contrast elements** — icons AND text need strong contrast against the background; avoid light text on light backgrounds or dark text on dark backgrounds
- **NEVER use horizontal lines to seperate title and body** — use whitespace or background color instead

---

## QA (Required)

**Assume there are problems. Your job is to find them.**

Your first render is almost never correct. Approach QA as a bug hunt, not a confirmation step. If you found zero issues on first inspection, you weren't looking hard enough.

### Content QA

```bash
python3 -m markitdown output.pptx
```

Check for missing content, typos, wrong order.

**When using templates, check for leftover placeholder text:**

```bash
python3 -m markitdown output.pptx | grep -iE "xxxx|lorem|ipsum|this.*(page|slide).*layout"
```

If grep returns results, fix them before declaring success.

### Visual QA

**⚠️ USE SUBAGENTS** — even for 2-3 slides. You've been staring at the code and will see what you expect, not what's there. Subagents have fresh eyes.

Convert slides to images (see [Converting to Images](#converting-to-images)), then use this prompt:

```
Visually inspect these slides. Assume there are issues — find them.

Look for:
- Overlapping elements (text through shapes, lines through words, stacked elements)
- Text overflow or cut off at edges/box boundaries
- Decorative lines positioned for single-line text but title wrapped to two lines
- Source citations or footers colliding with content above
- Elements too close (< 0.3" gaps) or cards/sections nearly touching
- Uneven gaps (large empty area in one place, cramped in another)
- Insufficient margin from slide edges (< 0.5")
- Columns or similar elements not aligned consistently
- Low-contrast text (e.g., light gray text on cream-colored background)
- Low-contrast icons (e.g., dark icons on dark backgrounds without a contrasting circle)
- Text boxes too narrow causing excessive wrapping
- Leftover placeholder content

For each slide, list issues or areas of concern, even if minor.

Read and analyze these images:
1. /path/to/slide-01.jpg (Expected: [brief description])
2. /path/to/slide-02.jpg (Expected: [brief description])

Report ALL issues found, including minor ones.
```

### Verification Loop

1. Generate slides → Convert to images → Inspect
2. **List issues found** (if none found, look again more critically)
3. Fix issues
4. **Re-verify affected slides** — one fix often creates another problem
5. Repeat until a full pass reveals no new issues

**Do not declare success until you've completed at least one fix-and-verify cycle.**

---

## Converting to Images

Convert presentations to individual slide images for visual inspection:

```bash
soffice --headless --convert-to pdf output.pptx
pdftoppm -jpeg -r 150 output.pdf slide
```

This creates `slide-01.jpg`, `slide-02.jpg`, etc.

To re-render specific slides after fixes:

```bash
pdftoppm -jpeg -r 150 -f N -l N output.pdf slide-fixed
```

---

## Dependencies

> All dependencies mentioned below are pre-installed, use them directly. 

- `markitdown[pptx]` - text extraction
- `Pillow` - thumbnail grids
- `pptxgenjs` - creating from scratch
- LibreOffice (`soffice`) - PDF conversion
- Poppler (`pdftoppm`) - PDF to images


# Image & Asset Generation Guide

This guide covers how to prepare visual assets (charts, diagrams, photos) before writing PptxGenJS code. All external images must be generated and verified before proceeding to slide authoring.

***

| Visual Type                              | Available Approaches                                         |
| ---------------------------------------- | ------------------------------------------------------------ |
| Simple bar/line/pie chart                | PptxGenJS native `addChart` · Matplotlib (see Option A)      |
| Process flow / Flowchart                 | Graphviz (see Option D)                                      |
| Icon grid / comparison layout            | Template slide with shapes                                   |
| Complex statistical chart                | Matplotlib (see Option A)                                    |
| Sequence / State / Gantt / Class diagram | PlantUML (see Option C)                                      |
| Architecture / dependency graph          | Graphviz (see Option D)                                      |
| Network topology                         | Graphviz (see Option D)                                      |
| Illustrations / hero images / backgrounds | GenerateImage (see Option B) · Web Search (see Option E)         |
| Conceptual / abstract visuals            | GenerateImage (see Option B)                                      |

**Decision guide:**
- **Numerical data** to visualize → Matplotlib (Option A)
- **Illustrations, backgrounds, hero images, or conceptual visuals** → GenerateImage (Option B)
- **Sequence interactions**, Gantt charts, or class diagrams → PlantUML (Option C)
- **Node-edge relationships** (flowcharts, architecture, dependency graphs, network topology) → Graphviz (Option D)
- **Stock photos, logos, or brand assets** that must be real → Web Search (Option E)
- **Simple bar/line/pie/doughnut chart** that reviewers may edit later → PptxGenJS native `addChart` (below)

***

## PptxGenJS Native Charts

For simple charts (bar, line, pie, doughnut, area, scatter, radar, bubble), use PptxGenJS `addChart` directly. This keeps the chart editable in PowerPoint — reviewers can change data, colors, and labels without regenerating images. Only fall back to Matplotlib when the chart type or customization exceeds what PptxGenJS supports.

### API

```javascript
slide.addChart(pres.ChartType.<type>, dataArray, options);
```

### Available Chart Types

All types are accessed via `pres.ChartType`:

| Constant | Chart |
|----------|-------|
| `pres.ChartType.area` | Area |
| `pres.ChartType.bar` | Bar (horizontal) |
| `pres.ChartType.bar3d` | Bar 3D |
| `pres.ChartType.bubble` | Bubble |
| `pres.ChartType.bubble3d` | Bubble 3D |
| `pres.ChartType.doughnut` | Doughnut |
| `pres.ChartType.line` | Line |
| `pres.ChartType.pie` | Pie |
| `pres.ChartType.radar` | Radar |
| `pres.ChartType.scatter` | Scatter |

> **⚠️ IMPORTANT**: Always use `pres.ChartType.xxx` (where `pres` is your PptxGenJS instance).



## Image Naming Convention (REQUIRED)

**All generated images MUST include dimensions in the filename:**

```
{name}_{width}x{height}.png
```

Examples:

- `architecture_800x600.png` — 800px wide, 600px tall
- `timeline_1200x400.png` — 1200px wide, 400px tall
- `chart_600x600.png` — 600px square

**When saving images, always include dimensions:**

```python
# Matplotlib example
fig, ax = plt.subplots(figsize=(8, 5), dpi=150)
# ... create chart ...
width_px = int(8 * 150)   # 1200
height_px = int(5 * 150)  # 750
plt.savefig(f'chart_{width_px}x{height_px}.png', dpi=150, transparent=True)
```

```bash
# Generic example — check output dimensions after generation
input="diagram_temp.png"
dims=$(file "$input" | grep -oE '[0-9]+ x [0-9]+' | tr -d ' ')
mv "$input" "diagram_${dims/x/_x_}.png"
```

***

## Option A: Matplotlib / Python Charts

### Color Consistency

All generated charts MUST use the same color palette as the presentation. Define colors at the top of your generation script based on your chosen theme.

```python
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# ============================================================
# COLOR PALETTE — Match your PPT theme
# ============================================================
# Example: "Ocean Gradient" theme
COLORS = {
    'primary': '#065A82',
    'secondary': '#1C7293',
    'accent': '#21295C',
    'background': '#F0F7FA',
    'text': '#21295C',
    'light': '#E8F4F8',
}

# Color cycle for multiple data series
COLOR_CYCLE = [COLORS['primary'], COLORS['secondary'], COLORS['accent'], '#4A90A4', '#2D5A6B']

# Apply theme globally
plt.rcParams.update({
    'axes.prop_cycle': plt.cycler(color=COLOR_CYCLE),
    'axes.facecolor': 'none',
    'axes.edgecolor': COLORS['text'],
    'axes.labelcolor': COLORS['text'],
    'text.color': COLORS['text'],
    'xtick.color': COLORS['text'],
    'ytick.color': COLORS['text'],
    'figure.facecolor': 'none',
    'font.family': 'sans-serif',
    'font.size': 12,
})
# ============================================================

# Create chart with theme colors
fig, ax = plt.subplots(figsize=(8, 5), dpi=150)
bars = ax.bar(['Q1', 'Q2', 'Q3', 'Q4'], [25, 40, 35, 50],
              color=[COLORS['primary'], COLORS['secondary'], COLORS['primary'], COLORS['secondary']],
              edgecolor=COLORS['accent'], linewidth=1.5)
ax.set_title('Quarterly Revenue', fontsize=16, fontweight='bold', color=COLORS['text'])
ax.set_ylabel('Revenue ($M)', color=COLORS['text'])
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

plt.tight_layout()
width_px, height_px = int(8 * 150), int(5 * 150)
plt.savefig(f'chart_{width_px}x{height_px}.png', dpi=150, transparent=True)
plt.close()
```

### Palette Templates

```python
# Midnight Executive
COLORS = {'primary': '#1E2761', 'secondary': '#CADCFC', 'accent': '#FFFFFF', 'text': '#1E2761'}

# Forest & Moss
COLORS = {'primary': '#2C5F2D', 'secondary': '#97BC62', 'accent': '#F5F5F5', 'text': '#2C5F2D'}

# Coral Energy
COLORS = {'primary': '#F96167', 'secondary': '#F9E795', 'accent': '#2F3C7E', 'text': '#2F3C7E'}

# Warm Terracotta
COLORS = {'primary': '#B85042', 'secondary': '#E7E8D1', 'accent': '#A7BEAE', 'text': '#B85042'}

# Teal Trust
COLORS = {'primary': '#028090', 'secondary': '#00A896', 'accent': '#02C39A', 'text': '#028090'}
```

Use Matplotlib for:

- Complex statistical charts
- Custom visualizations not supported by PptxGenJS
- Heatmaps, scatter plots, box plots

### CJK Support

**⚠️ CRITICAL: NEVER call `sns.set_theme()` or `sns.set_style()` directly in your code.** Both reset `matplotlib.rcParams` including font settings, which causes CJK text (Chinese/Japanese/Korean) to render as empty boxes.

When creating charts with Chinese/Japanese/Korean text, configure the font first:

```python
import os
import platform
import matplotlib.pyplot as plt
import matplotlib

def setup_matplotlib_cjk():
    """Configure matplotlib to support CJK characters"""
    system = platform.system()

    if system == "Darwin":  # macOS
        font_names = ['Arial Unicode MS', 'PingFang SC', 'Heiti SC', 'STHeiti']
    elif system == "Windows":
        font_names = ['Microsoft YaHei', 'SimHei', 'SimSun']
    else:  # Linux
        font_names = ['Noto Sans CJK SC', 'WenQuanYi Zen Hei', 'Droid Sans Fallback']

    available_fonts = [f.name for f in matplotlib.font_manager.fontManager.ttflist]
    for font_name in font_names:
        if font_name in available_fonts:
            plt.rcParams['font.sans-serif'] = [font_name] + plt.rcParams['font.sans-serif']
            plt.rcParams['axes.unicode_minus'] = False
            return font_name
    return None

# Setup CJK font before creating charts
cjk_font = setup_matplotlib_cjk()

# Create a bar chart with Chinese labels
categories = ['第一季度', '第二季度', '第三季度', '第四季度']
values = [120, 135, 142, 158]

plt.figure(figsize=(10, 6))
plt.bar(categories, values, color='steelblue')
plt.title('季度销售数据 Quarterly Sales', fontsize=16)
plt.xlabel('季度 Quarter', fontsize=12)
plt.ylabel('销售额 Sales', fontsize=12)
plt.tight_layout()
plt.savefig('chart.png', dpi=150)
plt.close()
```

### Seaborn API Safety Guide

| Status | Function | Notes |
|--------|----------|-------|
| ❌ FORBIDDEN | `sns.set_theme()` | Resets font.sans-serif → CJK broken |
| ❌ FORBIDDEN | `sns.set_style()` | Resets font.sans-serif → CJK broken |
| ❌ FORBIDDEN | `sns.set()` | Alias for set_theme → CJK broken |
| ❌ FORBIDDEN | `sns.reset_defaults()` | Resets all rcParams → CJK broken |
| ❌ FORBIDDEN | `sns.reset_orig()` | Resets all rcParams → CJK broken |
| ✅ Safe | `sns.set_context()` | Only changes font sizes, not font family |
| ✅ Safe | `sns.set_palette()` | Only changes colors |
| ✅ Safe | `sns.barplot()`, `sns.heatmap()`, etc. | All plotting functions are safe |

If you need to change seaborn style after CJK setup, re-apply the CJK font config after calling `sns.set_style()` / `sns.set_theme()`.

***

## Option B: GenerateImage (AI Image Generation)

Use GenerateImage to generate illustrations, backgrounds, hero images, and conceptual visuals directly. This is the preferred approach for custom imagery — it produces images that match the deck's style and color palette without relying on external search results.

### When to Use

- Full-bleed slide backgrounds or hero images
- Conceptual / abstract illustrations for content slides
- Supporting visuals when no real photo is required
- Any image where style coherence with the deck matters

### Workflow

1. **Write a detailed prompt** describing the desired scene, style, color tones, and mood.
2. **Choose the right `image_size`** for the target aspect ratio:
   - `landscape_16_9` — wide landscape (1024×576), for full-slide backgrounds and wide layouts
   - `landscape_4_3` — landscape (1024×768), for content area illustrations
   - `square_hd` — high-definition square (1024×1024), for headshots, profile images, square icons
   - `square` — standard square (1024×1024)
   - `portrait_3_4` — portrait (768×1024)
   - `portrait_9_16` — tall portrait (576×1024)
3. **Call GenerateImage directly** (no subagent needed). Generate each image one by one.
4. **Save and rename** to follow the standard naming convention: `{name}_{width}x{height}.png` (e.g. `hero_1024x576.png`). Store all generated images alongside other pre-generated assets in `<output-dir>/`.

### Prompt Tips

- **Be specific about style**: "a modern flat illustration of…" or "a photorealistic aerial view of…"
- **Include color guidance**: "using warm tones of terracotta and sage green" to match the slide palette
- **Describe composition**: "left side shows X, right side shows Y, with negative space in the center for text overlay"
- **Specify mood**: "professional, clean, and minimal" vs "vibrant, energetic, and bold"
- **Avoid text in images**: Generated text is often garbled — use PptxGenJS text elements instead
- **Prefer illustration style for consistency**: AI-generated photos can look uncanny — illustrations, abstract art, and stylized graphics tend to produce better results


***

## Option E: Web Search for Images

Search for relevant images when:

- Real stock photos, logos, or brand assets are needed
- Icons or logos that must be authentic are required
- Reference images for real-world objects or people

After downloading, rename to follow the naming convention: `{name}_{width}x{height}.png`.

***

## Option C: PlantUML Diagrams

Use PlantUML for sequence diagrams, state diagrams, Gantt charts, class diagrams, and other UML-style diagrams with rich semantics (participants, messages, timelines).

### When to Use

- Sequence / interaction diagrams
- State machine diagrams
- Gantt charts / project timelines
- Class / component diagrams
- Any UML-standard diagram type

### Rendering

Use the standalone script at `scripts/render_plantuml.py` which provides `returncode` checking, syntax error parsing with line numbers, retry on transient failures, and Gantt-safe DPI handling:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))
from render_plantuml import render_plantuml, PlantUMLSyntaxError, PlantUMLError, PLANTUML_THEME

try:
    render_plantuml(f"@startuml\n{PLANTUML_THEME}\nleft to right direction\nrectangle A\nrectangle B\nrectangle C\nA --> B\nB --> C\n@enduml", 'flow.png')
except PlantUMLSyntaxError as e:
    print(f"Syntax error in PlantUML code, fix the puml source and retry:\\n{e}")
except PlantUMLError as e:
    print(f"PlantUML rendering failed:\\n{e}")
```

### Tips

- **Always inject `PLANTUML_THEME`**: Every diagram must include `{PLANTUML_THEME}` after `@startuml`
- Use `participant` for services, `actor` for users, `database` for storage — each maps to distinct colors
- Use `left to right direction` for horizontal layout to reduce vertical space
- PlantUML uses `-Sdpi=150` by default; for `@startgantt` charts, omit `-Sdpi` (handled automatically by the script)

### Output Naming

Rename the final PNG to follow the standard naming convention: `{name}_{width}x{height}.png`.

***

## Option D: Graphviz Diagrams

Use Graphviz (`dot`) for flowcharts, architecture diagrams, dependency graphs, and network topology — any diagram with directed/undirected graphs of nodes and edges.

### When to Use

- Flowcharts and decision trees
- System architecture diagrams
- Dependency graphs
- Network topology diagrams
- Any node-edge graph structure

### Rendering

Use the standalone script at `scripts/render_graphviz.py` which provides `returncode` checking, syntax error parsing with line numbers, and auto size injection:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))
from render_graphviz import render_graphviz, GraphvizSyntaxError, GraphvizError, GRAPHVIZ_DPI

GRAPHVIZ_MAX_WIDTH_IN = 6.5
GRAPHVIZ_MAX_HEIGHT_IN = GRAPHVIZ_MAX_WIDTH_IN * 1.3 * 0.6

try:
    render_graphviz("digraph { rankdir=LR; nodesep=0.65; ranksep=0.85; node [fontsize=16 margin=\"0.40,0.28\"]; edge [fontsize=14 penwidth=1.5]; A -> B -> C }", 'flow.png',
                    max_width_in=GRAPHVIZ_MAX_WIDTH_IN, max_height_in=GRAPHVIZ_MAX_HEIGHT_IN)
except GraphvizSyntaxError as e:
    print(f"Syntax error in Graphviz code, fix the dot source and retry:\\n{e}")
except GraphvizError as e:
    print(f"Graphviz rendering failed:\\n{e}")
```

### Readability Rules

- **Node fontsize MUST be 16–20** — fontsize < 16 becomes unreadable when scaled down to fit a slide
- **Scale proportionally**: When increasing fontsize, also increase `margin` (e.g., `"0.40,0.28"`) and adjust `nodesep`/`ranksep` (e.g., `0.65`/`0.85`) accordingly
- **Multi-row layout (MUST for 4+ nodes)**: When 4+ nodes share the same rank, split them into 2–3 rows using `{rank=same}` with `style=invis` invisible edges to guide line breaks; use `constraint=false` for cycle/loop-back edges. Target aspect ratio 4:3 ~ 16:9 (e.g., 6 nodes → 3+3, 8 nodes → 4+4)
- **Cluster label fontsize** should match node fontsize (≥16)

### Output Naming

Rename the final PNG to follow the standard naming convention: `{name}_{width}x{height}.png`.

***

## Verify Assets Before Proceeding

```bash
# Confirm all external assets exist with dimensions in filename
ls -la *_*x*.png *_*x*.jpg 2>/dev/null

# Verify dimensions match filename
for f in *_*x*.png; do
  echo "$f: $(file "$f" | grep -oE '[0-9]+ x [0-9]+')"
done
```

**Only proceed to PptxGenJS code after:**

- [ ] All `[External]` assets from the plan are generated
- [ ] Asset files exist with `{name}_{width}x{height}.png` naming
- [ ] Filename dimensions match actual image dimensions

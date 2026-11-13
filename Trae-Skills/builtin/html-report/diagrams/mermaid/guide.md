# Mermaid Diagram Guide

Create Mermaid diagrams — flowcharts, sequence diagrams, class diagrams, state diagrams, ER diagrams, Gantt charts, mindmaps, timelines, quadrant charts, and more.

> **Note**: Mermaid is NOT the default diagram tool. Use it only when the user explicitly requests Mermaid. For most structural diagrams, prefer inline SVG (≤ 10 nodes) or Graphviz (> 10 nodes). This file serves as a reference when Mermaid is specifically requested.

---

## Select Diagram Type

Use this decision tree to pick the right diagram type, then read the corresponding file in this directory for full syntax, examples, and best practices.

```
What are you visualizing?
├─ Process / Logic flow → Flowchart
├─ Interaction between actors over time → Sequence Diagram
├─ Object-oriented structure → Class Diagram
├─ State transitions → State Diagram
├─ Database schema / entity relationships → ER Diagram
├─ Project timeline / scheduling → Gantt Chart
├─ Hierarchical concepts / brainstorming → Mindmap
├─ Chronological events → Timeline
├─ Git branching strategy → Gitgraph
├─ Proportional data → ECharts preferred; Mermaid Pie only for rough/simple proportions
├─ 2D classification / positioning → Quadrant Chart
├─ User journey / experience flow → User Journey
├─ System context / containers (C4) → C4 Diagram
├─ Requirements tracing → Requirement Diagram
├─ Block-based architecture → Block Diagram
└─ Packet/protocol structure → Packet Diagram
```

### Reference Files

| Diagram Type | File | Use For |
|-------------|------|---------|
| Flowchart | `flowchart.md` | Process flows, decision trees, architectures |
| Sequence | `sequence.md` | API calls, protocol flows, service interactions |
| Class | `class.md` | OOP design, domain models, type hierarchies |
| State | `state.md` | FSM, lifecycle management, workflow states |
| ER | `er.md` | Database design, data models, schemas |
| Gantt | `gantt.md` | Project timelines, sprints, task dependencies |
| Mindmap | `mindmap.md` | Brainstorming, concept hierarchies |
| Timeline | `timeline.md` | Chronological events, release history |
| Pie | `pie.md` | Simple proportional data |
| Gitgraph | `gitgraph.md` | Branching strategies, release flows |
| Quadrant | `quadrant.md` | Priority matrices, 2D classification |
| User Journey | `journey.md` | UX flows, customer journeys |
| C4 | `c4.md` | System architecture (Context/Container/Component) |

---

## Quick Syntax Cheat Sheet

**Flowchart:** `flowchart TD` / `LR` + nodes `[rect]` `{diamond}` `[(cylinder)]` + links `-->` `-.->` `==>`

**Sequence:** `sequenceDiagram` + `participant` + `->>` / `-->>` + `activate` / `alt` / `loop` / `par`

**Class:** `classDiagram` + `class Name { }` + `<|--` / `*--` / `o--` / `-->` / `..>`

**State:** `stateDiagram-v2` + `[*]` + `-->` + `state Name { }` + `<<choice>>` / `<<fork>>`

**ER:** `erDiagram` + `||--o{` / `||--|{` + entity attributes `{ type name PK }`

**Gantt:** `gantt` + `section` + tasks `:done/active/crit, id, start, duration`

**Mindmap:** `mindmap` + `root((text))` + indentation hierarchy

---

## Styling & Theming

Mermaid color should express structure and state, not decoration. Use these roles consistently:
- **Primary path**: the main flow or recommended route, mapped from `--page-brand` / `--accent`
- **Secondary path**: a genuinely distinct supporting route, mapped from `--chart-accent` only when the second path has explicit meaning
- **Success / warning / danger**: real semantic states, mapped from `--success`, `--warning`, `--danger`
- **Neutral**: default nodes, groups, borders, and inactive paths, mapped from `--bg`, `--bg2`, `--rule`, `--ink`, and `--muted`

Do not make rainbow flowcharts. If many node types appear, group them structurally or split the diagram instead of adding more colors.

Mermaid `themeVariables` and `classDef` values cannot be assumed to resolve CSS variables reliably. During report authoring, map the report tokens to concrete color values from `:root`, then place those resolved values in Mermaid config. Keep the local `./_shared/js/mermaid.min.js` loading rule unchanged.

### classDef (Flowchart/State)

```mermaid
flowchart LR
    A[Request]:::primary --> B[Review]:::neutral
    B --> C[Approved]:::success
    B --> D[Risk]:::warning
    B --> E[Rejected]:::danger
    classDef primary fill:#F5F2EF,stroke:#6B5E57,color:#3F3631
    classDef neutral fill:#FFFFFF,stroke:#DDD6CF,color:#24201D
    classDef success fill:#FFFFFF,stroke:#52C41A,color:#24201D
    classDef warning fill:#FFFFFF,stroke:#FAAD14,color:#24201D
    classDef danger fill:#FFFFFF,stroke:#FF4D4F,color:#24201D
```

The concrete colors above are examples of resolved report tokens. Replace them with the actual values selected for `--page-brand` / `--accent`, `--bg`, `--bg2`, `--rule`, `--ink`, and semantic tokens in the report. Do not use `--chart-series-*` for structural Mermaid diagrams.

### Theme Configuration (All Diagrams)

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {
    'primaryColor': '#F5F2EF',
    'primaryTextColor': '#3F3631',
    'primaryBorderColor': '#6B5E57',
    'lineColor': '#DDD6CF',
    'secondaryColor': '#F1EDE8',
    'tertiaryColor': '#ffffff',
    'fontFamily': 'Instrument Sans, PingFang SC, Microsoft YaHei, sans-serif'
}}}%%
flowchart TD
    A --> B --> C
```

Built-in themes: `default`, `neutral`, `dark`, `forest`, `base`

Use `theme: 'base'` when you need explicit token mapping. Use `theme: 'neutral'` when the default Mermaid styling is sufficient and the report surface remains visually quiet.

---

## Output Formats

### Option A: Raw Mermaid Code Block (Default)

Return as a fenced code block with `mermaid` language tag. Works in GitHub, GitLab, Notion, Obsidian, and most markdown renderers.

````markdown
```mermaid
flowchart LR
    A --> B --> C
```
````

### Option B: Self-Contained HTML File

When the user wants a rendered visual file, produce a single `index.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mermaid Diagram</title>
    <style>
        :root {
            --bg: #FFFFFF;
            --bg2: #F8F6F3;
            --ink: #24201D;
            --muted: #6F6660;
            --rule: #DDD6CF;
            --accent: #6B5E57;
            --radius-md: 8px;
            --space-5: 24px;
            --font-sans: "Instrument Sans", "PingFang SC", "Microsoft YaHei", sans-serif;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: var(--font-sans);
            color: var(--ink);
            background: var(--bg);
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: var(--space-5);
        }
        .container {
            background: var(--bg2);
            border: 1px solid var(--rule);
            border-radius: var(--radius-md);
            padding: var(--space-5);
            max-width: 100%;
            overflow-x: auto;
        }
        .mermaid { text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <pre class="mermaid">
            <!-- Mermaid code here -->
        </pre>
    </div>
    <script src="./_shared/js/mermaid.min.js"></script>
    <script>
        mermaid.initialize({
            startOnLoad: true,
            theme: 'neutral',
            securityLevel: 'loose',
            flowchart: { curve: 'basis', padding: 20 },
            sequence: { mirrorActors: false },
        });
    </script>
</body>
</html>
```

**Note**: The example above uses the local bundled `mermaid.min.js` (copied to `_shared/js/` by the report scaffold). No CDN required.

---

## General Best Practices

1. **Keep diagrams focused** — one diagram per concept. Split complex systems into multiple diagrams.
2. **Readable node labels** — 2-5 words per node. Use abbreviations or IDs for long names.
3. **Consistent direction** — pick one flow direction and stick with it.
4. **Limit complexity** — max ~20 nodes per flowchart, ~8 participants per sequence, ~15 states per state diagram.
5. **Use subgraphs/groups** — reduce visual clutter by grouping related elements.
6. **Label all relationships** — arrows without labels are ambiguous.
7. **Color with purpose** — encode primary path, secondary path, success, warning, danger, and neutral states only.
8. **Avoid quantitative misuse** — use ECharts for real data charts; Mermaid diagrams should explain structure.
9. **Keep architecture diagrams readable** — if labels become tiny, legends detach from the graph, or connector crossings exceed two, split the diagram or re-layout with lanes/groups.
10. **Target Mermaid v10+** — stick to stable syntax; avoid experimental features.

---

## Common Pitfalls

| Issue | Solution |
|-------|----------|
| Node text with special chars breaks | Wrap in quotes: `A["Text with (parens)"]` |
| Long labels cause overlap | Use short IDs + `<br/>` for line breaks |
| Diagram too wide | Switch direction (LR → TD) or split into sub-diagrams |
| Links crossing confusingly | Reorder node definitions to minimize crossings |
| Subgraph styling not applied | Use `classDef` after subgraph definition |
| Mermaid version incompatibility | Stick to core syntax; avoid experimental features |

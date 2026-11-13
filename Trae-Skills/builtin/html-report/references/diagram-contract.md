# Diagram Contract

Use this contract for architecture diagrams, flowcharts, system maps, process
diagrams, and other structural visuals.

## Tool Selection

- Mermaid: ordinary flows, sequences, states, relationships, timelines, and
  other compact structural diagrams.
- Graphviz: dependency graphs, dense directed relationships, and any diagram with
  complex automatic layout needs.
- PlantUML: sequence, component, deployment, C4, and UML-style diagrams that
  need stronger syntax.
- HTML/CSS grid: very small linear processes or content-like architecture blocks.
- Inline SVG: only when the user explicitly requests custom vector art or the
  diagram cannot be expressed adequately by the compact source-first tools.
- ECharts: quantitative data charts only.

Choose the cheapest correct representation. Do not hand-write SVG coordinates
for every simple diagram; compact source reduces output size and lets a layout
engine handle positioning.

## Readability Rules

- Node labels should be short, usually 2-5 words.
- Diagram source or styles must declare node text at 14px or larger.
- Node height should be at least 40px for a single line and about 56px for two
  lines.
- Keep one shape language per diagram. Do not mix capsules, sharp rectangles,
  circles, and floating cards without semantic reason.
- Group every node into a visible domain, layer, lane, or module when the system
  has more than one domain.

## Connector Rules

- Prefer orthogonal or simple directional connectors.
- Label relationships when the meaning is not obvious.
- Use neutral connector colors by default.
- Reserve accent color for the primary path or main data flow.
- Solid and dashed lines must have explicit meaning. Put that meaning in a
  legend if both appear.
- When the source-authored layout visibly declares more than two crossings,
  re-layout with lanes, buses, grouping, or split the diagram.

## Complexity Limits

- Flowchart-like diagrams should stay around 20 nodes or fewer.
- Architecture diagrams should stay around 5 layers or fewer and 8 nodes or
  fewer per layer.
- If the system exceeds the limit, create an overview plus one or more drilldown
  diagrams.

## Bitmap And Zoom Rules

- Do not use AI-generated bitmap images as primary architecture diagrams.
- PlantUML and Graphviz rendered PNGs must be saved as relative assets under
  `assets/`, not embedded as base64.
- Non-decorative diagram images must declare sufficient intrinsic dimensions and
  responsive sizing for normal report width. Add selective zoom only when the
  content density indicates that detail will require enlargement; Lightbox is
  not a default dependency.
- Every diagram image needs meaningful alt text and a visible caption.

## QA Boundary

Static QA verifies declared sizes, labels, grouping, and complexity limits.
Rendered node readability, crossings, clipping, and zoom behavior remain `NOT RUN`
unless the user explicitly requests the optional isolated rendered QA in
`references/qa-checklist.md`. Do not open or control the user's browser to prove
these checks.

# Information Scene Rendering Upgrade Checklist

Use this checklist when upgrading charts, pages, and graph scenes with shared
structured-information styling. The goal is broad non-semantic presentation
variety without changing task semantics, evidence contracts, verifier payloads,
or answer distributions.

## Scope

Apply this workflow scene by scene to renderers that look like structured
information artifacts:

- charts, chart panels, dashboards, editorial figures, and chart callouts
- forms, invoices, receipts, schedules, timelines, maps, and document panels
- node-link graphs, route diagrams, pipe/metro graph views, and graph panels

Charts, pages, and graph use the shared `information_scene_style` family under
`trace/tasks/shared/visual_style/`. Puzzles, games, and icons use
`panel_scene_style`; geometry and physics use `technical_diagram_style`.

## Preflight Rules

- Treat these upgrades as render-only unless a scene-specific issue explicitly
  requires a semantics change.
- Sample style before rendering and record it under `render_spec`.
- Do not apply a broad post-render recolor, crop, rotate, or move pass.
- Preserve semantic colors. If a task asks about color or uses color as
  evidence, pass protected semantic RGB values into the style resolver and
  filter unsafe palettes/treatments.
- Separate canvas/background styling from semantic mark styling. A scene should
  explicitly decide these non-semantic layers:
  - outer canvas/page background;
  - plot area or chart panel background;
  - card/table/callout/surface fill;
  - grid, axis, tick, border, and guide-line colors;
  - title/chrome/context fills.
  Avoid the current failure mode where every layer stays white/off-white.
- When expanding palettes, include visibly distinct but readable light themes,
  not only small off-white shifts. Candidate themes should cover cool, warm,
  mint/green, lavender, blue-gray, newspaper gray, parchment/editorial, and
  high-contrast light variants. Dark themes need scene-specific approval.
- Plot/panel backgrounds may be tinted independently of the canvas when exact
  mark/value reading remains clear. Keep sufficient contrast against marks,
  text, grid lines, and evidence overlays.
- Keep style choices independent of answer value, correct option, query id, and
  difficulty bucket.
- Compute evidence bboxes/points after final layout and style-dependent stroke
  widths are resolved.
- Use coordinate-preserving post-image noise with default apply probability
  `0.5` unless a task documents a narrower reason.
- Optional context/distractor text must use the vendored pools documented in
  `docs/workflows/SHARED_CONTEXT_TEXT_ASSETS.md`; every drawn text element must
  be trace-backed, bbox-backed, and explicitly non-answer-bearing unless the
  task verifier scopes it in.
- Visible text should use the vendored font families documented in
  `docs/workflows/SHARED_FONT_ASSETS.md`. Sample fonts by meaningful text block
  with seed/namespace determinism: one family for a chart's labels, one family
  for an option set, one family per page section or context box, etc.
- For graph scenes, do not add graph-like distractor marks that could be
  mistaken for nodes, edges, labels, or route segments.
- Upgrade one scene at a time, regenerate that scene review workbook, and
  inspect output before moving to another scene.
- Do not run solve-rate jobs unless explicitly requested.

## Style Ownership

- Shared low-level style definitions live in
  `trace/tasks/shared/visual_style/information_scene.py`.
- Charts consume them through `trace/tasks/charts/shared/information_style.py`.
- Pages consume them through `trace/tasks/pages/shared/information_style.py`.
- Graph consumes them through `trace/tasks/graph/shared/information_style.py`.
- Domain adapters should be thin. They map shared roles such as canvas, surface,
  panel, grid, axis, connector, label, header, callout, and accent colors onto
  domain-specific renderers.
- Scene renderers still own semantic geometry, layout, entity tracing, visible
  values, chart marks, graph topology, and evidence projection.

## Chart Scene Review Addendum

When upgrading a chart scene, review the following before changing solve-rate
configuration:

1. **Palette coverage**
   - Is the outer canvas always white/off-white?
   - Is the plot area or panel always white?
   - Are axes/grid/ticks/borders always the same gray?
   - Does the scene support enough light palette families to avoid a uniform
     house style?

2. **Background and plot readability**
   - Preserve exact-value readability for tasks that read values from axes,
     value labels, guides, legends, or printed cells.
   - For value-readout tasks, guide lines and value labels should remain
     contrast-safe after tinting.
   - For heatmaps, maps, matrix grids, and color-encoded charts, protect the
     semantic color scale before applying surrounding style colors.

3. **Semantic color protection**
   - Mark/category/series colors that encode values, groups, regions, or legend
     identities must be passed as protected colors to shared style sampling when
     possible.
   - Non-semantic chart chrome may vary freely; semantic mark palettes may vary
     only through task-owned palette logic.

4. **Typography**
   - Use `assets/fonts/` through `sample_font_family(...)` and
     `load_font(..., font_family=...)`.
   - Keep one sampled family for all labels within one chart/panel unless the
     scene has clear separate text regions.
   - Avoid display/condensed fonts for dense tick labels, table cells, small map
     labels, and other tight layouts unless inspection confirms they remain
     readable.

5. **Context and distractors**
   - If the scene gets report/news/dashboard/app-window context, use
     `assets/context_text/` and record every context text bbox/source/font.
   - Place context in reserved regions first. Use content-frame translation only
     after bbox-transform tests exist for that scene.
   - Distractors must not create alternative valid answers or look like extra
     chart marks inside the semantic plot area.

6. **Layout and spacing**
   - Add only bounded layout jitter or reserved-region placement that preserves
     evidence bboxes and does not crop axes/legends.
   - Recheck known chart-specific rendering issues from coverage notes, such as
     label overlap, tiny legends, overly thin flow bands, crowded value labels,
     and ambiguous highlight boxes.

7. **Metadata**
   - Record sampled palette/style ids, RGB roles, font families, context layer
     metadata, semantic protected colors, and final layout bboxes in
     `render_spec`.
   - Scene review workbooks should make these choices visible enough to inspect
     variation across 25 samples per task.

## Required Metadata

Record enough metadata to audit the rendered scene:

- treatment id, palette id, and combined style pack
- resolved RGB roles for canvas, surface, panel, header, text, muted text,
  grid, axis, guide, connector, neutral mark, accent, highlight, callout, and
  shadows
- layout/style settings such as content margin, panel padding, title-band
  height, frame width, corner radius, shadow offset, guide density, context
  density, and typography scale
- sampled font families for answer-bearing text roles; context text font
  families belong in `context_text_layer.elements[]`
- chrome mode: `none`, `thin_frame`, or `accent_frame` with default weights
  `0.5`, `0.25`, and `0.25`
- protected semantic colors and contrast/separation checks
- background metadata and post-image noise metadata
- scene-specific final layout metadata, scene bbox, and evidence maps

The current metadata key is `render_spec.information_scene_style`. Graph
node-link tasks also carry the same payload under
`render_spec.panel_geometry.information_scene_style` because their render spec
already treats panel geometry as the scene-local layout contract.

## Scene Review Procedure

For each scene:

1. Inspect current renderer and configs for hardcoded backgrounds, narrow
   palettes, fixed style roles, semantic color usage, and chart-specific
   rendering issues called out in coverage notes.
2. Decide which visual layers can safely vary: canvas, plot/panel fill, surface
   cards, axes/grid/ticks, typography, context text, borders, shadows, and
   layout jitter.
3. Resolve `information_scene_style` before any drawing.
4. Use the domain adapter to map shared style roles into the existing renderer.
5. Preserve task-owned semantic colors, visible values, graph topology, and
   answer-bearing labels.
6. Compile touched modules.
7. Smoke-generate multiple seeds and verify:
   - style metadata is present in `render_spec`
   - evidence remains inside the final canvas
   - semantic colors remain unchanged where required
   - canvas and plot/panel backgrounds both show meaningful variation when safe
   - style changes are visible but non-semantic
   - context/distractor text uses `assets/context_text/`, records manifest/source
     metadata, and stays outside the answer contract unless explicitly scoped in
   - text uses `assets/fonts/` through the shared font sampler/loader and keeps
     each meaningful block internally consistent
   - labels, legends, value labels, tick labels, highlights, and flow/region
     boundaries remain readable
   - post-image noise remains coordinate-preserving
8. Regenerate the scene review workbook.
9. Do not run solve-rate jobs unless explicitly requested.

Example scene-review command:

```bash
PYTHONPATH=. python scripts/run_task_review.py \
  --tasks task_charts__single_series__value_predicate_count,task_pages__infographic__metric_arithmetic_value,task_graph__node_link__degree_predicate_count \
  --mode inspection \
  --out-root plans/task-reviews \
  --seed 20260523 \
  --random-count 25 \
  --max-attempts-per-instance 200 \
  --workers 4
```

## Current Treatment Registry

- `clean_default`
- `report_card`
- `dashboard_tile`
- `executive_dashboard`
- `news_graphic`
- `academic_figure`
- `journal_appendix`
- `infographic_panel`
- `poster_explainer`
- `annotated_callout`
- `caption_heavy_figure`
- `source_note_sheet`
- `compact_small_multiples`
- `data_table_report`
- `web_article_embed`
- `desktop_app_window`
- `control_console`
- `presentation_slide`
- `print_scan_sheet`
- `dark_analytics_board`

## Current Palette Registry

- `neutral_report`
- `publication_gray`
- `cool_business`
- `warm_editorial`
- `soft_mint`
- `slate_amber`
- `ink_teal`
- `burgundy_sage`
- `indigo_ochre`
- `coastal_blue`
- `atlas_map`
- `metro_bright`
- `data_viz_classic`
- `okabe_ito_light`
- `pastel_dashboard`
- `monochrome_news`
- `high_contrast_light`
- `dark_analytics`
- `dark_mint`
- `dark_blue_orange`

# Technical Diagram Rendering Upgrade Checklist

Use this checklist when upgrading geometry and physics scenes with shared
technical-diagram styling. The goal is broader non-semantic visual variety
without changing task semantics, annotation contracts, verifier payloads, or
answer distributions.

## Scope

Apply this workflow scene by scene to geometry and physics renderers that use:

- coordinate grids, graph paper, axes, geometric construction diagrams, formula
  figures, or dimension annotations
- physics apparatus diagrams, circuit diagrams, ray diagrams, force diagrams,
  field maps, plots, or lab-style schematics

Geometry and physics use the shared `technical_diagram_style` family under
`trace/tasks/shared/visual_style/`. Puzzles, games, and icons use
`panel_scene_style`; do not import the puzzle/game adapters for technical
diagrams.

## Preflight Rules

- Treat these upgrades as render-only unless a scene-specific issue explicitly
  requires a semantics change.
- Sample style before rendering and record it under `render_spec`.
- Do not apply a broad post-render recolor, crop, rotate, or move pass.
- Preserve semantic colors. If a task asks about color or uses color as
  annotation, pass protected semantic RGB values into the style resolver and
  filter unsafe palettes/treatments.
- Keep style choices independent of answer value, correct option, query id, and
  difficulty bucket.
- Compute annotation bboxes/points after final layout and style-dependent stroke
  widths are resolved.
- For full coordinate-plane geometry scenes, resolve the bounded graph-paper
  panel before projecting graph-unit geometry. Treat `graph_panel_bbox_px` as
  the semantic scene bbox and keep the canvas outside that panel free of graph
  paper.
- Use coordinate-preserving post-image noise with default apply probability
  `0.5` unless a task documents a narrower reason.
- Upgrade one scene at a time, regenerate that scene's review artifacts,
  inspect them in the browser review app, and then move to another scene.
- Do not run solve-rate jobs unless explicitly requested.

## Style Ownership

- Shared low-level style definitions live in
  `trace/tasks/shared/visual_style/technical_diagram.py`.
- Geometry consumes them through
  `trace/tasks/geometry/shared/diagram_style.py`.
- Physics consumes them through
  `trace/tasks/physics/shared/diagram_style.py`.
- Domain adapters should be thin: they map shared roles such as paper fill,
  grid lines, axes, guides, labels, strokes, and accents onto domain-specific
  renderers.
- Scene renderers still own semantic geometry, layout, entity tracing, and
  annotation projection.

## Required Metadata

Record enough metadata to audit the rendered diagram:

- treatment id, palette id, and combined style pack
- resolved RGB roles for canvas, paper, grid, axis, guides, labels, strokes,
  accents, fills, and option/label surfaces
- stroke widths for axes, grid lines, label strokes, and panel borders
- grid/background kind, spacing, major-line cadence, and texture
- protected semantic colors and contrast/separation checks
- independent frame mode: `none`, `plain_outline`, or `matching_outline`
  with default weights `0.5`, `0.25`, and `0.25`
- background metadata and post-image noise metadata
- for full coordinate-plane graph-paper scenes: `layout_placement`,
  `graph_panel_bbox_px`, `graph_content_bbox_px`, `graph_origin_px`,
  `graph_spacing_px`, and `scene_bbox_px`

The current metadata key is `render_spec.technical_diagram_style`.

## Scene Review Procedure

For each scene:

1. Inspect current renderer and configs for hardcoded backgrounds, narrow
   palettes, fixed style roles, and semantic color usage.
2. Resolve `technical_diagram_style` before any drawing.
3. Use the domain adapter to map shared style roles into the existing renderer.
4. Preserve task-owned semantic colors and answer-bearing labels.
5. Compile touched modules.
6. Smoke-generate multiple seeds and verify:
   - style metadata is present in `render_spec`
   - annotation remains inside the final canvas
   - semantic colors remain unchanged where required
   - style changes are visible but non-semantic
   - post-image noise remains coordinate-preserving
7. Regenerate the scene review artifacts, reload the browser review app index,
   and inspect the scene there.
8. Do not run solve-rate jobs unless explicitly requested.

Example scene-review command:

```bash
PYTHONPATH=. python scripts/run_task_review.py \
  --tasks task_physics__electrostatic_field__field_direction_choice,task_physics__electrostatic_field__zero_field_point_label,task_physics__electrostatic_field__potential_value \
  --mode inspection \
  --out-root review/task-reviews \
  --seed 20260523 \
  --random-count 100 \
  --max-attempts-per-instance 120 \
  --workers 4
```

## Current Treatment Registry

- `bare_canvas`
- `off_white_paper`
- `graph_paper_light`
- `engineering_grid`
- `millimeter_paper`
- `blueprint_grid`
- `dark_blueprint`
- `lab_notebook`
- `ruled_notebook`
- `worksheet_panel`
- `textbook_figure`
- `presentation_slide`
- `whiteboard`
- `chalkboard_dark`
- `drafting_vellum`
- `isometric_grid`
- `subtle_scan_sheet`
- `exam_problem_box`
- `lab_card`
- `monochrome_print`

## Current Palette Registry

- `neutral_ink`
- `cool_gray_blue`
- `warm_paper_ink`
- `graphite_blue`
- `engineering_cyan`
- `blueprint_white`
- `blueprint_amber`
- `lab_teal`
- `physics_orange`
- `geometry_indigo`
- `chalk_soft`
- `whiteboard_marker`
- `green_grid`
- `violet_annotation`
- `sepia_print`
- `slate_mint`
- `navy_lab`
- `steel_crimson`
- `olive_field`
- `magenta_cyan`

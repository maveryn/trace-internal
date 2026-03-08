# TRACE Status

Date: 2026-03-08

## Implemented
1. Deterministic build pipeline with sidecar trace shards and atomic finalize.
2. Typed train-instance ABI with mandatory `trace_ref`.
3. Pre-finalize validation + structured error codes.
4. Strict reproducibility comparison mode.
5. External prompt-bundle system with dual output modes.
6. Deterministic background/noise visual variation helpers.
7. Domain + task-group default config loading with section-level `shared` + `task_overrides` composition.
8. Shared geometry single-object scene helpers (`graph_paper`, `graph_rendering`, `single_object_scene`, `angle_geometry`, `polygon_geometry`).
9. Objective-style geometry measurement tasks (single shape/object per image):
   - angle measure (primitive-angle, triangle/quadrilateral polygon-angle, or line-intersection source) with deterministic balanced source/answer sampling defaults, minimum ray length constraints, and MCQ query formatting,
   - area measure (triangle/quadrilateral + ellipse variants),
   - perimeter measure (triangle/quadrilateral + circle variants),
   - length measure (segment, polygon side, circle radius/diameter, ellipse major/minor axis variants).
   - angle measure now uses option-letter (`A..E`) ground-truth answers for MCQ output mode.
10. Geometry graph-paper backgrounds now render center-origin cues by default: axis arrows + signed integer scale labels across the full visible axis range (no origin text label).
11. Geometry graph-paper colors now vary within configured ranges per instance; axis lines are sampled darker than minor/major grid lines by construction.
12. Geometry shape ink style is now sampled from shared domain-config color ranges with Lab-distance constraints from background anchor colors; area/perimeter tasks reuse one shared task-group shape pipeline.
13. Geometry area/perimeter conic answers use `pi_expression` answer type (`kπ`) with labeled graph-point-map evidence.
14. Active prompt bundles now use explicit JSON output contracts in both modes (`answer_only` + `answer_and_evidence`) across geometry and tile tasks.
15. Geometry analytical_2d area task supports one explicit + one derived variant per shape family (rectangle, triangle, parallelogram, trapezoid, rhombus, circle, ellipse), uses vertex/endpoint labels plus numeric measurement text on the figure, and emits structured `measurement_ref_map` evidence (`annotation -> value`) on non-graph-paper solid backgrounds.

## Active tasks
1. `task_tile_path_shortest_path` (`domain=tile`, `task_group=path`)
2. `task_geometry_measurement_angle` (`domain=geometry`, `task_group=measurement`)
3. `task_geometry_measurement_area` (`domain=geometry`, `task_group=measurement`)
4. `task_geometry_measurement_perimeter` (`domain=geometry`, `task_group=measurement`)
5. `task_geometry_measurement_length` (`domain=geometry`, `task_group=measurement`)
6. `task_geometry_analytical_2d_area` (`domain=geometry`, `task_group=analytical_2d`)

## Current quality baseline
1. Tests are required to pass before finalize.
2. Sample tooling supports per-task artifacts, per-query distribution reports, and per-domain combined Excel workbooks with embedded image previews.

## Next priorities
1. Continue objective-first refactor for additional domains (tile/icons/charts/graphs/documents).
2. Introduce cross-domain `scene_variant` and role-binding schema in architecture docs/contracts.
3. Add future polygon variants as deferred tasks (diameter, min-side, max-side) after current scope stabilizes.

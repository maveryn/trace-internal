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
   - angle measure (primitive-angle or line-intersection source) with deterministic balanced source/answer sampling defaults, minimum ray length constraints, axis-aligned-ray construction, and nearest-integer degree query formatting,
   - area measure (triangle/quadrilateral + ellipse variants),
   - perimeter measure (triangle/quadrilateral + circle variants),
   - length measure (segment, polygon side, circle radius/diameter, ellipse major/minor axis variants),
   - slope measure (single finite line crossing x-axis at an integer lattice coordinate, with nearest-tenth numeric answers and x-axis crossing-point evidence).
   - angle measure ground-truth answers are nearest-integer degree values with raw-angle tolerance bounded by `0.05°`.
10. Geometry graph-paper backgrounds now render center-origin cues by default: axis arrows + signed integer scale labels across the full visible axis range (no origin text label).
11. Geometry graph-paper colors now vary within configured ranges per instance; axis lines are sampled darker than minor/major grid lines by construction.
12. Geometry shape ink style is now sampled from shared domain-config color ranges with Lab-distance constraints from background anchor colors; area/perimeter tasks reuse one shared task-group shape pipeline.
13. Geometry area/perimeter conic answers use `pi_expression` answer type (`kπ`) with labeled graph-point-map evidence.
14. Active prompt bundles now use explicit JSON output contracts in both modes (`answer_only` + `answer_and_evidence`) across geometry and tile tasks, with exactly 5 high-quality variants per required composition layer.
15. Geometry analytical_2d area task supports one explicit + one derived variant per shape family (rectangle, triangle, parallelogram, trapezoid, rhombus, circle, ellipse), uses vertex/endpoint labels plus numeric measurement text on the figure, and emits structured `measurement_ref_map` evidence (`annotation -> value`) on non-graph-paper solid backgrounds.
16. Geometry analytical_3d volume task supports six annotated-solid variants (rectangular prism, triangular prism, square pyramid, cylinder, cone, sphere) with deterministic balanced variant sampling and typed integer/`kπ` answers.
17. Analytical 2D shape-unit scaling is now decoupled from graph-paper `graph_cells` limits via dedicated render params (`analytical_unit_spacing_px`, `analytical_unit_padding_px`).

## Active tasks
1. `task_tile_path_shortest_path` (`domain=tile`, `task_group=path`)
2. `task_geometry_measurement_angle` (`domain=geometry`, `task_group=measurement`)
3. `task_geometry_measurement_area` (`domain=geometry`, `task_group=measurement`)
4. `task_geometry_measurement_perimeter` (`domain=geometry`, `task_group=measurement`)
5. `task_geometry_measurement_length` (`domain=geometry`, `task_group=measurement`)
6. `task_geometry_measurement_slope` (`domain=geometry`, `task_group=measurement`)
7. `task_geometry_analytical_2d_area` (`domain=geometry`, `task_group=analytical_2d`)
8. `task_geometry_analytical_3d_volume` (`domain=geometry`, `task_group=analytical_3d`)

## Current quality baseline
1. Tests are required to pass before finalize.
2. Distribution QA uses `scripts/check_task_answer_distribution.py` with per-variant answer-only checks (`unique_answers >= 5`, `max_answer_frequency < 25%`, numeric `max_five_bin_frequency <= 50%`) and multithreaded sample generation (`--workers`).
3. Task-review tooling writes per-task artifacts under `task-reviews/<task_id>/`, including one inspection workbook with one sheet per task variant.

## Next priorities
1. Continue objective-first refactor for additional domains (tile/icons/charts/graphs/documents).
2. Introduce cross-domain `scene_variant` and role-binding schema in architecture docs/contracts.
3. Add future polygon variants as deferred tasks (diameter, min-side, max-side) after current scope stabilizes.

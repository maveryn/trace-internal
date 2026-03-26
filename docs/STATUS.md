# TRACE Status

Date: 2026-03-26

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
   - area measure (triangle/quadrilateral + ellipse variants, with triangle/quadrilateral target-area sampling from exact feasible support),
   - perimeter measure (triangle/quadrilateral + circle variants, with triangle/circle target sampling from exact feasible support),
   - length measure (segment, polygon side, circle radius/diameter, ellipse major/minor axis variants),
   - slope measure (single finite line crossing x-axis at an integer lattice coordinate, with nearest-tenth numeric answers and x-axis crossing-point evidence).
   - angle measure ground-truth answers are nearest-integer degree values with raw-angle tolerance bounded by `0.05°`.
10. Geometry graph-paper backgrounds now render center-origin cues by default: axis arrows + signed integer scale labels across the full visible axis range (no origin text label).
11. Geometry graph-paper colors now vary within configured ranges per instance; axis lines are sampled darker than minor/major grid lines by construction.
12. Geometry shape ink style is now sampled from shared domain-config color ranges with Lab-distance constraints from background anchor colors; area/perimeter tasks reuse one shared task-group shape pipeline.
13. Geometry area/perimeter conic answers use `pi_expression` answer type (`kπ`) with coordinate-only graph-point evidence (`graph_point`).
14. Active prompt bundles now use explicit JSON output contracts in both modes (`answer_only` + `answer_and_evidence`) across geometry and tile tasks, with exactly 5 high-quality variants per required composition layer.
15. Geometry analytical_2d area task supports one explicit + one derived variant per shape family (rectangle, triangle, parallelogram, trapezoid, rhombus, circle, ellipse), uses vertex/endpoint labels plus numeric measurement text on the figure, and emits structured `measurement_ref_map` evidence (`annotation -> value`) on non-graph-paper solid backgrounds.
16. Geometry analytical_3d volume task supports six annotated-solid variants (rectangular prism, triangular prism, square pyramid, cylinder, cone, sphere) with deterministic balanced variant sampling and typed integer/`kπ` answers.
17. Geometry analytical_3d surface-area task supports the same six annotated solids with total-surface-area questions, integer/`kπ` answer types, and structured `measurement_ref_map` evidence.
18. Analytical 2D shape-unit scaling is now decoupled from graph-paper `graph_cells` limits via dedicated render params (`analytical_unit_spacing_px`, `analytical_unit_padding_px`, `analytical_scene_fill_ratio`).
19. Geometry measurement area/perimeter tasks now use unlabeled coordinate-only evidence (`graph_point_set` for polygons, `graph_point` for ellipse/circle) and keep shape vertices/reference points strictly inside the plotted graph-paper interior.
20. Geometry analytical_2d length task supports six derived annotated-scene variants (triangle altitude, rectangle diagonal, rhombus diagonals, isosceles trapezoid height, inscribed square, circle chord) with decimal answers rounded to one decimal place and structured `measurement_ref_map` evidence.
21. Analytical 2D length rendering now reserves explicit scene margin and uses local collision-aware text placement so labels/value annotations stay off geometry and away from the canvas edge more reliably.
22. Tile count now includes `task_tile_count_color_count` and `task_tile_count_color_components`, the first single-board `rectangular_tiling` tasks with dynamic canvas sizing, left/top coordinate gutters, coordinate-grounded `grid_point_set` evidence, and shared rectangular-board count-family helpers.
23. Tile shared 4-neighbor graph helpers now live under `trace/tasks/tile/shared/grid_graph.py`, which is reused across pathfinding and color-component counting instead of staying under a path-specific module name.
24. Tile reachability now includes `task_tile_reachability_reachable_count`, a single-board rectangular blocked-grid task with one purple start tile, black obstacle tiles, row/column coordinate gutters, and coordinate-grounded reachable-set evidence.

## Active tasks
1. `task_tile_count_color_count` (`domain=tile`, `task_group=count`)
2. `task_tile_count_color_components` (`domain=tile`, `task_group=count`)
3. `task_tile_path_shortest_path` (`domain=tile`, `task_group=path`)
4. `task_tile_reachability_reachable_count` (`domain=tile`, `task_group=reachability`)
5. `task_geometry_measurement_angle` (`domain=geometry`, `task_group=measurement`)
6. `task_geometry_measurement_area` (`domain=geometry`, `task_group=measurement`)
7. `task_geometry_measurement_perimeter` (`domain=geometry`, `task_group=measurement`)
8. `task_geometry_measurement_length` (`domain=geometry`, `task_group=measurement`)
9. `task_geometry_measurement_slope` (`domain=geometry`, `task_group=measurement`)
10. `task_geometry_analytical_2d_area` (`domain=geometry`, `task_group=analytical_2d`)
11. `task_geometry_analytical_2d_length` (`domain=geometry`, `task_group=analytical_2d`)
12. `task_geometry_analytical_3d_volume` (`domain=geometry`, `task_group=analytical_3d`)
13. `task_geometry_analytical_3d_surface_area` (`domain=geometry`, `task_group=analytical_3d`)

## Current quality baseline
1. Tests are required to pass before finalize.
2. Distribution QA uses `scripts/check_task_answer_distribution.py` with per-variant answer-only checks (`unique_answers >= 5`, `max_answer_frequency < 25%`) and multithreaded sample generation (`--workers`); numeric 5-bin summaries remain reported for review but are not hard pass/fail gates.
3. Task-review tooling writes per-task artifacts under `task-reviews/<task_id>/`, including one inspection workbook named `<task_id>.xlsx` with one sheet per task variant.
4. The current active geometry review set (5 measurement + 2 analytical_2d + 2 analytical_3d tasks) passes distribution review under the active gates.

## Next priorities
1. Continue objective-first refactor for additional domains (tile/icons/charts/graphs/documents).
2. Introduce cross-domain `scene_variant` and role-binding schema in architecture docs/contracts.
3. Add future polygon variants as deferred tasks (diameter, min-side, max-side) after current scope stabilizes.

# TRACE Status

Date: 2026-03-27

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
22. Geometry analytical_2d perimeter task supports five derived annotated-scene variants (right triangle, rectangle, rhombus, isosceles trapezoid, inscribed square) with decimal answers rounded to one decimal place and structured `measurement_ref_map` evidence.
23. Geometry analytical_2d composite-area task supports five shaded/composite polygon variants (inner-rectangle cutout, triangle cutout, rectangle+triangle union, L-shape cutout, step-rectangle union) with integer answers and structured `measurement_ref_map` evidence.
24. Shared analytical 2D scene rendering now supports reusable polygon fill semantics (`shaded`, `background`) so composite/shaded objectives can reuse one collision-aware render stack instead of task-local draw overlays.
25. Geometry comparison now includes `task_geometry_comparison_angle`, `task_geometry_comparison_length`, `task_geometry_comparison_area`, and `task_geometry_comparison_perimeter`, each with 4–6 labeled graph-paper objects, `largest`/`smallest` winner queries, `option_letter` answers, and winner-evidence graph-point sets.
26. Geometry counting now includes `task_geometry_counting_angle`, `task_geometry_counting_triangle`, `task_geometry_counting_quadrilateral`, `task_geometry_counting_shape_type`, and `task_geometry_counting_convexity`, all non-graph-paper multi-object scenes with integer answers and sorted `label_set` evidence; angle scenes count acute/right/obtuse classes, triangle scenes count equilateral / isosceles-but-not-equilateral / scalene / right / acute / obtuse classes, quadrilateral scenes count square / rectangle-but-not-square / rhombus-but-not-square / parallelogram-only classes, mixed-shape scenes count triangle / quadrilateral / pentagon / hexagon / circle / ellipse instances, and convexity scenes count convex vs concave polygons using strict shared polygon classification.
27. Icons counting now includes `task_icons_counting_type`, `task_icons_counting_orientation`, and `task_icons_counting_color`, all using a two-panel `Reference` + `Scene` image, integer answers, and scene-only `bbox_set` evidence in final image coordinates; type counting matches icon identity against the curated 3000-icon Prism pool, orientation counting uses the curated asymmetric subset and same-icon scenes with rotation-based orientation queries, and color counting uses same-icon scenes so the only varying predicate is tint, with a stricter Lab-distance threshold (`60`). These tasks sample `target_count` independently in `0..10` and `distractor_count` independently in `1..10`, place icons randomly in the scene panel with at most `10%` pairwise overlap (normalized by the smaller box area), and apply per-icon subtle noise before compositing; the sampled palette, overlap/noise config, final tints, and per-instance noise edits are recorded in trace metadata.
28. Icons transformation now includes `task_icons_transformation_pair_count`, a two-panel `Reference` + labeled `Scene` grid task with integer answers and sorted `label_set` evidence; the Reference pair shows one canonical D4 transform, Scene cells each show `icon -> transformed icon`, and the task counts how many cells apply the same rule. The task uses the curated asymmetric icon pool, rejects icon/transform pairs that collapse visually under rendered-silhouette checks, and records the sampled transform ids plus per-icon subtle noise in trace metadata.

## Active tasks
1. `task_tile_path_shortest_path` (`domain=tile`, `task_group=path`)
2. `task_geometry_comparison_angle` (`domain=geometry`, `task_group=comparison`)
3. `task_geometry_comparison_area` (`domain=geometry`, `task_group=comparison`)
4. `task_geometry_comparison_length` (`domain=geometry`, `task_group=comparison`)
5. `task_geometry_comparison_perimeter` (`domain=geometry`, `task_group=comparison`)
6. `task_geometry_counting_angle` (`domain=geometry`, `task_group=counting`)
7. `task_geometry_counting_triangle` (`domain=geometry`, `task_group=counting`)
8. `task_geometry_counting_quadrilateral` (`domain=geometry`, `task_group=counting`)
9. `task_geometry_counting_shape_type` (`domain=geometry`, `task_group=counting`)
10. `task_geometry_counting_convexity` (`domain=geometry`, `task_group=counting`)
11. `task_geometry_measurement_angle` (`domain=geometry`, `task_group=measurement`)
12. `task_geometry_measurement_area` (`domain=geometry`, `task_group=measurement`)
13. `task_geometry_measurement_perimeter` (`domain=geometry`, `task_group=measurement`)
14. `task_geometry_measurement_length` (`domain=geometry`, `task_group=measurement`)
15. `task_geometry_measurement_slope` (`domain=geometry`, `task_group=measurement`)
16. `task_geometry_analytical_2d_area` (`domain=geometry`, `task_group=analytical_2d`)
17. `task_geometry_analytical_2d_length` (`domain=geometry`, `task_group=analytical_2d`)
18. `task_geometry_analytical_2d_perimeter` (`domain=geometry`, `task_group=analytical_2d`)
19. `task_geometry_analytical_2d_composite_area` (`domain=geometry`, `task_group=analytical_2d`)
20. `task_geometry_analytical_3d_volume` (`domain=geometry`, `task_group=analytical_3d`)
21. `task_geometry_analytical_3d_surface_area` (`domain=geometry`, `task_group=analytical_3d`)
22. `task_icons_counting_type` (`domain=icons`, `task_group=counting`)
23. `task_icons_counting_orientation` (`domain=icons`, `task_group=counting`)
24. `task_icons_counting_color` (`domain=icons`, `task_group=counting`)
25. `task_icons_transformation_pair_count` (`domain=icons`, `task_group=transformation`)

## Current quality baseline
1. Tests are required to pass before finalize.
2. Distribution QA uses `scripts/check_task_answer_distribution.py` with per-variant answer-only checks (`unique_answers >= 5`, `max_answer_frequency < 25%`) and multithreaded sample generation (`--workers`); numeric 5-bin summaries remain reported for review but are not hard pass/fail gates.
3. Task-review tooling writes per-task artifacts under `task-reviews/<task_id>/`, including one inspection workbook named `<task_id>.xlsx` with one sheet per task variant.
4. The current active reviewed task set (20 geometry tasks + 4 icons tasks) passes distribution review under the active gates; tile review artifacts remain tracked separately.

## Next priorities
1. Extend icons beyond counting/transformation using the new curated Prism asset pipeline (relation/comparison are the next natural families).
2. Introduce cross-domain `scene_variant` and role-binding schema in architecture docs/contracts.
3. Add future polygon variants as deferred tasks (diameter, min-side, max-side) after current scope stabilizes.

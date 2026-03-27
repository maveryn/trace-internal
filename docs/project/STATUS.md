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
8. Repo docs are now organized into `docs/core`, `docs/workflows`, `docs/domains`, `docs/project`, and `docs/tasks`, with repo-local workflow/domain skills under `skills/` acting as thin execution overlays on top of those source-of-truth docs.
9. Shared geometry single-object scene helpers (`graph_paper`, `graph_rendering`, `single_object_scene`, `angle_geometry`, `polygon_geometry`).
10. Objective-style geometry measurement tasks (single shape/object per image):
   - angle measure (primitive-angle or line-intersection source) with deterministic balanced source/answer sampling defaults, minimum ray length constraints, axis-aligned-ray construction, and nearest-integer degree query formatting,
   - area measure (triangle/quadrilateral + ellipse variants, with triangle/quadrilateral target-area sampling from exact feasible support),
   - perimeter measure (triangle/quadrilateral + circle variants, with triangle/circle target sampling from exact feasible support),
   - length measure (segment, polygon side, circle radius/diameter, ellipse major/minor axis variants),
   - slope measure (single finite line crossing x-axis at an integer lattice coordinate, with nearest-tenth numeric answers and x-axis crossing-point evidence).
   - angle measure ground-truth answers are nearest-integer degree values with raw-angle tolerance bounded by `0.05°`.
11. Geometry graph-paper backgrounds now render center-origin cues by default: axis arrows + signed integer scale labels across the full visible axis range (no origin text label).
12. Geometry graph-paper colors now vary within configured ranges per instance; axis lines are sampled darker than minor/major grid lines by construction.
13. Geometry shape ink style is now sampled from shared domain-config color ranges with Lab-distance constraints from background anchor colors; area/perimeter tasks reuse one shared task-group shape pipeline.
14. Geometry area/perimeter conic answers use `pi_expression` answer type (`kπ`) with coordinate-only graph-point evidence (`graph_point`).
15. Active prompt bundles now use explicit JSON output contracts in both modes (`answer_only` + `answer_and_evidence`) across geometry, icons, and tile tasks, with exactly 5 high-quality variants per required composition layer.
16. Geometry analytical_2d area task supports one explicit + one derived variant per shape family (rectangle, triangle, parallelogram, trapezoid, rhombus, circle, ellipse), uses vertex/endpoint labels plus numeric measurement text on the figure, and emits structured `measurement_ref_map` evidence (`annotation -> value`) on non-graph-paper solid backgrounds.
17. Geometry analytical_3d volume task supports six annotated-solid variants (rectangular prism, triangular prism, square pyramid, cylinder, cone, sphere) with deterministic balanced variant sampling and typed integer/`kπ` answers.
18. Geometry analytical_3d surface-area task supports the same six annotated solids with total-surface-area questions, integer/`kπ` answer types, and structured `measurement_ref_map` evidence.
19. Analytical 2D shape-unit scaling is now decoupled from graph-paper `graph_cells` limits via dedicated render params (`analytical_unit_spacing_px`, `analytical_unit_padding_px`, `analytical_scene_fill_ratio`).
20. Geometry measurement area/perimeter tasks now use unlabeled coordinate-only evidence (`graph_point_set` for polygons, `graph_point` for ellipse/circle) and keep shape vertices/reference points strictly inside the plotted graph-paper interior.
21. Geometry analytical_2d length task supports six derived annotated-scene variants (triangle altitude, rectangle diagonal, rhombus diagonals, isosceles trapezoid height, inscribed square, circle chord) with decimal answers rounded to one decimal place and structured `measurement_ref_map` evidence.
22. Analytical 2D length rendering now reserves explicit scene margin and uses local collision-aware text placement so labels/value annotations stay off geometry and away from the canvas edge more reliably.
23. Tile tasks now keep concrete task modules flat under `trace/tasks/tile/<task_group>_<task_name>.py` and route shared helpers/noise-default loading through `trace/tasks/tile/shared/` instead of per-task-group wrapper packages.
24. Tile count now includes `task_tile_count_color_count`, `task_tile_count_color_components`, and `task_tile_count_largest_component_size`, single-board `rectangular_tiling` tasks with dynamic canvas sizing, left/top coordinate gutters, coordinate-grounded `grid_point_set` evidence, shared rectangular-board count-family helpers, a reusable per-color component catalog, target-answer-balanced component-count queries, and unique-largest-component evidence for extremum-style component questions.
25. Tile shared 4-neighbor graph helpers now live under `trace/tasks/tile/shared/grid_graph.py`, which is reused across pathfinding and color-component counting instead of staying under a path-specific module name.
26. Tile reachability now includes `task_tile_reachability_region_size`, a single-board rectangular blocked-grid task with one start tile sampled from the shared 10-color named palette, black obstacle tiles, row/column coordinate gutters, coordinate-grounded reachable-set evidence, and a default reachable-answer cap of `12`.
27. Shared rectangular tile-board defaults now cap board sides at `7` instead of `8`; example/strict-repro configs plus `task_tile_path_shortest_path` are aligned to that ceiling, and shortest-path generation now samples exact target path lengths while emitting `grid_point_path` tile-coordinate evidence on the same labeled square-cell board contract as the other tile tasks.
28. Tile symmetry now includes `task_tile_symmetry_violation_count`, a single-board rectangular named-color task with deterministic `vertical` / `horizontal` variants, exact target-count construction over a uniform `1..10` violation range, and counted-side `grid_point_set` evidence.
29. Tile pattern now includes `task_tile_pattern_match3_run_count`, a single-board rectangular named-color task with deterministic `rows` / `cols` variants, exact target-count construction over qualifying-line counts, fixed run length `3`, query-color prompts with hex labels, and one canonical witness run per counted line.
30. Tile transition now includes `task_tile_transition_gravity_max_drop`, a single-board rectangular state-transition task with one colored tile per column, black bottom-contiguous obstacles, uniformly sampled target max-drop distances, a unique winning column by construction, and `grid_point_path` trajectory evidence for the winning drop.
31. Tile path now also includes `task_tile_path_reachable_target_count`, a square-cell blocked-grid task with one green start tile, multiple red marked targets, exact target-answer sampling over reachable-target counts `0..6`, and `grid_point_set` evidence for only the reachable targets.
32. Tile relation now also includes `task_tile_relation_min_distance`, a white-background rectangular-board task with exactly two connected colored regions, uniform target-answer sampling over minimum orthogonal distances `2..6`, and a unique straight `grid_point_path` witness between the unique closest pair.
33. Geometry analytical_2d perimeter task supports five derived annotated-scene variants (right triangle, rectangle, rhombus, isosceles trapezoid, inscribed square) with decimal answers rounded to one decimal place and structured `measurement_ref_map` evidence.
34. Geometry analytical_2d composite-area task supports five shaded/composite polygon variants (inner-rectangle cutout, triangle cutout, rectangle+triangle union, L-shape cutout, step-rectangle union) with integer answers and structured `measurement_ref_map` evidence.
35. Shared analytical 2D scene rendering now supports reusable polygon fill semantics (`shaded`, `background`) so composite/shaded objectives can reuse one collision-aware render stack instead of task-local draw overlays.
36. Geometry comparison now includes `task_geometry_comparison_angle`, `task_geometry_comparison_length`, `task_geometry_comparison_area`, and `task_geometry_comparison_perimeter`, each with 4–6 labeled graph-paper objects, `largest`/`smallest` winner queries, `option_letter` answers, and winner-evidence graph-point sets.
37. Geometry counting now includes `task_geometry_counting_angle`, `task_geometry_counting_triangle`, `task_geometry_counting_quadrilateral`, `task_geometry_counting_shape_type`, and `task_geometry_counting_convexity`, all non-graph-paper multi-object scenes with integer answers and sorted `label_set` evidence; angle scenes count acute/right/obtuse classes, triangle scenes count equilateral / isosceles-but-not-equilateral / scalene / right / acute / obtuse classes, quadrilateral scenes count square / rectangle-but-not-square / rhombus-but-not-square / parallelogram-only classes, mixed-shape scenes count triangle / quadrilateral / pentagon / hexagon / circle / ellipse instances, and convexity scenes count convex vs concave polygons using strict shared polygon classification.
38. Icons counting now includes `task_icons_counting_type`, `task_icons_counting_orientation`, `task_icons_counting_color`, `task_icons_counting_attribute_binding`, and `task_icons_counting_size_relation`, all using integer answers and scene-only `bbox_set` evidence in final image coordinates. Type counting matches icon identity against the curated 3000-icon Prism pool, orientation counting uses the curated asymmetric subset and same-icon scenes with rotation-based orientation queries, color counting uses same-icon scenes so tint is the only varying predicate (with a stricter Lab-distance threshold `60`), attribute-binding counting binds icon type + color + orientation together using structured partial-match distractors from the asymmetric pool, and size-relation counting uses same-icon scenes with randomized tint/rotation plus a Prism-style nominal-size gap so the only matching predicate is whether a scene icon is smaller or larger than the reference. The first four counting tasks use the shared two-panel `Reference` + `Scene` layout and sample `target_count` independently in `0..10` with `distractor_count` independently in `1..10`; the size-relation task uses tighter `0..8` / `1..8` count caps to keep larger-icon scenes readable. All five place icons randomly in the scene panel with at most `10%` pairwise overlap (normalized by the smaller box area) and apply per-icon subtle noise before compositing; the sampled palette, overlap/noise config, final tints, nominal sizes, and per-instance noise edits are recorded in trace metadata.
39. Icons transformation now includes `task_icons_transformation_pair_count`, a two-panel `Reference` + labeled `Scene` grid task with integer answers and sorted `label_set` evidence; the Reference pair shows one canonical D4 transform, Scene cells each show `icon -> transformed icon`, and the task counts how many cells apply the same rule. The task uses the curated asymmetric icon pool, rejects icon/transform pairs that collapse visually under rendered-silhouette checks, and records the sampled transform ids plus per-icon subtle noise in trace metadata.
40. Icons relation now includes `task_icons_relation_relative_position_type`, a two-panel `Reference` + `Scene` task with one marked Anchor icon, integer answers, and scene-only `bbox_set` evidence; query variants ask for matches left/right/above/below the Anchor, target counts are capped at `5`, distractors are capped at `10` with a target-conditioned floor of `target_count + 1`, spatial membership is evaluated strictly from rendered candidate/Anchor bboxes, and distractors are mixed across same-type wrong-side and different-type queried-side cases so the task requires both icon-type matching and directional reasoning instead of letting side occupancy become a cue. Same-type wrong-side distractors now follow Prism-style relaxed spatial margins, requiring at least `75%` of the distractor bbox area to lie outside the queried region so near-miss positives are rejected.
41. Icons relation also includes `task_icons_relation_occlusion_order`, a two-panel `Reference` + labeled `Scene` grid task with integer answers and sorted `label_set` evidence; the Reference cell and every Scene cell contain the same icon pair with varying colors, overlap amounts, and subtle per-icon noise, while only the front-to-back order (`a_over_b` vs `b_over_a`) determines whether a Scene cell matches. The task uses the curated 3000-icon Prism pool, keeps each overlapping icon pair Lab-separated by at least `80`, samples overlap ratios in `0.40..0.60`, and balances counts over `target_count in 0..6`, `distractor_count in 1..6`.
42. Icons sequence now includes `task_icons_sequence_missing_count`, a single-panel horizontal sequence-row task with integer answers and one-box `bbox_set` evidence for the missing Scene cell. Every visible Scene cell contains randomly placed icons of one shared type and tint, orientation may vary per instance, and the number of icons in each cell follows one arithmetic progression with a hidden count sampled from `0..10`. The missing cell may appear anywhere in the row, including either end, visible icons stay in the smaller `24..40` px band, each instance samples its own row box width/height and derives the final canvas from that geometry, and any pairwise overlap inside one cell is capped at `20%` of the smaller icon box area.

## Active tasks
1. `task_tile_count_color_count` (`domain=tile`, `task_group=count`)
2. `task_tile_count_color_components` (`domain=tile`, `task_group=count`)
3. `task_tile_count_largest_component_size` (`domain=tile`, `task_group=count`)
4. `task_tile_path_shortest_path` (`domain=tile`, `task_group=path`)
5. `task_tile_path_reachable_target_count` (`domain=tile`, `task_group=path`)
6. `task_tile_pattern_match3_run_count` (`domain=tile`, `task_group=pattern`)
7. `task_tile_reachability_region_size` (`domain=tile`, `task_group=reachability`)
8. `task_tile_relation_min_distance` (`domain=tile`, `task_group=relation`)
9. `task_tile_symmetry_violation_count` (`domain=tile`, `task_group=symmetry`)
10. `task_tile_transition_gravity_max_drop` (`domain=tile`, `task_group=transition`)
11. `task_geometry_comparison_angle` (`domain=geometry`, `task_group=comparison`)
12. `task_geometry_comparison_area` (`domain=geometry`, `task_group=comparison`)
13. `task_geometry_comparison_length` (`domain=geometry`, `task_group=comparison`)
14. `task_geometry_comparison_perimeter` (`domain=geometry`, `task_group=comparison`)
15. `task_geometry_counting_angle` (`domain=geometry`, `task_group=counting`)
16. `task_geometry_counting_triangle` (`domain=geometry`, `task_group=counting`)
17. `task_geometry_counting_quadrilateral` (`domain=geometry`, `task_group=counting`)
18. `task_geometry_counting_shape_type` (`domain=geometry`, `task_group=counting`)
19. `task_geometry_counting_convexity` (`domain=geometry`, `task_group=counting`)
20. `task_geometry_measurement_angle` (`domain=geometry`, `task_group=measurement`)
21. `task_geometry_measurement_area` (`domain=geometry`, `task_group=measurement`)
22. `task_geometry_measurement_perimeter` (`domain=geometry`, `task_group=measurement`)
23. `task_geometry_measurement_length` (`domain=geometry`, `task_group=measurement`)
24. `task_geometry_measurement_slope` (`domain=geometry`, `task_group=measurement`)
25. `task_geometry_analytical_2d_area` (`domain=geometry`, `task_group=analytical_2d`)
26. `task_geometry_analytical_2d_length` (`domain=geometry`, `task_group=analytical_2d`)
27. `task_geometry_analytical_2d_perimeter` (`domain=geometry`, `task_group=analytical_2d`)
28. `task_geometry_analytical_2d_composite_area` (`domain=geometry`, `task_group=analytical_2d`)
29. `task_geometry_analytical_3d_volume` (`domain=geometry`, `task_group=analytical_3d`)
30. `task_geometry_analytical_3d_surface_area` (`domain=geometry`, `task_group=analytical_3d`)
31. `task_icons_counting_type` (`domain=icons`, `task_group=counting`)
32. `task_icons_counting_orientation` (`domain=icons`, `task_group=counting`)
33. `task_icons_counting_color` (`domain=icons`, `task_group=counting`)
34. `task_icons_counting_attribute_binding` (`domain=icons`, `task_group=counting`)
35. `task_icons_counting_size_relation` (`domain=icons`, `task_group=counting`)
36. `task_icons_relation_relative_position_type` (`domain=icons`, `task_group=relation`)
37. `task_icons_relation_occlusion_order` (`domain=icons`, `task_group=relation`)
38. `task_icons_sequence_missing_count` (`domain=icons`, `task_group=sequence`)
39. `task_icons_transformation_pair_count` (`domain=icons`, `task_group=transformation`)

## Current quality baseline
1. Tests are required to pass before finalize.
2. Distribution QA uses `scripts/check_task_answer_distribution.py` with per-variant answer-only checks (`unique_answers >= 5`, `max_answer_frequency < 25%`) and multithreaded sample generation (`--workers`); numeric 5-bin summaries remain reported for review but are not hard pass/fail gates.
3. Task-review tooling writes per-task artifacts under `task-reviews/<task_id>/`, including one inspection workbook named `<task_id>.xlsx` with one sheet per task variant.
4. The current active reviewed task set (10 tile tasks + 20 geometry tasks + 9 reviewed icons tasks) passes distribution review under the active gates.

## Next priorities
1. Extend icons beyond the current counting/transformation/relation/sequence set using the curated Prism asset pipeline (`comparison` and richer relation/transformation variants are the next natural families).
2. Introduce cross-domain `scene_variant` and role-binding schema in architecture docs/contracts.
3. Add future polygon variants as deferred tasks (diameter, min-side, max-side) after current scope stabilizes.

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
38. Icons counting now includes `task_icons_counting_type`, `task_icons_counting_orientation`, and `task_icons_counting_color`, all using a two-panel `Reference` + `Scene` image, integer answers, and scene-only `bbox_set` evidence in final image coordinates; type counting matches icon identity against the curated 3000-icon Prism pool, orientation counting uses the curated asymmetric subset and same-icon scenes with rotation-based orientation queries, and color counting uses same-icon scenes so the only varying predicate is tint, with a stricter Lab-distance threshold (`60`). These tasks sample `target_count` independently in `0..10` and `distractor_count` independently in `1..10`, place icons randomly in the scene panel with at most `10%` pairwise overlap (normalized by the smaller box area), and apply per-icon subtle noise before compositing; the sampled palette, overlap/noise config, final tints, and per-instance noise edits are recorded in trace metadata.
39. Icons transformation now includes `task_icons_transformation_pair_count`, a two-panel `Reference` + labeled `Scene` grid task with integer answers and sorted `label_set` evidence; the Reference pair shows one canonical D4 transform, Scene cells each show `icon -> transformed icon`, and the task counts how many cells apply the same rule. The task uses the curated asymmetric icon pool, rejects icon/transform pairs that collapse visually under rendered-silhouette checks, and records the sampled transform ids plus per-icon subtle noise in trace metadata.
40. Charts now includes `task_charts_statistics_summary_value`, the first `statistics` family task under `domain=charts`, with semantic `task_variant` values `max|min|range|mean|median|sum|mode`, visual `scene_variant` values `area|bar|horizontal_bar|line|scatter|dot_plot|lollipop`, integer answers, `label_set` evidence over the supporting labeled marks, randomized uppercase mark labels, and one per-instance chart color sampled randomly with a Lab-distance floor from the white/light chart background.
41. Charts also includes `task_charts_statistics_summary_label`, a companion `statistics` task that reuses the axis-based chart scene variants plus composition-style `pie|donut` scenes and the spoke-and-polygon `radar` scene, asks for the winning mark label on `argmax|argmin|median_label` queries, uses `option_letter` answers and integer evidence carrying the winning statistic value, renders pie/donut as multicolor percentage charts with a right-side legend, and renders radar with one spoke per label plus printed point values near the markers.
42. Charts now also includes `task_charts_counting_value_count`, the first `counting` family task under `domain=charts`, with semantic `task_variant` values `above_threshold|below_threshold|in_interval`, visual `scene_variant` values `area|bar|pie|donut|horizontal_bar|line|radar|scatter|dot_plot|lollipop`, integer answers, sorted `label_set` evidence over the matching marks, and target-balanced count sampling over the default answer support `0..10`; pie/donut scenes use positive integer percentages that sum to `100`, distinct slice colors, and a right-side legend, while radar scenes use one spoke per label and printed point values near the markers.
43. Shared deterministic variant-selection helpers now live in `trace/tasks/shared/variant_sampling.py`; geometry imports were updated to use the cross-domain helper, and charts reuse its namespaced balanced-cycling path for separate semantic and scene axes.
44. Charts now also includes `task_charts_readout_subset_value`, the first `readout` family task under `domain=charts`, with semantic `task_variant` values `sum_two|difference_two_abs|max_two|min_two|mean_two`, visual `scene_variant` values `area|bar|pie|donut|horizontal_bar|line|radar|scatter|dot_plot|lollipop`, integer answers, and ordered `integer_list` evidence carrying the two queried values in the same label order used in the prompt; pie/donut scenes again use positive integer percentages that sum to `100`, distinct slice colors, and a right-side legend, while radar scenes use one spoke per label and printed point values near the markers.
45. Charts now also includes `task_charts_multiseries_pairwise_comparison_count`, the first `multiseries` family task under `domain=charts`, with semantic `task_variant` values `series_a_gt_b_count|series_a_lt_b_count`, visual `scene_variant` values `grouped_bar|multi_line|grouped_lollipop`, integer answers, sorted category-label `label_set` evidence, `2..3` series per chart, `5..10` labeled categories per chart, and target-balanced count sampling over the default answer support `0..8`; the queried pair of series is named in the prompt while an optional third series acts as a distractor, and right-side legends map series colors to series names.

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
34. `task_icons_transformation_pair_count` (`domain=icons`, `task_group=transformation`)
35. `task_charts_statistics_summary_value` (`domain=charts`, `task_group=statistics`)
36. `task_charts_statistics_summary_label` (`domain=charts`, `task_group=statistics`)
37. `task_charts_counting_value_count` (`domain=charts`, `task_group=counting`)
38. `task_charts_readout_subset_value` (`domain=charts`, `task_group=readout`)
39. `task_charts_multiseries_pairwise_comparison_count` (`domain=charts`, `task_group=multiseries`)

## Current quality baseline
1. Tests are required to pass before finalize.
2. Distribution QA uses `scripts/check_task_answer_distribution.py` with per-variant answer-only checks (`unique_answers >= 5`, `max_answer_frequency < 25%`) and multithreaded sample generation (`--workers`); numeric 5-bin summaries remain reported for review but are not hard pass/fail gates.
3. Task-review tooling writes per-task artifacts under `task-reviews/<task_id>/`, including one inspection workbook named `<task_id>.xlsx` with one sheet per task variant.
4. The current active reviewed task set (10 tile tasks + 20 geometry tasks + 4 icons tasks + 5 charts tasks) passes distribution review under the active gates.

## Next priorities
1. Extend icons beyond counting/transformation using the new curated Prism asset pipeline (relation/comparison are the next natural families).
2. Introduce cross-domain `scene_variant` and role-binding schema in architecture docs/contracts.
3. Add future polygon variants as deferred tasks (diameter, min-side, max-side) after current scope stabilizes.

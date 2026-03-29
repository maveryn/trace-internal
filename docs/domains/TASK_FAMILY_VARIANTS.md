# Task Families & Variants

## Purpose
Define how we split tasks into reusable families so each dataset slice stays comparable and avoids hidden weighting bias.

## Core rule
1. **Family = reasoning mode** (for example `measurement`, `comparison`).
2. **Variant = visual/semantic subtype inside a family** (for example polygon `n`-gon subtype, query subtype).
3. Keep family boundaries stable; add variants before adding new families unless reasoning mode changes.

## Geometry direction (current)
1. `measurement` should use **one primary object per image**.
2. Multi-object value-query geometry tasks belong under `comparison` (separate from single-object `measurement`).
3. Multi-object geometry class-membership tasks belong under `counting`; scenes should label whole objects and count how many match one requested class.
4. `analytical_2d` should use one primary annotated scene where area/length/perimeter must be inferred from symbolic/numeric relationships (not direct readout); auxiliary constructions or coupled shapes are acceptable when they are part of the derivation.
5. `comparison` should enforce exactly one winner by construction and use one reusable winner-gap policy (`gap_norm >= 0.20` plus optional task-level absolute floors) so scenes stay readable without hand-tuned per-instance ambiguity checks.

## Icons direction (current)
1. `counting` should use a reference panel plus a scene panel rather than raw icon-name prompts.
2. Reference-scene icon counting tasks should answer with an integer count and use scene-only `bbox_set` evidence in final image coordinates.
3. Orientation-sensitive icon tasks should use the curated asymmetric Prism subset (`non_symmetry.txt`) so rotated matches remain visually meaningful.
4. Prism-style icon counting should sample `target_count` and `distractor_count` from explicit supports, derive `object_count` from the pair, place icons randomly under an explicit overlap cap, and keep per-icon noise on the individual icon instances rather than as a full-image post-process.
5. Icons relation tasks should keep one visibly marked `Anchor` icon in the Scene panel, use a smaller spatial count range than global counting, and ground matches with scene-only `bbox_set` evidence.

## Planned tile direction
1. Tile tasks should use one board per image and keep prompts grounded in board coordinates rather than raw pixel positions.
2. V1 tile scene geometry uses `rectangular_tiling`; square tiles are one sampled aspect-ratio case, not a separate tiling family.
3. Canonical tile coordinates are zero-based `(row, col)` with top-left origin.
4. New tile tasks should prefer coordinate-grounded evidence (`grid_point_set`, `grid_point_path`) and keep pixel overlays as derived trace projections.
5. See `TILE_TASK_SETUP.md` for the concrete board-geometry, metadata, and evidence contract.
6. Reachability-style tile tasks should treat black obstacle tiles and marked start tiles as semantic board roles, not as generic query colors.

## Charts direction (current)
1. Charts follow the same split as geometry: `task_group` encodes reasoning family, while chart type is treated as `scene_variant` inside the task.
2. Active chart families are `statistics`, `counting`, `readout`, `multiseries`, `distribution`, `composition`, and `trend`.
3. `task_charts_statistics_summary_value` uses semantic `task_variant` values `max`, `min`, `range`, `mean`, `median`, `sum`, and `mode`.
4. `task_charts_statistics_summary_label` uses semantic `task_variant` values `argmax`, `argmin`, and `median_label`.
5. `task_charts_counting_value_count` uses semantic `task_variant` values `above_threshold`, `below_threshold`, and `in_interval`.
6. `task_charts_readout_subset_value` uses semantic `task_variant` values `sum_two`, `difference_two_abs`, `max_two`, `min_two`, and `mean_two`.
7. `task_charts_multiseries_pairwise_comparison_count` uses semantic `task_variant` values `series_a_gt_b_count` and `series_a_lt_b_count`.
8. `task_charts_distribution_histogram_count` uses semantic `task_variant` values `modal_bin_count`, `interval_mass`, and `cumulative_count_to_bin`.
9. `task_charts_distribution_boxplot_label` uses semantic `task_variant` values `highest_median`, `largest_iqr`, and `smallest_iqr`.
10. `task_charts_distribution_density_label` uses semantic `task_variant` values `highest_mode`, `lowest_mode`, and `bimodal_label`.
11. `task_charts_composition_subset_value` uses semantic `task_variant` values `stack_total_at_label`, `stack_segment_value`, and `combined_share_subset`.
12. `task_charts_trend_structure_value` uses semantic `task_variant` values `peak_count`, `trough_count`, `longest_increasing_streak`, and `longest_decreasing_streak`.
13. Single-series chart tasks use `scene_variant` values `area`, `bar`, `horizontal_bar`, `line`, `scatter`, `dot_plot`, and `lollipop`.
14. `task_charts_statistics_summary_label`, `task_charts_counting_value_count`, and `task_charts_readout_subset_value` additionally support `pie` and `donut` as composition-style scene variants with percentage slices and a right-side legend.
15. Those same three chart tasks also support `radar` as a spoke-and-polygon scene variant with printed point values near the radar markers.
16. `task_charts_composition_subset_value` supports `stacked_bar`, `stacked_horizontal_bar`, `pie`, and `donut`, with compatibility constrained by variant (`stack_total_at_label|stack_segment_value` on stacked scenes, `combined_share_subset` on pie/donut scenes).
17. `task_charts_trend_structure_value` currently supports the ordered single-series scene variants `area`, `bar`, `horizontal_bar`, `line`, `dot_plot`, and `lollipop`.
18. `task_charts_multiseries_pairwise_comparison_count` supports `grouped_bar`, `grouped_horizontal_bar`, `multi_line`, and `grouped_lollipop`.
19. Distribution chart tasks currently use fixed scene contracts:
   - `task_charts_distribution_histogram_count` -> `histogram`
   - `task_charts_distribution_boxplot_label` -> `boxplot`
   - `task_charts_distribution_density_label` -> `violin`
20. Keep the broader chart-type universe in `CHART_DOMAIN_PLAN.md` and the concrete active contract in `CHART_TASK_SETUP.md`; histogram is only valid as an active chart type when it preserves true numeric-bin semantics distinct from `bar`.

## Tables direction (current)
1. Tables follow the same split as charts: `task_group` encodes reasoning family, while table styling is treated as `scene_variant` inside the task.
2. The active table families are `statistics`, `counting`, `readout`, `relation`, `ranking`, and `temporal`.
3. `task_tables_statistics_summary_label` uses semantic `task_variant` values `argmax`, `argmin`, `row_sum_argmax`, and `row_sum_argmin`.
4. `task_tables_statistics_summary_value` uses semantic `task_variant` values `column_sum`, `column_mean`, `column_median`, `row_sum`, `row_mean`, `table_sum`, and `table_mean`.
5. `task_tables_statistics_filtered_subset_value` uses semantic `task_variant` values `filtered_column_sum` and `filtered_column_mean`, while an internal filter subtype chooses `above_threshold|below_threshold|in_interval`.
6. `task_tables_statistics_filtered_subset_label` uses semantic `task_variant` values `filtered_argmax` and `filtered_argmin`, while an internal filter subtype chooses `above_threshold|below_threshold|in_interval`.
7. `task_tables_counting_value_count` uses semantic `task_variant` values `above_threshold`, `below_threshold`, `in_interval`, `col_a_gt_col_b`, and `col_a_lt_col_b`.
8. `task_tables_readout_subset_value` uses semantic `task_variant` values `cell_lookup`, `cell_sum_two`, and `cell_difference_two_abs`.
9. `task_tables_relation_row_compare_label` uses semantic `task_variant` values `higher_of_two_rows` and `lower_of_two_rows`.
10. `task_tables_relation_extremum_transfer_value` uses semantic `task_variant` values `argmax_transfer` and `argmin_transfer`.
11. `task_tables_ranking_label` uses semantic `task_variant` values `kth_highest_in_column` and `kth_lowest_in_column`, with an internal queried rank `k` currently sampled from `2..4`.
12. `task_tables_temporal_value` uses semantic `task_variant` values `value_at_year`, `delta_between_years`, `absolute_difference_between_years`, `sum_over_year_interval`, and `mean_over_year_interval`.
13. All active table tasks use `scene_variant` values `spreadsheet`, `zebra`, `ledger`, and `card_table`.
14. Table row labels should use short visible human-style names rather than single letters when the answer is a row identity.
15. Table tasks use one fixed prompt-facing evidence type in v1: `bbox_set`.
16. Evidence boxes should mark the minimal supporting table region(s): one decisive numeric cell bbox or one winning-row region bbox for `task_tables_statistics_summary_label`, one queried-column region bbox, queried-row region bbox, or full numeric-table region bbox for `task_tables_statistics_summary_value`, one ordered set of filter/target value-cell pairs for `task_tables_statistics_filtered_subset_value`, one ordered set of filter/target value-cell pairs for `task_tables_statistics_filtered_subset_label`, one ordered set of matching value-cell bboxes or compared two-column value-cell pairs for `task_tables_counting_value_count`, one queried value-cell bbox or ordered queried-cell pair for `task_tables_readout_subset_value`, one ordered pair of compared queried-column value-cell bboxes for `task_tables_relation_row_compare_label`, one ordered pair `[source extremum cell, target value cell]` for `task_tables_relation_extremum_transfer_value`, one queried-column region bbox for `task_tables_ranking_label`, and one ordered set of queried year-cell bboxes for `task_tables_temporal_value`.

## Graph direction (current)
1. Graph tasks use one simple node-link graph per image in v1; keep graphs unweighted by default, and make directionality or edge weights explicit only when the task semantics truly require them.
2. `task_group` should encode the reasoning family (for example `counting`, `relation`, `path`), while graph layout stays a visual `scene_variant` or trace-only sampling axis inside a task.
3. Node labels are the canonical prompt-facing identities; prefer `label_set` evidence when the witness unit is one or more nodes.
4. Layout variation should change readability only, not semantics; graph answers must come from adjacency/topology rather than absolute node position.
5. Keep graph sampling variation split between topology families and layout families so graph semantics remain stable while scenes still vary visually.
6. If a graph task supports directed variants, make the prompt wording, trace metadata, and rendered arrowheads explicit; do not reuse plain `degree` wording for directed in-/out-degree queries.

## Puzzles direction (current)
1. Puzzles use `task_group` for hidden-rule reasoning families such as `arithmetic`, `logic`, `spatial`, and `topology`; avoid splitting families by one-off visual templates when the reasoning contract is still the same.
2. Early arithmetic puzzle tasks should favor explicit unknown slots so evidence can stay local and visually obvious.
3. `task_puzzles_arithmetic_equation_value` uses semantic `task_variant` values `result_unknown` and `operand_unknown`.
4. `task_puzzles_arithmetic_equation_value` uses visual `scene_variant` values `equation_strip`, `equation_card`, and `equation_outline`.
5. `task_puzzles_arithmetic_balance_value` uses semantic `task_variant` values `sum_pair_unknown`, `two_panel_chain_unknown`, and `three_panel_chain_unknown`.
6. `task_puzzles_arithmetic_balance_value` uses visual `scene_variant` values `balance_strip`, `balance_card`, and `balance_outline`.
7. The active equation-scene grammar uses one flat equation row with `2..5` left-side operand boxes, operators sampled from `+`, `-`, and `×`, one right-side result box, and the `?` randomly placed on either side according to `task_variant`.
8. The active balance-scene grammar uses `2..3` stacked balance panels with boxed symbols and numbers plus one highlighted query box below the panels.
9. Prompt-facing arithmetic evidence should stay as one-box `bbox_set` grounding on the queried unknown slot or highlighted query box; do not widen to explanatory multi-box evidence unless a later family truly needs ordered witnesses.

## Temporal direction (current)
1. Temporal tasks should group by visual time artifact (`clock`, `calendar`, `schedule`, `timeline`) rather than by one exact question stem.
2. The current active temporal families are `clock`, `calendar`, and `schedule`.
3. `task_temporal_clock_readout` uses semantic `task_variant` values `shown_time`, `minutes_after`, and `minutes_before`.
4. `task_temporal_clock_compare` uses semantic `task_variant` values `earliest_time` and `latest_time`.
5. `task_temporal_calendar_month_view` uses semantic `task_variant` values `date_of_weekday_occurrence`, `count_marked_weekend_days`, and `days_between_marked_dates`.
6. `task_temporal_schedule_day_planner` uses semantic `task_variant` values `overlap_count`, `longer_than_reference_count`, and `maximum_non_overlapping_count`.
7. The active temporal tasks use visual `scene_variant` values `classic`, `minimal`, and `outline`.
8. The active temporal tasks use non-semantic visual axes `style_variant=studio|accented|marker` and `accent_color_name` from the shared named-color palette; these axes should change styling only, never the prompt contract.
9. `task_temporal_clock_readout` uses two-hand `bbox_set` evidence over the hour and minute hands, `task_temporal_clock_compare` uses a one-box `bbox_set` over the winning clock face, `task_temporal_calendar_month_view` uses date-cell `bbox_set` evidence over the relevant day cells, and `task_temporal_schedule_day_planner` uses event-block `bbox_set` evidence over the relevant schedule blocks.
10. Early temporal tasks should prefer local prompt-facing evidence on the queried artifact itself (for example hand bboxes, winning clock faces, date-cell bboxes, or event blocks) instead of wide scene evidence.
11. For temporal offset variants, keep the displayed scene fixed and let the prompt carry the offset; prompt JSON examples must match the active offset semantics rather than reusing the direct-readout example answer.
12. For month-view calendar tasks, keep the visual scaffold fixed to one month grid and widen question diversity through `task_variant`; do not fork separate calendar task ids for nth-weekday lookup vs marked-date counting when the same date-cell evidence contract already covers them.
13. For single-day schedule tasks, keep one stable planner scaffold and widen question diversity through `task_variant`; if a schedule variant answers with a selected event subset, enforce that witness subset’s uniqueness by construction before exposing it as prompt-facing evidence.

## Planned geometry measurement variants
1. **Angle measurement**
   - One angle per image.
   - Ask for the angle value rounded to the nearest integer degree.
   - Evidence: unlabeled 3-point set in graph-unit integer coordinates.
2. **Polygon area measurement**
   - One shape per image: triangle/quadrilateral polygon or ellipse.
   - Ask for area (`integer` for polygons, `kπ` for ellipses).
   - Evidence: polygon/circle-specific graph-point evidence in graph-unit coordinates.
3. **Polygon perimeter measurement**
   - One shape per image: triangle/quadrilateral polygon or circle.
   - Ask for perimeter/circumference (`integer` for polygons, `kπ` for circles).
   - Evidence: polygon/circle-specific graph-point evidence in graph-unit coordinates.
4. **Slope measurement**
   - One finite line per image on graph paper.
   - Line crosses x-axis at an integer lattice coordinate and at least one other integer lattice point.
   - Ask for slope to one decimal place.
   - Evidence: one x-axis crossing lattice point.

## Implemented analytical variant
1. **Comparison angle (`task_geometry_comparison_angle`)**
   - One graph-paper image with 4–6 labeled angles.
   - Query type: `largest` or `smallest`.
   - Answer type: winner label (`option_letter`) with no textual option list in the prompt.
   - Evidence: `graph_point_set` for the winning angle's vertex + two ray endpoints.
2. **Comparison area (`task_geometry_comparison_area`)**
   - One graph-paper image with 4–6 labeled rectangles.
   - Query type: `largest` or `smallest`.
   - Answer type: winner label (`option_letter`) with no textual option list in the prompt.
   - Evidence: `graph_point_set` for the winning rectangle vertices.
3. **Comparison length (`task_geometry_comparison_length`)**
   - One graph-paper image with 4–6 labeled line segments.
   - Query type: `largest` or `smallest`.
   - Answer type: winner label (`option_letter`) with no textual option list in the prompt.
   - Evidence: `graph_point_set` for the winning segment endpoints.
4. **Comparison perimeter (`task_geometry_comparison_perimeter`)**
   - One graph-paper image with 4–6 labeled rectangles.
   - Query type: `largest` or `smallest`.
   - Answer type: winner label (`option_letter`) with no textual option list in the prompt.
   - Evidence: `graph_point_set` for the winning rectangle vertices.
5. **Counting angle (`task_geometry_counting_angle`)**
   - One non-graph-paper image with 6–10 labeled angles.
   - Query variants: `acute_angle`, `right_angle`, `obtuse_angle`.
   - Answer type: integer count.
   - Evidence: sorted `label_set` of the matching angle labels.
6. **Counting triangle (`task_geometry_counting_triangle`)**
   - One non-graph-paper image with 5–8 labeled triangles.
   - Query variants: `equilateral_triangle`, `isosceles_triangle`, `scalene_triangle`, `right_triangle`, `acute_triangle`, `obtuse_triangle`.
   - Answer type: integer count.
   - Evidence: sorted `label_set` of the matching triangle labels.
   - Overlap wording: the isosceles query is phrased as `isosceles triangles but not equilateral triangles` so the task does not rely on competing textbook conventions.
7. **Counting quadrilateral (`task_geometry_counting_quadrilateral`)**
   - One non-graph-paper image with 5–7 labeled quadrilaterals.
   - Query variants: `square`, `rectangle_non_square`, `rhombus_non_square`, `parallelogram_only`.
   - Answer type: integer count.
   - Evidence: sorted `label_set` of the matching quadrilateral labels.
   - Overlap wording: rectangle/rhombus/parallelogram prompts use exclusive wording so squares are not double-counted by convention.
8. **Counting shape type (`task_geometry_counting_shape_type`)**
   - One non-graph-paper image with 6–9 labeled mixed shapes.
   - Query variants: `triangle`, `quadrilateral`, `pentagon`, `hexagon`, `circle`, `ellipse`.
   - Answer type: integer count.
   - Evidence: sorted `label_set` of the matching shape labels.
   - Visual distinction rule: ellipses must stay visibly non-circular so `circle` and `ellipse` do not collapse into one ambiguous class.
9. **Counting convexity (`task_geometry_counting_convexity`)**
   - One non-graph-paper image with 6–9 labeled polygons.
   - Query variants: `convex_polygon`, `concave_polygon`.
   - Polygon families: quadrilateral, pentagon, and hexagon.
   - Answer type: integer count.
   - Evidence: sorted `label_set` of the matching polygon labels.
   - Visual distinction rule: concave polygons must keep a clear reflex indentation; degenerate or borderline near-flat shapes are rejected instead of left to interpretation.
10. **Analytical area (`task_geometry_analytical_2d_area`)**
   - One annotated shape per image: rectangle, triangle, parallelogram, trapezoid, rhombus, circle, ellipse.
   - One explicit + one derived variant per shape.
   - Ask for area (`integer` for polygonal shapes, `kπ` for circle/ellipse).
   - Evidence: structured `measurement_ref_map` (`annotation -> value`) for all quantities used in the area computation.
11. **Analytical length (`task_geometry_analytical_2d_length`)**
   - One annotated analytical scene per image, including auxiliary constructions or coupled shapes.
   - Derived-only variants: triangle altitude side, rectangle diagonal side, rhombus diagonal side, isosceles trapezoid leg, inscribed square side, circle chord length.
   - Ask for a target segment length rounded to one decimal place.
   - Evidence: structured `measurement_ref_map` (`annotation -> value`) for the givens used in the derivation.
12. **Analytical perimeter (`task_geometry_analytical_2d_perimeter`)**
   - One annotated analytical scene per image, including auxiliary constructions or coupled shapes.
   - Derived-only variants: right triangle from leg+hypotenuse, rectangle from side+diagonal, rhombus from diagonals, isosceles trapezoid from bases+height, inscribed square from circle diameter.
   - Ask for the perimeter rounded to one decimal place.
   - Evidence: structured `measurement_ref_map` (`annotation -> value`) for the givens used in the derivation.
13. **Analytical composite area (`task_geometry_analytical_2d_composite_area`)**
   - One annotated analytical scene per image with one shaded target region; auxiliary cuts/unions and coupled polygons are allowed.
   - Derived-only variants: inner-rectangle cutout, triangle cutout, rectangle+triangle union, L-shape cutout, step-rectangle union.
   - Ask for the shaded/composite area as an integer number of square units.
   - Evidence: structured `measurement_ref_map` (`annotation -> value`) for the givens used in the derivation.
14. **Analytical 3D volume (`task_geometry_analytical_3d_volume`)**
   - One annotated 3D solid per image: rectangular prism, triangular prism, square pyramid, cylinder, cone, sphere.
   - Ask for volume (`integer` for polyhedra, `kπ` for cylinder/cone/sphere).
   - Evidence: structured `measurement_ref_map` (`annotation -> value`) for the required measurement labels.
15. **Analytical 3D surface area (`task_geometry_analytical_3d_surface_area`)**
   - One annotated 3D solid per image: rectangular prism, triangular prism, square pyramid, cylinder, cone, sphere.
   - Ask for total surface area (`integer` for polyhedra, `kπ` for cylinder/cone/sphere).
   - Evidence: structured `measurement_ref_map` (`annotation -> value`) for the required measurement labels.
16. **Icons counting type (`task_icons_counting_type`)**
   - One two-panel image with a `Reference` icon and a `Scene` panel of icons.
   - Query: how many scene icons have the same icon type as the reference.
   - Count support: `target_count` in `0..10`, `distractor_count` in `1..10`, total scene icons in `1..20`.
   - Answer type: integer count.
   - Evidence: scene-only `bbox_set` in final image coordinates.
17. **Icons counting orientation (`task_icons_counting_orientation`)**
   - One two-panel image with a `Reference` icon and a `Scene` panel of icons.
   - Query: how many scene icons have the same orientation as the reference icon.
   - Scene uses one shared icon type from the asymmetric curated pool; orientation is conveyed by rotation.
   - Count support: `target_count` in `0..10`, `distractor_count` in `1..10`, total scene icons in `1..20`.
   - Answer type: integer count.
   - Evidence: scene-only `bbox_set` in final image coordinates.
18. **Icons counting color (`task_icons_counting_color`)**
   - One two-panel image with a `Reference` icon and a `Scene` panel of icons.
   - Query: how many scene icons have the same color as the reference icon.
   - Scene keeps the same icon type as the reference throughout; color is the only matching predicate.
   - Count support: `target_count` in `0..10`, `distractor_count` in `1..10`, total scene icons in `1..20`.
   - Answer type: integer count.
   - Evidence: scene-only `bbox_set` in final image coordinates.
19. **Icons counting attribute binding (`task_icons_counting_attribute_binding`)**
   - One two-panel image with a `Reference` icon and a `Scene` panel of icons.
   - Query: how many scene icons match the reference exactly in icon type, color, and orientation.
   - Scene uses the asymmetric curated icon pool so orientation stays meaningful, and distractors are built mostly from structured `2-of-3` and `1-of-3` partial matches instead of easy all-wrong negatives.
   - Count support: `target_count` in `0..10`, `distractor_count` in `1..10`, total scene icons in `1..20`.
   - Answer type: integer count.
   - Evidence: scene-only `bbox_set` in final image coordinates.
20. **Icons counting size relation (`task_icons_counting_size_relation`)**
   - One two-panel image with a `Reference` icon and a `Scene` panel of icons.
   - Query variants: count scene icons that are `smaller` or `larger` than the reference icon.
   - Scene keeps the same icon type as the reference while randomizing tint and rotation; size is the only matching predicate.
   - Count support: `target_count` in `0..8`, `distractor_count` in `1..8`, total scene icons in `1..16`.
   - Size distinction rule: reference nominal size is sampled from `64..96` px, scene nominal sizes from `40..120` px, and every scene icon must satisfy `|scene_size-reference_size| >= 12` px so there are no same-size near misses.
   - Answer type: integer count.
   - Evidence: scene-only `bbox_set` in final image coordinates.
21. **Icons transformation pair count (`task_icons_transformation_pair_count`)**
   - One two-panel image with a `Reference` pair and a labeled `Scene` grid of icon pairs.
   - Query: how many Scene cells apply the same transformation as the Reference pair.
   - Transform vocabulary: `rot90`, `rot180`, `rot270`, `flip_h`, `flip_v`, `flip_diag_main`, `flip_diag_anti`.
   - Count support: `target_count` in `0..6`, `distractor_count` in `1..6`, total Scene cells in `2..12`.
   - Answer type: integer count.
   - Evidence: sorted `label_set` of the matching Scene cell labels.
   - Visual distinction rule: candidate icons are accepted only when the sampled transform and at least one distractor transform remain visually distinct from identity and from the reference transform.
22. **Icons relation relative-position type (`task_icons_relation_relative_position_type`)**
   - One two-panel image with a `Reference` icon on the left and a `Scene` panel of icons on the right; exactly one Scene icon is visibly marked as the `Anchor`.
   - Query variants: `left_of_anchor`, `right_of_anchor`, `above_anchor`, `below_anchor`.
   - Count support: `target_count` in `0..5`, `distractor_count` in `max(1, target_count + 1)..10`, with the Anchor excluded from the counted candidate set.
   - Answer type: integer count.
   - Evidence: scene-only `bbox_set` in final image coordinates.
   - Spatial distinction rule: evaluate left/right/above/below strictly from rendered bboxes, mix distractors across same-type wrong-side and different-type queried-side cases so the scene cannot be solved from one-sided occupancy alone, and require same-type wrong-side distractors to sit mostly outside the queried region (Prism-style relaxed margin rule).
23. **Icons relation between two anchors count (`task_icons_relation_between_two_anchors_count`)**
   - One single-panel image with free-placed Scene icons and two visibly marked anchors `A` and `B`.
   - Query variants: `inside_vertical_strip`, `inside_horizontal_strip`.
   - Count support: `target_count` in `0..5`, `distractor_count` in `1..10`, with the anchors excluded from the counted candidate set.
   - Answer type: integer count.
   - Evidence: scene-only `bbox_set` in final image coordinates.
   - Spatial distinction rule: anchors share the same icon type/tint/rotation and are exactly aligned on the non-varying axis, all candidates use a different icon type from the anchors, and strip membership is evaluated from icon centers with a fixed `14` px boundary margin so no candidate center sits near the strip edge.
24. **Icons relation mirror symmetry (`task_icons_relation_mirror_symmetry`)**
   - One two-panel image with a `Reference` cell on the left and a labeled `Scene` grid of icon-arrangement cells on the right.
   - Query variants: `mirror_vertical`, `mirror_horizontal`, `mirror_diagonal_main`, `mirror_diagonal_anti`, `mirror_both_axes`.
   - Count support: fixed `6` Scene cells, `target_count` in `0..4`, `distractor_count = 6 - target_count`.
   - Answer type: integer count.
   - Evidence: sorted `label_set` of the matching Scene cell labels.
   - Exactness rule: matching cells must satisfy exactly the same supported symmetry signature as the Reference cell (vertical, horizontal, main-diagonal, anti-diagonal, or vertical+horizontal only); distractors are a mix of exact-other-signature cells and cells with none of the supported symmetries, and the task uses the curated asymmetric icon subset so icon-level symmetry does not blur those signatures.
25. **Icons relation occlusion order (`task_icons_relation_occlusion_order`)**
   - One two-panel image with a `Reference` cell on the left and a labeled `Scene` grid of overlapping icon pairs on the right.
   - Query: how many labeled Scene cells show the same front-to-back order as the Reference cell.
   - Count support: `target_count` in `0..6`, `distractor_count` in `1..6`, total Scene cells in `2..12`.
   - Answer type: integer count.
   - Evidence: sorted `label_set` of the matching Scene cell labels.
26. **Graph counting degree count (`task_graph_counting_degree_count`)**
   - One single-panel labeled node-link graph.
   - Query variants: `How many nodes have degree k?`, `How many nodes have in-degree k?`, and `How many nodes have out-degree k?`
   - Graph contract: simple unweighted graph with `5..10` nodes for undirected degree queries and `5..9` nodes for directed in-/out-degree queries, labeled from `A..J` or `1..10`; the directed variants render arrowheads and reject reciprocal edge pairs for readability.
   - Variation axes: `topology_profile` (`balanced|low_degree|hub_heavy`) and `scene_variant` (`circular|shell|spring`).
   - Answer type: integer count.
   - Evidence: `label_set` of the node labels whose asked degree measure equals `k`.
27. **Graph relation same-component count (`task_graph_relation_same_component_count`)**
   - One single-panel labeled undirected node-link graph.
   - Query: `How many nodes, including node X itself, are in the same connected component as X?`
   - Graph contract: simple disconnected unweighted graph with `5..10` nodes, `2..4` connected components, and a queried component size in `1..6`.
   - Variation axes: `topology_profile` (`balanced|low_degree|hub_heavy`) and `scene_variant` (`circular|shell|spring`), plus non-semantic label/shape/color/layout-transform diversity shared with the graph domain.
   - Answer type: integer count.
   - Evidence: `label_set` of all node labels in the connected component containing the queried node, including the queried node itself.
28. **Graph comparison largest-component size (`task_graph_comparison_largest_component_size`)**
   - One single-panel labeled undirected node-link graph.
   - Query: `How many nodes are in the largest connected component?`
   - Graph contract: simple disconnected unweighted graph with `5..10` nodes, `2..4` connected components, and a unique-largest-component size in `2..6`.
   - Variation axes: `topology_profile` (`balanced|low_degree|hub_heavy`) and `scene_variant` (`circular|shell|spring`), plus non-semantic label/shape/color/layout-transform diversity shared with the graph domain.
   - Answer type: integer count.
   - Evidence: `label_set` of all node labels in the unique largest connected component.
29. **Graph counting articulation-point count (`task_graph_counting_articulation_point_count`)**
   - One single-panel labeled undirected node-link graph.
   - Query: `How many nodes are articulation points?`
   - Graph contract: simple undirected graph with `5..10` nodes and articulation-point-count support `0..8`.
   - Variation axes: `topology_profile` (`balanced|low_degree|hub_heavy`) and `scene_variant` (`circular|shell|spring`), plus non-semantic label/shape/color/layout-transform diversity shared with the graph domain.
   - Answer type: integer count.
   - Evidence: `label_set` of all articulation-point nodes.
30. **Graph counting bridge count (`task_graph_counting_bridge_count`)**
   - One single-panel labeled undirected node-link graph.
   - Query: `How many edges are bridges?`
   - Graph contract: simple connected undirected graph with `5..10` nodes and bridge-count support `0..8`.
   - Variation axes: `topology_profile` (`balanced|low_degree|hub_heavy`) and `scene_variant` (`circular|shell|spring`), plus non-semantic label/shape/color/layout-transform diversity shared with the graph domain.
   - Answer type: integer count.
   - Evidence: `edge_set` of all bridge edges, represented as unordered endpoint-label pairs.
31. **Graph relation unique-cycle size (`task_graph_relation_unique_cycle_size`)**
   - One single-panel labeled undirected node-link graph.
   - Query: `The graph contains exactly one cycle. How many nodes are in that cycle?`
   - Graph contract: connected unicyclic graph with `5..10` nodes, unique-cycle-size support `3..7`, and at least one node outside the cycle.
   - Variation axes: `topology_profile` (`balanced|low_degree|hub_heavy`) and `scene_variant` (`circular|shell|spring`), plus non-semantic label/shape/color/layout-transform diversity shared with the graph domain.
   - Answer type: integer count.
   - Evidence: `label_set` of all node labels in the unique cycle.
32. **Graph path shortest-path length (`task_graph_path_shortest_path_length`)**
   - One single-panel labeled node-link graph.
   - Query: `The graph has a unique shortest path from node X to node Y. How many edges are in that path?` or `The directed graph has a unique shortest path from node X to node Y, following the direction of the arrows. How many edges are in that path?`
   - Graph contract: connected simple graph, shortest-path-length support `1..5`, at least one node outside the witness path, undirected node counts in `5..10`, directed node counts in `5..9`, and exactly one shortest witness path between the queried endpoints.
   - Variation axes: `topology_profile` (`balanced|low_degree|hub_heavy`) and `scene_variant` (`circular|shell|spring`), plus non-semantic label/shape/color/layout-transform diversity shared with the graph domain.
   - Answer type: integer count.
   - Evidence: ordered `label_path` of all node labels on the unique shortest path from the queried source node to the queried goal node, including both endpoints.
33. **Graph relation reachable count (`task_graph_relation_reachable_count`)**
   - One single-panel labeled directed node-link graph.
   - Query: `How many nodes, including node X itself, are reachable from X by following the direction of the arrows?`
   - Graph contract: simple directed graph with `5..9` nodes, reachable-count support `1..7`, at least one unreachable node, and traversal semantics defined only by directed successor adjacency.
   - Variation axes: `topology_profile` (`balanced|low_degree|hub_heavy`) and `scene_variant` (`circular|shell|spring`), plus non-semantic label/shape/color/layout-transform diversity shared with the graph domain.
   - Answer type: integer count.
   - Evidence: unordered `label_set` of all node labels reachable from the queried source node, including the queried node itself.
34. **Graph optimization minimum-spanning-tree weight (`task_graph_optimization_minimum_spanning_tree_weight`)**
   - One single-panel labeled connected weighted node-link graph.
   - Query: `The weighted graph has a unique minimum spanning tree. What is its total weight?`
   - Graph contract: simple undirected graph with `5..8` nodes, `1..2` extra non-tree edges, distinct integer edge weights in `1..9`, and a unique MST by construction.
   - Variation axes: `topology_profile` (`balanced|low_degree|hub_heavy`) and `scene_variant` (`circular|shell|spring`), plus non-semantic label/shape/color/layout-transform diversity shared with the graph domain.
   - Answer type: integer total weight.
   - Evidence: `edge_set` of all MST edges, represented as unordered endpoint-label pairs.
35. **Graph order topological position (`task_graph_order_topological_position`)**
   - One single-panel labeled directed acyclic graph.
   - Query: `What is the position of node X in the unique topological order, counting from 1?`
   - Graph contract: simple DAG with `5..7` nodes, a unique topological order by construction, and target-position support `1..7`.
   - Variation axes: `topology_profile` (`balanced|low_degree|hub_heavy`) and `scene_variant` (`circular|shell|spring`), plus non-semantic label/shape/color/layout-transform diversity shared with the graph domain.
   - Answer type: integer position.
   - Evidence: ordered `label_sequence` of all node labels in the unique topological order from first to last.
31. **Icons sequence missing count (`task_icons_sequence_missing_count`)**
   - One single-panel image with a horizontal row of `4..6` Scene boxes.
   - Query: how many icons should appear in the missing Scene box to continue the sequence.
   - Sequence rule: visible box counts follow one arithmetic progression with hidden answer support `0..10` and integer step `±1..±3`.
   - Visual rule: all visible Scene icons keep one shared icon type and tint, may vary by rotation, use the smaller `24..40` px size band, stay within `20%` pairwise overlap inside each box, and each instance samples one row box width/height with the final canvas fit to that row geometry.
   - Answer type: integer count.
   - Evidence: one-box `bbox_set` for the missing Scene box in final image coordinates.
32. **Icons sequence rotation violation (`task_icons_sequence_rotation_violation`)**
   - One single-panel image with a horizontal row of `5..7` numbered Scene boxes, each containing exactly one icon.
   - Query: which numbered box breaks the rotation sequence.
   - Sequence rule: the clean row follows one constant step over rotations `{0, 90, 180, 270}` using step support `{90, 270}`, and exactly one box is corrupted away from that rule.
   - Visual rule: all Scene icons keep one shared icon type and tint from the curated asymmetric icon subset, use the larger `48..72` px size band, and each instance samples its own row box width/height with the final canvas fit to that row geometry.
   - Answer type: integer box index.
   - Evidence: one-box `bbox_set` for the violating Scene box in final image coordinates.
   - Ambiguity rule: reject any row where more than one box index could plausibly be the unique violation under the supported constant-step hypotheses.
33. **Icons pattern grid rotation violation (`task_icons_pattern_grid_rotation_violation`)**
   - One single-panel image with a numbered `3 x 3` grid of Scene boxes, each containing exactly one icon.
   - Query: which numbered box breaks the 2D rotation pattern.
   - Pattern rule: the clean grid follows one row/column offset rule `rotation[row, col] = base + row * row_step + col * col_step (mod 360)` using rotations `{0, 90, 180, 270}` and row/column step supports `{90, 180, 270}`.
   - Visual rule: all Scene icons keep one shared icon type and tint from the curated asymmetric icon subset, use the larger `48..72` px size band, and the final canvas is fit to sampled square-friendly grid cell geometry.
   - Answer type: integer box index.
   - Evidence: one-box `bbox_set` for the violating grid box in final image coordinates.
   - Ambiguity rule: reject any grid where more than one box index could plausibly be the unique violation under the supported row/column rule hypotheses.
34. **Icons pattern grid size violation (`task_icons_pattern_grid_size_violation`)**
   - One single-panel image with a numbered `3 x 3` grid of Scene boxes, each containing exactly one icon.
   - Query: which numbered box breaks the 2D size pattern.
   - Pattern rule: the clean grid follows one row/column size-level rule `level[row, col] = base + row * row_step + col * col_step` using symbolic levels `{1,2,3,4,5}` and step supports `{-1,0,1}` with the all-zero step pair disallowed.
   - Visual rule: all Scene icons keep one shared icon type, one shared tint, and one shared rotation from the curated Prism icon pool; only nominal size changes across the grid, and per-instance pixel sizes are derived from the symbolic size ladder after sampled cell geometry is fixed.
   - Answer type: integer box index.
   - Evidence: one-box `bbox_set` for the violating grid box in final image coordinates.
   - Ambiguity rule: reject any grid where more than one box index could plausibly be the unique violation under the supported row/column size-rule hypotheses.
32. **Icons counting singleton type (`task_icons_counting_singleton_type`)**
   - One single-panel image with `6..15` randomly placed Scene icons.
   - Query: how many icons have a type that appears exactly once in the image.
   - Frequency rule: counting is over icon type only; colors and rotations may vary per icon, but repeated `icon_id` values define the repeated groups and singleton `icon_id` values define the counted witnesses.
   - Sampling rule: `target_count` in `0..5`; the remaining icons are partitioned into `1..4` repeated types with multiplicity `2..4` each, so at least one repeated type always remains in the scene.
   - Answer type: integer count.
   - Evidence: sorted `bbox_set` of the singleton-type icons in final image coordinates.

## Future polygon variants (deferred)
1. Polygon diameter measurement.
2. Polygon minimum-side query.
3. Polygon maximum-side query.

## Evidence formatting notes
1. Evidence coordinate frame is task/domain declared (`graph_unit`, `pixel`, `cell`, etc.), not globally fixed.
2. If exact integer projection is impossible for a shape family, keep values as close as possible and document canonicalization in task docs.
3. Evidence schema must be declared in each task contract and remain stable for verifier compatibility.
4. For counting families with object labels, prefer `label_set` evidence over geometric coordinates so multi-object grounding stays compact and readable.
5. For reference+scene icon tasks, prefer `bbox_set` evidence over labels so grounding stays tied to visible scene instances rather than hidden asset ids.
6. For graph path families, prefer an ordered graph-native witness type such as `label_path` instead of overloading unordered `label_set`.
7. For graph edge-witness families, use one graph-native edge witness type such as `edge_set` rather than collapsing bridge- or MST-like witnesses onto nodes or pixel boxes.
8. For graph ordered-but-nonpath families, use an ordered label-sequence witness such as `label_sequence`; keep the ordered JSON shape, but do not imply that consecutive labels must be adjacent in the graph.

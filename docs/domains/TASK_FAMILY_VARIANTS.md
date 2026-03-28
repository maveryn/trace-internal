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
2. The active table families are `statistics`, `counting`, and `readout`.
3. `task_tables_statistics_summary_label` uses semantic `task_variant` values `argmax` and `argmin`.
4. `task_tables_statistics_summary_value` uses semantic `task_variant` values `column_sum`, `column_mean`, and `column_median`.
5. `task_tables_statistics_row_summary_value` uses semantic `task_variant` values `row_sum` and `row_mean`.
6. `task_tables_counting_value_count` uses semantic `task_variant` values `above_threshold`, `below_threshold`, and `in_interval`.
7. `task_tables_counting_column_pair_count` uses semantic `task_variant` values `col_a_gt_col_b` and `col_a_lt_col_b`.
8. `task_tables_readout_subset_value` uses semantic `task_variant` values `cell_lookup`, `cell_sum_two`, and `cell_difference_two_abs`.
9. `task_tables_relation_row_compare_label` uses semantic `task_variant` values `higher_of_two_rows` and `lower_of_two_rows`.
10. All active table tasks use `scene_variant` values `spreadsheet`, `zebra`, `ledger`, and `card_table`.
11. Table row labels should use short visible human-style names rather than single letters when the answer is a row identity.
12. Table tasks use one fixed prompt-facing evidence type in v1: `bbox_set`.
13. Evidence boxes should mark the minimal supporting table region(s): one decisive numeric cell bbox for `task_tables_statistics_summary_label`, one queried-column region bbox for `task_tables_statistics_summary_value`, one queried-row region bbox for `task_tables_statistics_row_summary_value`, one ordered set of matching value-cell bboxes for `task_tables_counting_value_count`, one ordered set of compared two-column value-cell pairs for `task_tables_counting_column_pair_count`, one queried value-cell bbox or ordered queried-cell pair for `task_tables_readout_subset_value`, and one ordered pair of compared queried-column value-cell bboxes for `task_tables_relation_row_compare_label`.

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
26. **Icons sequence missing count (`task_icons_sequence_missing_count`)**
   - One single-panel image with a horizontal row of `4..6` Scene boxes.
   - Query: how many icons should appear in the missing Scene box to continue the sequence.
   - Sequence rule: visible box counts follow one arithmetic progression with hidden answer support `0..10` and integer step `±1..±3`.
   - Visual rule: all visible Scene icons keep one shared icon type and tint, may vary by rotation, use the smaller `24..40` px size band, stay within `20%` pairwise overlap inside each box, and each instance samples one row box width/height with the final canvas fit to that row geometry.
   - Answer type: integer count.
   - Evidence: one-box `bbox_set` for the missing Scene box in final image coordinates.

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

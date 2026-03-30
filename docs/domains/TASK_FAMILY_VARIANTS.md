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

## Diagrams direction (current)
1. Diagrams should stay schematic and diagram-native; do not use `diagrams` for generic graph problems or document layouts with a few connectors.
2. The active early diagrams families are `flow`, `hierarchy`, `cycle`, `set_diagram`, and `schematic`.
3. `task_diagrams_flow_next_step_label` uses semantic `task_variant` values `direct_next_step` and `branch_next_step`.
4. `task_diagrams_flow_next_step_label` uses visual `scene_variant` values `flowchart` and `swimlane`.
5. `task_diagrams_hierarchy_ancestor_label` uses semantic `task_variant` values `parent_of_node` and `lowest_common_ancestor_of_two_nodes`.
6. `task_diagrams_hierarchy_ancestor_label` uses visual `scene_variant` value `org_chart`.
7. `task_diagrams_cycle_offset_stage_label` uses semantic `task_variant` values `after_k_steps` and `before_k_steps`.
8. `task_diagrams_cycle_offset_stage_label` uses visual `scene_variant` value `cycle_ring`.
9. `task_diagrams_set_diagram_region_sum_value` uses semantic `task_variant` values `sum_only_in_named_set`, `sum_in_named_set`, `sum_in_named_union`, `sum_in_named_intersection`, and `sum_in_exactly_two_sets`.
10. `task_diagrams_set_diagram_region_sum_value` uses visual `scene_variant` value `set_diagram`.
11. `task_diagrams_schematic_callout_target_label` uses semantic `task_variant` values `callout_for_named_part` and `callout_for_highlighted_part`.
12. `task_diagrams_schematic_callout_target_label` uses visual `scene_variant` value `annotated_schematic`.
13. Prompt-facing flow evidence should stay as one-box `bbox_set` grounding on the target next-step node; keep lane and branch-label geometry in trace unless a later task explicitly queries those elements.
14. Prompt-facing hierarchy evidence should stay as one-box `bbox_set` grounding on the target ancestor node; keep connector geometry in trace unless a later task explicitly queries the connectors themselves.
15. Prompt-facing cycle evidence should stay as one-box `bbox_set` grounding on the target stage; keep arrow and direction-badge geometry in trace unless a later task explicitly queries those elements.
16. Prompt-facing set-diagram evidence should stay on the contributing digits themselves as an ordered `bbox_set`; keep region geometry in trace unless a later task explicitly queries the regions themselves.
17. Prompt-facing schematic evidence should stay on the queried target part rather than the answer badge; keep callout-circle and leader-line geometry in trace unless a later task explicitly queries those elements.
18. Swimlane remains a visual scene variant inside `flow`, not a separate task group, as long as the reasoning contract is still “follow the visible process structure.”
19. Org-chart hierarchy should stay tree-native; if a later diagram starts depending on arbitrary node-link structure instead of rooted parent-child containment, it likely belongs back in `graph`.

## Documents direction (current)
1. Documents should start with structured page reasoning families such as `readout`, `arithmetic`, `layout`, `relation`, `selection`, and later `line_items`; avoid counting a task as `documents` if it is really a free-form OCR paragraph benchmark.
2. The active early documents families are `readout`, `arithmetic`, `layout`, `relation`, and `selection`.
3. `task_documents_readout_field_value` uses semantic `task_variant` values `lookup_identifier`, `lookup_name`, `lookup_date`, `lookup_contact`, and `lookup_amount`.
4. `task_documents_arithmetic_section_expression_value` uses semantic `task_variant` values `sum_two_amounts_in_section`, `difference_two_amounts_in_section`, and `sum_minus_amount_in_section`.
5. `task_documents_layout_section_membership_label` uses semantic `task_variant` values `section_of_field_label`, `section_of_field_value`, and `section_of_label_value_pair`.
6. `task_documents_relation_section_extremum_value` uses semantic `task_variant` values `earliest_date_in_section`, `latest_date_in_section`, `largest_amount_in_section`, and `smallest_amount_in_section`.
7. `task_documents_selection_checkbox_count` uses semantic `task_variant` values `checked_box_count` and `unchecked_box_count`.
8. The active document task families all use visual `scene_variant` values drawn from `form_sheet`, `invoice_sheet`, and `receipt_sheet`.
9. Document arithmetic, layout, and relation tasks should target a named visible section like `Profile`, `Fees`, `Dates`, `Billing Summary`, or `Totals` so the model must localize the relevant block before answering.
10. The active structured-document grammar keeps the same label/value semantics across the three page styles:
   - boxed field grids for forms,
   - header blocks and summary boxes for invoices,
   - narrow labeled rows for receipts.
11. Prompt-facing document readout evidence should stay as one ordered `bbox_set` pair `[label_bbox, value_bbox]`.
12. Prompt-facing document arithmetic evidence should stay as the ordered operand value boxes only; do not widen it to the whole section or include unrelated labels when the computation is local to visible amount fields.
13. Prompt-facing document layout evidence should stay as the matching section-header bbox only; do not widen section-membership tasks to the whole section or full page when the answer is one named block.
14. Document text generation should stay typed and short; prefer IDs, dates, amounts, names, and contact fields over long prose in early families.

## Puzzles direction (current)
1. Puzzles use `task_group` for hidden-rule reasoning families such as `arithmetic`, `logic`, `spatial`, and `topology`; avoid splitting families by one-off visual templates when the reasoning contract is still the same.
2. Early arithmetic puzzle tasks should favor explicit unknown slots so evidence can stay local and visually obvious.
3. `task_puzzles_arithmetic_equation_value` uses semantic `task_variant` values `result_unknown` and `operand_unknown`.
4. `task_puzzles_arithmetic_equation_value` uses visual `scene_variant` values `equation_strip`, `equation_card`, and `equation_outline`.
5. `task_puzzles_arithmetic_balance_value` uses semantic `task_variant` values `sum_pair_unknown`, `two_panel_chain_unknown`, and `three_panel_chain_unknown`.
6. `task_puzzles_arithmetic_balance_value` uses visual `scene_variant` values `balance_strip`, `balance_card`, and `balance_outline`.
7. `task_puzzles_arithmetic_grid_value` uses semantic `task_variant` values `sum_rule_missing`, `difference_rule_missing`, and `product_rule_missing`.
8. `task_puzzles_arithmetic_grid_value` uses visual `scene_variant` values `grid_strip`, `grid_card`, and `grid_outline`.
9. The active equation-scene grammar uses one flat equation row with `2..5` left-side operand boxes, operators sampled from `+`, `-`, and `×`, one right-side result box, and the `?` randomly placed on either side according to `task_variant`.
10. The active balance-scene grammar uses `2..3` stacked equality panels with boxed symbols and numbers, explicit `+` and `=` signs, and a final query row shaped like `symbol = ?`.
11. The active arithmetic-grid grammar uses `3..5` rows, exactly `3` columns, no headers, and a repeated hidden row rule `a op b = c` with one explicit `?` cell.
12. Prompt-facing arithmetic evidence should stay as one-box `bbox_set` grounding on the queried unknown slot, final question-mark query box, or question-mark grid cell; do not widen to explanatory multi-box evidence unless a later family truly needs ordered witnesses.
13. `task_puzzles_logic_adjacency_completion_label` uses semantic `task_variant` value `king_non_touch`.
14. `task_puzzles_logic_adjacency_completion_label` uses visual `scene_variant` values `logic_strip`, `logic_card`, and `logic_outline`.
15. `task_puzzles_logic_grid_completion_label` uses semantic `task_variant` values `row_uniqueness`, `column_uniqueness`, and `row_and_column_uniqueness`.
16. `task_puzzles_logic_grid_completion_label` uses visual `scene_variant` values `logic_strip`, `logic_card`, and `logic_outline`.
17. The active logic-board grammar uses one square `3x3` through `5x5` board with one explicit `?` cell and exactly six labeled image options.
18. The explicit adjacency logic variant must state whether matching symbols are forbidden by edge only or by edge and corner; the current `king_non_touch` rule forbids both and uses the full six-shape option set so the answer stays unique from the visible neighborhood.
19. Prompt-facing logic evidence should stay as one-box `bbox_set` grounding on the winning option panel; keep the query interaction stable as option selection even when later logic families vary the rule structure.
20. `task_puzzles_spatial_fold_result_label` uses semantic `task_variant` values `vertical_fold_result` and `horizontal_fold_result`.
21. `task_puzzles_spatial_fold_result_label` uses visual `scene_variant` values `fold_strip`, `fold_card`, and `fold_outline`.
22. The active spatial fold-result grammar uses one marked paper sheet with an explicit dashed fold line and arrow above exactly six labeled folded-result options; keep the fold direction explicit in the reference sheet rather than implicit in the options alone.
23. `task_puzzles_spatial_cube_removal_count` uses semantic `task_variant` value `cube_removal_count`.
24. `task_puzzles_spatial_cube_removal_count` uses visual `scene_variant` values `stack_strip`, `stack_card`, and `stack_outline`.
25. The active cube-removal grammar uses one fixed-view side-by-side isometric comparison of an original block stack and the remaining stack after cubes were removed, and asks for the exact removal count.
26. `task_puzzles_spatial_assembly_label` uses semantic `task_variant` value `can_be_built`.
27. `task_puzzles_spatial_assembly_label` uses visual `scene_variant` values `assembly_strip`, `assembly_card`, and `assembly_outline`.
28. The active assembly grammar uses `2..4` polyomino pieces above `5..6` labeled silhouette options, keeps one shared polyomino cell size across the top pieces and the option silhouettes, and asks which option can be built by using all pieces exactly once.
29. `task_puzzles_spatial_overlay_result_label` uses semantic `task_variant` value `overlay_union_same_grid`.
30. `task_puzzles_spatial_overlay_result_label` uses visual `scene_variant` values `overlay_strip`, `overlay_card`, and `overlay_outline`.
31. The active transparent-sheet overlay grammar uses two aligned source sheets above `5..6` labeled result options, keeps the paper frames and hidden grid alignment fixed across both source sheets and all options, and asks which option matches the union of the two source mark sets when no rotation or flipping is allowed.
32. Prompt-facing spatial evidence should stay as one-box `bbox_set` grounding on the winning option image/panel for fold-result, assembly, and overlay tasks or as the ordered two-box structure pair `[original left, remaining right]` for cube-removal tasks; do not invent fake per-missing-cube or explanatory assembly bboxes.
33. `task_puzzles_topology_bead_equivalence_count` uses semantic `task_variant` values `color_cycle_count`, `shape_cycle_count`, and `mixed_cycle_count`.
34. `task_puzzles_topology_bead_equivalence_count` uses visual `scene_variant` values `loop_strip`, `loop_card`, and `loop_outline`.
35. The active topology bead-loop grammar uses one reference loop above `6..7` labeled option loops, `4..6` beads per loop, and counts the options whose bead order matches the reference up to cyclic rotation only; color-bearing variants should use Lab-separated colors, prompt-facing evidence should be the ordered set of valid option-image bboxes, and the prompt must explicitly say that flipping/reflection is not allowed.

## Temporal direction (current)
1. Temporal tasks should group by visual time artifact (`clock`, `calendar`, `schedule`, `timeline`) rather than by one exact question stem.
2. The current active temporal families are `clock`, `calendar`, `schedule`, and `timeline`.
3. `task_temporal_clock_readout` uses semantic `task_variant` values `shown_time`, `minutes_after`, and `minutes_before`.
4. `task_temporal_clock_compare` uses semantic `task_variant` values `earliest_time` and `latest_time`.
5. `task_temporal_calendar_month_view` uses semantic `task_variant` values `date_of_weekday_occurrence`, `count_marked_weekend_days`, and `days_between_marked_dates`.
6. `task_temporal_schedule_day_planner` uses semantic `task_variant` values `overlap_count`, `longer_than_reference_count`, and `maximum_non_overlapping_count`.
7. `task_temporal_timeline_milestones` uses semantic `task_variant` values `before_reference_count`, `between_reference_events_count`, and `position_of_reference`.
8. The active temporal tasks use visual `scene_variant` values `classic`, `minimal`, and `outline`, except `task_temporal_timeline_milestones`, which uses `classic|roadmap|minimal`.
9. The active temporal tasks use non-semantic visual axes `style_variant=studio|accented|marker` and `accent_color_name` from the shared named-color palette; these axes should change styling only, never the prompt contract.
10. `task_temporal_clock_readout` uses two-hand `bbox_set` evidence over the hour and minute hands, `task_temporal_clock_compare` uses a one-box `bbox_set` over the winning clock face, `task_temporal_calendar_month_view` uses date-cell `bbox_set` evidence over the relevant day cells, `task_temporal_schedule_day_planner` uses event-block `bbox_set` evidence over the relevant schedule blocks, and `task_temporal_timeline_milestones` uses event-card `bbox_set` evidence over the relevant timeline milestones.
11. Early temporal tasks should prefer local prompt-facing evidence on the queried artifact itself (for example hand bboxes, winning clock faces, date-cell bboxes, event blocks, or event cards) instead of wide scene evidence.
12. For temporal offset variants, keep the displayed scene fixed and let the prompt carry the offset; prompt JSON examples must match the active offset semantics rather than reusing the direct-readout example answer.
13. For month-view calendar tasks, keep the visual scaffold fixed to one month grid and widen question diversity through `task_variant`; do not fork separate calendar task ids for nth-weekday lookup vs marked-date counting when the same date-cell evidence contract already covers them.
14. For single-day schedule tasks, keep one stable planner scaffold and widen question diversity through `task_variant`; if a schedule variant answers with a selected event subset, enforce that witness subset’s uniqueness by construction before exposing it as prompt-facing evidence.
15. For milestone-timeline tasks, keep evidence on visible event cards rather than the full axis or connector lines, even when the answer depends on temporal order across multiple events.

## Physics direction (current)
1. Physics should stay diagram-first: the image should contain the operative values, directions, or placements needed to solve the task.
2. `task_group` should encode the reasoning family (for example `mechanics`, later `circuits` or `optics`), while `scene_variant` names the scaffold and `query_variant` names the requested quantity.
3. The active physics families are `mechanics`, `circuits`, and `optics`.
4. `task_physics_mechanics_force_diagram`
   - uses scene variants `free_body_box|textured_block`
   - uses query variants `net_horizontal_force|net_vertical_force|balancing_force_horizontal|balancing_force_vertical`
   - keeps integer answers with unordered `bbox_set` evidence over either the shown queried-axis arrows (`net_*`) or the marked `?` arrow (`balancing_force_*`)
5. `task_physics_mechanics_lever_balance`
   - uses scene variants `center_fulcrum|offset_fulcrum|textured_beam`
   - uses query variants `left_torque|right_torque|missing_weight_to_balance`
   - keeps integer answers with unordered `bbox_set` evidence over either the relevant side’s weight blocks (`*_torque`) or the marked `?` weight block (`missing_weight_to_balance`)
   - samples one non-semantic `accent_color_name` palette for the beam / fulcrum / shown weights while leaving the red `?` weight semantics unchanged
6. `task_physics_circuits_equivalent_resistance`
   - uses scene variants `parallel|simple_series_parallel`
   - uses query variants `total_resistance|missing_resistor_value`
   - keeps integer answers with unordered `bbox_set` evidence over either the full asked resistor set (`total_resistance`) or the marked red `?` resistor in the left circuit (`missing_resistor_value`)
   - requires every scene to contain at least one parallel bank; the single-circuit readout uses `3..4` parallel branches or `4..5` total resistors, while the paired missing-resistor variant uses smaller side-by-side circuits with equal total resistance
   - samples one non-semantic `accent_color_name` palette for the wires, terminals, and resistor boxes
7. `task_physics_optics_ray_trace`
   - uses scene variants `single_mirror|double_mirror|triple_mirror|quad_mirror`
   - uses query variants `bounce_count|target_hit_count`
   - keeps integer answers with unordered `graph_point_set` evidence over either bounce points or hit target points
   - shows only the initial ray direction in the prompt image, keeps the solved full path in trace/debug artifacts, ties mirror count directly to `scene_variant`, and reserves `quad_mirror` for `bounce_count` while the smaller mirror-count scenes feed `target_hit_count`
   - uses large unlabeled target dots for `target_hit_count`, no separate bounce circles for `bounce_count`, and one non-semantic `accent_color_name` palette for the board and mirrors while the ray keeps a fixed warm contrast color
8. `task_physics_mechanics_spring_extension`
   - uses scene variants `paired_springs|staggered_springs|textured_spring`
   - uses query variants `missing_weight_for_extension|missing_extension_for_weight|extension_difference`
   - keeps integer answers with unordered `bbox_set` evidence over either the two compared extension markers (`extension_difference`) or the reference/query weight-marker witness set for the two missing-value variants
   - keeps the two springs explicitly identical within each instance and encodes the proportionality only through the shown weight/extension pair, not through a printed formula
   - uses one non-semantic `accent_color_name` palette for the card chrome / support bars / springs while the missing-value placeholders remain red
9. Early physics tasks should prefer light arithmetic over heavy formula derivations, and prompt-facing evidence should stay on the visible witness objects rather than decorative scene chrome.

## Games direction (current)
1. Games should start with real game-state artifacts whose visible pieces are sufficient to answer the question; do not hide state or rely on unstated house rules in early tasks.
2. The active games families are `dots_and_boxes`, `bingo`, `cards`, and `dominoes`.
3. `task_games_dots_and_boxes_capture_count`
   - uses scene variant `single_board`
   - uses query variant `forced_turn_capture_count`
   - keeps integer answers with unordered `bbox_set` evidence over the boxes captured during the highlighted forced turn
   - uses one non-semantic `style_variant` axis `classic|soft|outlined` for paper-board chrome only
4. `task_games_bingo_completed_line_count`
   - uses scene variant `single_card`
   - uses query variants `completed_row_count|completed_column_count|completed_straight_line_count`
   - keeps integer answers with unordered marked-cell `bbox_set` evidence over the cells in the counted completed lines
   - uses one non-semantic `style_variant` axis `classic|soft|outlined` for bingo-card chrome and mark styling only
5. `task_games_cards_hand_count`
   - uses scene variants `single_row|two_row`
   - uses query variants `same_suit_as_reference_count|higher_than_reference_count|pair_count|longest_run_length`
   - keeps integer answers with unordered `bbox_set` evidence over the relevant cards in the visible hand
   - uses one non-semantic `style_variant` axis `classic|soft|outlined` for card chrome only
6. `task_games_dominoes_chain_count`
   - uses scene variants `single_row|two_row`
   - uses query variants `matching_end_count|higher_sum_than_reference_count|sum_to_target_count|double_count`
   - keeps integer answers with unordered `bbox_set` evidence over the matching loose dominoes below the top chain
   - uses one non-semantic `style_variant` axis `classic|soft|outlined` for domino chrome only
7. Dots-and-boxes tasks should keep the highlighted starting move explicit in the image and state the bonus-turn / forced-continuation rule directly in the prompt so the task stays grounded in the visible board state instead of hidden strategy.
8. Bingo-card tasks should keep the first scaffold to one visible `5 x 5` card and state exactly which line types count; do not imply diagonal or free-center rules unless the prompt says so directly.
9. Card-hand tasks should keep visible card counts in the `7..14` range, with two-row layouts reserved for larger hands so cards stay readable.
10. Domino-chain tasks should keep the top chain as reference/context and the loose dominoes below as the counted witness set, with explicit rule text whenever the query depends on open-end matching, pip sums, or doubles.
11. When a card-hand task depends on display order across wrapped rows (for example longest-run questions), keep an explicit continuation cue in the image and state the reading order directly in the prompt.

## Geometry direction (current)
1. Geometry now exposes ten active task ids:
   - `task_geometry_measurement_value`
   - `task_geometry_comparison_value`
   - `task_geometry_counting_value`
   - `task_geometry_analytical_2d_value`
   - `task_geometry_analytical_3d_value`
   - `task_geometry_coordinate_relation`
   - `task_geometry_graphing_count`
   - `task_geometry_solid_view_count`
   - `task_geometry_similarity_count`
   - `task_geometry_transformation_match`
2. Geometry follows a chart-style two-axis policy:
   - `scene_variant` identifies the geometric scene family / object family,
   - `query_variant` identifies the requested question type.
3. The consolidation is taxonomy-first: legacy geometry generators still provide the underlying scene construction, prompt wording, and verifier traces, but active sampling and docs now expose the broader scene/query surface instead of 20 separate task ids.
4. `task_geometry_measurement_value`
   - uses scene variants `angle|segment|triangle|quadrilateral|pentagon|circle|ellipse|line`
   - uses query variants `angle|length|area|perimeter|slope`
   - keeps legacy graph-grounded evidence (`graph_point` / `graph_point_set`) and legacy answer typing (`integer|decimal|pi_expression`) by compatible pair
5. `task_geometry_comparison_value`
   - uses scene variants `angle|segment|rectangle`
   - uses query variants `largest_angle|smallest_angle|largest_length|smallest_length|largest_area|smallest_area|largest_perimeter|smallest_perimeter`
   - keeps `option_letter` answers with winner-specific geometry evidence
6. `task_geometry_counting_value`
   - uses scene variants `angle|triangle|quadrilateral|mixed_shape|polygon`
   - uses query variants for the counted class (`acute_angle`, `square`, `ellipse`, `concave_polygon`, etc.)
   - keeps integer answers with unordered `label_set` evidence
7. `task_geometry_analytical_2d_value`
   - uses scene variants `rectangle|triangle|parallelogram|trapezoid|rhombus|circle|ellipse|composite_region`
   - uses query variants `area|length|perimeter|composite_area`
   - keeps structured `measurement_ref_map` evidence and the legacy analytical answer typing
8. `task_geometry_analytical_3d_value`
   - uses scene variants `rectangular_prism|triangular_prism|square_pyramid|cylinder|cone|sphere`
   - uses query variants `volume|surface_area`
   - keeps structured `measurement_ref_map` evidence and the legacy analytical answer typing
9. `task_geometry_transformation_match`
   - uses scene variants `triangle|quadrilateral`
   - uses query variants `translation_match|reflection_match|rotation_match`
   - keeps `option_letter` answers with winning-polygon `graph_point_set` evidence
10. `task_geometry_similarity_count`
   - uses scene variants `triangle|quadrilateral`
   - uses query variants `congruent_count|similar_count`
   - keeps integer answers with unordered `label_set` evidence over the matching candidate labels
11. `task_geometry_coordinate_relation`
   - uses scene variants `segment_set|line_points|quadrant_points|polygon_lattice`
   - uses query variants `parallel_count|perpendicular_count|collinear_count|same_quadrant_count|point_in_shape_count`
   - uses integer answers plus unordered `graph_point_set` evidence for segment-count variants, where the witness is the set of matching-segment endpoint coordinates relative to target segment `AB`
   - uses integer answers plus unordered `graph_point_set` evidence for `collinear_count`, where the witness is the set of dot-point coordinates lying on the line through `A` and `B`
   - keeps segment scenes on centered `20 x 20` graph paper and samples the target plus candidate segments anywhere in the window as long as their endpoints stay off the border and no segments intersect
   - uses integer answers plus unordered `graph_point_set` evidence for `same_quadrant_count`, where the witness is the set of dot-point coordinates in the same quadrant as the X-marked reference point
   - uses integer answers plus `graph_point_set` evidence for `point_in_shape_count`, where the witness is the set of integer lattice points strictly inside the polygon
12. `task_geometry_graphing_count`
   - uses scene variants `quadratic|absolute_value|cubic|sinusoid|piecewise_linear`
   - uses query variants `x_intercept_count|horizontal_line_intersection_count|turning_point_count|local_minima_count|local_maxima_count`
   - keeps integer answers with unordered `graph_point_set` evidence over the relevant intersection or turning-point coordinates
13. `task_geometry_solid_view_count`
   - uses scene variant `cube_stack`
   - uses query variants `top_view_visible_count|front_view_visible_count|right_view_visible_count`
   - uses a two-panel cube-stack + blank query-grid scaffold rather than graph paper
   - keeps integer answers with prompt-facing `bbox_set` evidence on the query-grid cells that should be filled in the requested orthographic view
14. For the five consolidated value tasks, `execution_trace`, `query_spec.params`, and `scene_ir.relations` should expose the consolidated `scene_variant` / `query_variant` pair, while preserving `legacy_task_id` and other `legacy_*` trace slots for auditability.
16. **Icons counting reference match (`task_icons_counting_reference_match_count`)**
   - One two-panel image with a `Reference` icon and a `Scene` panel of icons.
   - Query variants: `match_type|match_color|match_orientation|match_attribute_binding`.
   - Count support: `target_count` in `0..10`, `distractor_count` in `1..10`, total scene icons in `1..20`.
   - Asset policy: `match_type|match_color` use the full Prism pool, while `match_orientation|match_attribute_binding` use the asymmetric subset.
   - Predicate policy: `match_type` compares only `icon_id`, `match_color` only `tint_rgb`, `match_orientation` only `rotation_degrees`, and `match_attribute_binding` requires all three at once with structured partial-match distractors.
   - Answer type: integer count.
   - Evidence: scene-only `bbox_set` in final image coordinates.
17. **Icons counting size relation (`task_icons_counting_size_relation`)**
   - One two-panel image with a `Reference` icon and a `Scene` panel of icons.
   - Query variants: count scene icons that are `smaller` or `larger` than the reference icon.
   - Scene keeps the same icon type as the reference while randomizing tint and rotation; size is the only matching predicate.
   - Count support: `target_count` in `0..8`, `distractor_count` in `1..8`, total scene icons in `1..16`.
   - Size distinction rule: reference nominal size is sampled from `64..96` px, scene nominal sizes from `40..120` px, and every scene icon must satisfy `|scene_size-reference_size| >= 12` px so there are no same-size near misses.
   - Answer type: integer count.
   - Evidence: scene-only `bbox_set` in final image coordinates.
18. **Icons transformation pair count (`task_icons_transformation_pair_count`)**
   - One two-panel image with a `Reference` pair and a labeled `Scene` grid of icon pairs.
   - Query: how many Scene cells apply the same transformation as the Reference pair.
   - Transform vocabulary: `rot90`, `rot180`, `rot270`, `flip_h`, `flip_v`, `flip_diag_main`, `flip_diag_anti`.
   - Count support: `target_count` in `0..6`, `distractor_count` in `1..6`, total Scene cells in `2..12`.
   - Answer type: integer count.
   - Evidence: sorted `label_set` of the matching Scene cell labels.
   - Visual distinction rule: candidate icons are accepted only when the sampled transform and at least one distractor transform remain visually distinct from identity and from the reference transform.
19. **Icons relation relative-position type (`task_icons_relation_relative_position_type`)**
   - One two-panel image with a `Reference` icon on the left and a `Scene` panel of icons on the right; exactly one Scene icon is visibly marked as the `Anchor`.
   - Query variants: `left_of_anchor`, `right_of_anchor`, `above_anchor`, `below_anchor`.
   - Count support: `target_count` in `0..5`, `distractor_count` in `max(1, target_count + 1)..10`, with the Anchor excluded from the counted candidate set.
   - Answer type: integer count.
   - Evidence: scene-only `bbox_set` in final image coordinates.
   - Spatial distinction rule: evaluate left/right/above/below strictly from rendered bboxes, mix distractors across same-type wrong-side and different-type queried-side cases so the scene cannot be solved from one-sided occupancy alone, and require same-type wrong-side distractors to sit mostly outside the queried region (Prism-style relaxed margin rule).
20. **Icons relation between two anchors count (`task_icons_relation_between_two_anchors_count`)**
   - One single-panel image with free-placed Scene icons and two visibly marked anchors `A` and `B`.
   - Query variants: `inside_vertical_strip`, `inside_horizontal_strip`.
   - Count support: `target_count` in `0..5`, `distractor_count` in `1..10`, with the anchors excluded from the counted candidate set.
   - Answer type: integer count.
   - Evidence: scene-only `bbox_set` in final image coordinates.
   - Spatial distinction rule: anchors share the same icon type/tint/rotation and are exactly aligned on the non-varying axis, all candidates use a different icon type from the anchors, and strip membership is evaluated from icon centers with a fixed `14` px boundary margin so no candidate center sits near the strip edge.
21. **Icons relation mirror symmetry (`task_icons_relation_mirror_symmetry`)**
   - One two-panel image with a `Reference` cell on the left and a labeled `Scene` grid of icon-arrangement cells on the right.
   - Query variants: `mirror_vertical`, `mirror_horizontal`, `mirror_diagonal_main`, `mirror_diagonal_anti`, `mirror_both_axes`.
   - Count support: fixed `6` Scene cells, `target_count` in `0..4`, `distractor_count = 6 - target_count`.
   - Answer type: integer count.
   - Evidence: sorted `label_set` of the matching Scene cell labels.
   - Exactness rule: matching cells must satisfy exactly the same supported symmetry signature as the Reference cell (vertical, horizontal, main-diagonal, anti-diagonal, or vertical+horizontal only); distractors are a mix of exact-other-signature cells and cells with none of the supported symmetries, and the task uses the curated asymmetric icon subset so icon-level symmetry does not blur those signatures.
22. **Icons relation occlusion order (`task_icons_relation_occlusion_order`)**
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
32. **Icons pattern structured violation (`task_icons_pattern_structured_violation`)**
   - One single-panel numbered row or grid, with exactly one icon per visible box.
   - Query variants: `row_rotation_violation|grid_rotation_violation|grid_size_violation`.
   - Scene variants: `sequence_row` for the row rule and `numbered_grid` for the two grid rules.
   - Rule policy:
     - `row_rotation_violation` uses a constant-step row over rotations `{0,90,180,270}` with step support `{90,270}`.
     - `grid_rotation_violation` uses one row/column rotation-offset rule over `{0,90,180,270}` with row/column step support `{90,180,270}`.
     - `grid_size_violation` uses one row/column symbolic size-level rule over `{1,2,3,4,5}` with step support `{-1,0,1}` and the all-zero pair disallowed.
   - Answer type: integer box index.
   - Evidence: one-box `bbox_set` for the violating numbered box in final image coordinates.
   - Ambiguity rule: reject any row/grid where another supported rule hypothesis would make a different violating index plausible.
33. **Icons counting singleton type (`task_icons_counting_singleton_type`)**
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

# Scene, Task, And Query Guide

## Purpose
Define how TRACE splits public tasks from reusable visual scenes and internal
query knobs so each dataset slice stays comparable and avoids hidden weighting
bias.

This file owns cross-domain scene/task/query boundary guidance. Detailed active
contracts stay in the relevant `*_TASK_SETUP.md` doc when one exists and should
not be copied into skills or planning notes.

## Core rule
1. **Scene = reusable visual grammar**. A scene fixes the renderer/scaffold and
   the visible object types, but can still expose non-semantic style or sampling
   parameters.
2. **Task = public sampling unit**. A task is unique by the hard task boundary
   in `docs/core/TASK_UNIT_POLICY.md`: scene grammar, primary witness kind,
   visual search pattern, and algorithmic/objective family. Answer/evidence
   type is supporting contract metadata, not enough by itself to force a split
   or merge.
3. **Query = internal reasoning branch**. Query ids cover task-internal
   branches that share the same task contract but need a distinct
   reasoning/rationale template family, such as a different operation,
   predicate, ordering rule, answer transform, or witness role. Query ids are
   not public sampling units.
4. Prefer adding query support inside an existing task only when the same
   primary witness kind, visual search pattern, and algorithmic/objective
   family stay intact. Add a new task when any of those axes changes.
5. Use `query_id` as the canonical metadata field and "query id" as the
   human-facing name. Do not reintroduce `task_variant` as a public concept.

## Geometry scene/task rules
1. `measurement` should use **one primary object per image**.
2. Multi-object value-query geometry tasks belong under `comparison` (separate from single-object `measurement`).
3. Multi-object geometry class-membership tasks belong under `counting`; scenes should label whole objects and count how many match one requested class.
4. `analytical` should use panel-label or property-label scenes where the answer is selected from visible candidate panels and grounded by the selected panel evidence.
5. `comparison` should enforce exactly one winner by construction and use one reusable winner-gap policy (`gap_norm >= 0.20` plus optional task-level absolute floors) so scenes stay readable without hand-tuned per-instance ambiguity checks.
6. Keep active geometry task inventory and scene/query/evidence details in `GEOMETRY_TASK_SETUP.md` rather than restating them in skills or planning notes.

## Icons direction (current)
1. `counting` should use a reference panel plus a scene panel rather than raw icon-name prompts.
2. Reference-scene icon counting tasks should answer with an integer count and use scene-only `bbox_set` evidence in final image coordinates.
3. Orientation-sensitive icon tasks should use the curated asymmetric icon subset (`non_symmetry.txt`) so rotated matches remain visually meaningful.
4. Reference-scene icon counting should sample `target_count` and `distractor_count` from explicit supports, derive `object_count` from the pair, place icons randomly under an explicit overlap cap, and keep per-icon noise on the individual icon instances rather than as a full-image post-process.
5. Icons relation tasks should keep one visibly marked `Anchor` icon in the Scene panel, use a smaller spatial count range than global counting, and ground matches with scene-only `bbox_set` evidence.
6. Active icon outputs record query branches such as reference matching, size relation, anchor direction, strip axis, mirror signature, and fixed pattern queries as `query_id`.
7. Keep active icon task inventory, scene/query/evidence details, and asset-manifest policy in `ICON_TASK_SETUP.md` rather than restating them in skills or cross-domain notes.

## Illustrations direction (current)
1. Illustrations use synthetic drawings of recognizable objects, not natural images or generic icon silhouettes.
2. The shared object library should own object geometry, style variants, semantic part metadata, and part bbox projection so tasks do not duplicate object drawers.
3. `mixed_object_canvas` renders non-overlapping animals, vehicles, plants, and household/tool objects on simple non-semantic backgrounds.
4. `environment_object_canvas` renders habitat-aware foreground objects around curved roads/rivers, bridges/crosswalks, optional skylines, and non-counted sky décor.
5. Visible-part counting uses `integer` answers and `bbox_set` evidence with one final-image pixel bbox per counted part.
6. Environment side counting uses `integer` answers and `bbox_set` evidence with one final-image pixel bbox per counted foreground object.
7. Future illustration tasks should reuse the same object/part/feature records for object-type counts, part-presence counts, spatial relation counts, occlusion-visible counts, and paired-panel change reasoning.
8. Keep active illustrations task inventory and renderer policy in `ILLUSTRATIONS_TASK_SETUP.md`.

## Cell-Board Direction
1. Cell-board puzzle tasks should use one board per image and keep public evidence grounded in image pixel points at tile centers, with board coordinates retained only in private trace metadata.
2. Current cell-board scene geometry uses `rectangular_tiling`; square tiles are one sampled aspect-ratio case, not a separate tiling family.
3. Private canonical tile coordinates are zero-based `(row, col)` with top-left origin.
4. New cell-board tasks should prefer public pixel evidence (`point_set`, `point_sequence`) and keep grid coordinates as private verifier metadata.
5. See `PUZZLE_TASK_SETUP.md` for the concrete `puzzles/cell_board` board-geometry, metadata, and evidence contract.
6. Reachability-style cell-board tasks should treat black obstacle cells and marked start cells as semantic board roles, not as generic query colors.

## Charts Direction (Current)
1. Charts uses the public taxonomy `domain -> scene_id -> task_id`; `task_id` is the sampling unit.
2. Semantic branches are recorded as `query_id` and trace params.
3. Visual chart type, table style, palette, background, axis orientation, and mirror directions remain internal scene/query/render params unless they change the reasoning or evidence contract.
4. Detailed active chart scene counts live in `docs/ACTIVE_TASK_INVENTORY.md`, per-task docs, and `trace/core/taxonomy.py`; do not duplicate the full scene inventory here.
5. `table` tasks are chart tasks with public IDs prefixed `task_charts__table__`.

## Graph direction (current)
1. Graph tasks use one simple node-link graph per image in v0; keep graphs unweighted by default, and make directionality or edge weights explicit only when the task semantics truly require them.
2. `task_group` should encode the reasoning family (for example `counting`, `relation`, `path`), while graph layout stays a visual `scene_variant` or trace-only sampling axis inside a task.
3. Node labels are prompt-facing identities; use pixel `point_set` evidence when the witness unit is one or more node centers, and use `bbox_set` when the answer is a visible node label or label box.
4. Layout variation should change readability only, not semantics; graph answers must come from adjacency/topology rather than absolute node position.
5. Keep graph sampling variation split between topology families and layout families so graph semantics remain stable while scenes still vary visually.
6. If a graph task supports directed variants, make the prompt wording, trace metadata, and rendered arrowheads explicit; do not reuse plain `degree` wording for directed in-/out-degree queries.
7. Named-node graph prompts must use canonical visible labels as identities; when `label_variant=named`, prompt-facing labels are quoted, for example node `"Abby"`.
8. Graph background/panel style variation is non-semantic and must stay limited to light canvas/panel tint and border color; do not use it to move graph geometry or change node, edge, arrow, label, or weight-label readability parameters.
9. Structure-option matching uses `task_graph__graph_options__structure_match_label` on scene `graph_options`; it records `query_id=same_structure_label|contained_subgraph_label`, samples `edge_mode=undirected|directed`, and uses one selected-option panel `bbox_set` as evidence.
10. Binary-tree tasks use scene `binary_tree`, whose top-down layout is semantic: left/right child positions define traversal order. Count and node-label relation queries use node `bbox_set`; traversal and search-tree operation queries use ordered node `bbox_sequence`.

## Pages GUI-Like Direction (Current)
1. GUI-like pages tasks use synthetic web and desktop application screens with visible candidate labels for control grounding.
2. `task_group=counting` covers multi-control GUI count tasks where evidence is the full bbox set of counted controls.
3. `task_pages__control_board__filter_count` uses `integer` answers for grouped control-state counts and sectioned table-row filters.
4. Its five `query_id` values are `disabled_controls_in_group_count`, `selected_enabled_controls_in_group_count`, `selected_rows_with_status_count`, `enabled_action_for_type_count`, and `value_threshold_in_group_count`.
5. `task_group=relation` covers choosing controls associated with visible context regions.
6. `task_pages__navigation_flow__navigation_path_target_label` uses `option_letter` answers for menu-path and ribbon-group target variants.
7. `task_pages__command_matrix__command_intent_target_label` uses `option_letter` answers for command-intent and dual-guide command variants across create/insert, select/choose, view/toggle, edit/transform, and format/style intent categories; prompts use short cue phrases that must be mapped through shuffled guides to object rows and coded action headers.
8. `task_pages__workspace__professional_target_label` uses `option_letter` answers and ordered guide-card/context-row/coded-header/control evidence for toolbar-palette, property-panel, canvas-workspace, IDE, and file-dialog target variants.
9. `task_pages__web_action__web_action_target_label` uses `option_letter` answers and ordered instruction-banner/context/control evidence for click-target, type-field, and select-option web action variants.
10. Candidate-label badge bboxes and table cell bboxes are trace metadata; prompt-facing evidence stays on the context/path/header/instruction bboxes and actionable control bbox.
11. Keep app-family and visual-style axes non-semantic: they should change screen context and chrome only, never the command/control mapping.
12. GUI style/background variation is color-only and may affect light canvas tint, chrome, panels, rows, controls, and badges; it must not change target geometry, badge placement/size, font sizes, row heights, control spacing, or evidence bboxes.
13. Keep the active pages contract in `PAGES_TASK_SETUP.md` rather than duplicating every command pool in cross-domain notes.

## Pages Structured Artifact Direction (Current)
1. Pages covers page-like structured artifacts, diagrams, static maps, schedules, timelines, schemas, and GUI/web screens.
2. Concrete page query branches are recorded as `query_id`.
3. The active structured-artifact families are `arithmetic`, `cross_form`, `cycle`, `hierarchy`, `infographic`, and `map`.
4. `task_pages__form_section__section_expression_value` uses `query_id` values `sum_two_amounts_in_section`, `difference_two_amounts_in_section`, and `sum_minus_amount_in_section`, with visual `scene_variant` values `form_sheet`, `invoice_sheet`, and `receipt_sheet`.
5. `task_pages__paired_forms__reconciliation_value` uses `query_id` values `total_amount_delta`, `shortfall_minus_overage_value`, and `sum_absolute_quantity_differences`, with visual `scene_variant` value `purchase_receipt_pair`; receiving-slip rows are shuffled relative to purchase-order rows.
6. `task_pages__cycle__offset_stage_label` uses `query_id` values `after_offset_stage_label|before_offset_stage_label`, query relationship values `after|before`, visual `scene_variant` value `cycle_ring`, and `cycle_direction` values `clockwise|counterclockwise`.
7. `task_pages__hierarchy__tree_count` uses `query_id` values `subtree_descendant_count`, `subtree_leaf_count`, and `path_length_between_two_nodes`, with visual `scene_variant` value `rooted_tree`.
8. `task_pages__map__navigation_label` uses `query_id` values `destination_after_directions` and `landmark_after_route_step`, with visual `scene_variant` value `campus_map`.
9. `task_pages__infographic__metric_arithmetic_value`, `task_pages__infographic__section_ranked_total_label`, `task_pages__infographic__filtered_metric_total_value`, and `task_pages__infographic__column_profile_comparison_value` share `scene_id=infographic` and use label/value bboxes from the metric cards used in the answer.
10. Prompt-facing arithmetic evidence should stay as ordered operand value boxes only.
11. Prompt-facing cross-form evidence should stay on item-code and numeric cells used for matching and computation.
12. Prompt-facing cycle evidence should stay as one target-stage `bbox_set`.
13. Prompt-facing hierarchy evidence should stay on node boxes: unordered counted-node sets for subtree counting and ordered node paths for path length.
14. Prompt-facing map evidence should stay on route landmark boxes.
13. Page text generation should stay typed and short; prefer IDs, dates, amounts, names, and contact fields over long prose in page-like families.

## Puzzles direction (current)
1. Puzzles use `task_group` for hidden-rule reasoning families such as `logic`, `probability`, `spatial`, `topology`, and `visual`; avoid splitting families by one-off visual templates when the reasoning contract is still the same.
1. Active puzzle tasks inherit shared render-only treatment and palette primitives from `configs/domains/puzzles/base.yaml` and the shared puzzle/game visual-style helpers; this must not change maze topology, cube geometry, fold/overlay coordinates, option semantics, or evidence semantics.
1. Automaton puzzles use scenes `agent_automaton`, `life_automaton`, and `turing_tape`. Active tasks are `task_puzzles__agent_automaton__agent_final_pose_label`, `task_puzzles__agent_automaton__agent_cell_flip_count`, `task_puzzles__life_automaton__life_future_grid_label`, `task_puzzles__life_automaton__life_population_count`, and `task_puzzles__turing_tape__turing_written_symbol_count`; each records the concrete branch in `query_id`.
2. Logic grid completion is split into `task_puzzles__logic_grid__grid_uniqueness_completion_label` and `task_puzzles__logic_grid__grid_king_non_touch_label`. The uniqueness task records `query_id=grid_uniqueness_completion` with `uniqueness_query=axis_uniqueness|row_and_column_uniqueness` and `uniqueness_axis=row|column` for axis uniqueness, while king non-touch records `query_id=king_non_touch`.
3. The split logic grid tasks use visual `scene_variant` values `logic_strip`, `logic_card`, and `logic_outline`.
4. Raven matrix logic is split into `task_puzzles__raven_matrix__raven_count_progression_label`, `task_puzzles__raven_matrix__raven_spatial_transform_label`, `task_puzzles__raven_matrix__raven_set_operation_label`, `task_puzzles__raven_matrix__raven_analogical_transform_label`, and `task_puzzles__raven_matrix__raven_position_progression_label`. Each records its fixed `query_id`.
5. The split Raven tasks use visual `scene_variant` values `raven_strip`, `raven_card`, and `raven_outline`.
5. Nonogram logic is split into `task_puzzles__nonogram__nonogram_line_completion_label` and `task_puzzles__nonogram__nonogram_candidate_solution_label`. Each uses scene `nonogram` and fixed `query_id=line_completion_label|candidate_solution_label`.
5. The split nonogram tasks use visual `scene_variant` values `nonogram_classic`, `nonogram_card`, and `nonogram_blueprint`; evidence is projected from marked row/option bboxes or clue-rail/candidate bboxes depending on the query.
5. Arithmetic-constraint logic uses `task_puzzles__arithmetic_constraint__arithmetic_constraint_value`, `task_puzzles__arithmetic_constraint__cryptarithm_digit_value`, `task_puzzles__arithmetic_constraint__number_wall_value`, and `task_puzzles__arithmetic_constraint__operator_grid_value`; each records the internal `query_id` and uses prompt-facing `bbox_set` evidence on the puzzle panel plus marked targets.
5. Tents logic is split into `task_puzzles__tents__tents_missing_tent_cell_label` and `task_puzzles__tents__tents_valid_candidate_count`. Each uses scene `tents` and fixed `query_id=missing_tent_cell_label|valid_candidate_count`; evidence is projected from candidate-cell, marked-tree, and clue boxes. The scene also records render-only `palette_variant=garden|autumn|lake|violet|slate`.
5. Dice probability uses `task_puzzles__dice_probability__dice_single_event_value`, `task_puzzles__dice_probability__dice_pair_event_value`, and `task_puzzles__dice_probability__dice_conditional_event_value` on scene `dice_probability`. The sampled visible-top event branch is recorded as `query_id`, answers are reduced fraction strings, and prompt-facing evidence is tray-level `bbox_set` grounding.
5. The dice probability tasks use visual `scene_variant` values `dice_tray_clean`, `dice_tray_felt`, and `dice_tray_notebook`; probability is over uniformly selecting from the shown dice, never over rolling unseen dice.
6. Spinner probability uses `task_puzzles__spinner_probability__spinner_compound_event_value` and `task_puzzles__spinner_probability__spinner_pair_event_value` on scene `spinner_probability`. The sampled event branch is recorded as `query_id`, answers are reduced fraction strings, and prompt-facing evidence is panel-level `bbox_set` grounding.
6. The spinner probability tasks use visual `scene_variant` values `spinner_clean`, `spinner_card`, and `spinner_notebook`; sectors are equal probability by construction. Single-spinner scenes show color plus shape markers, while pair-spinner scenes are color-only to keep product-space probability readable.
6. The active logic-board grammar uses one square board with one explicit `?` cell and exactly six labeled image options.
7. The explicit adjacency logic variant must state whether matching symbols are forbidden by edge only or by edge and corner; the current `king_non_touch` rule forbids both and uses the full six-shape option set so the answer stays unique from the visible neighborhood.
8. Prompt-facing logic evidence should stay as one-box `bbox_set` grounding on the winning option panel; keep the query interaction stable as option selection even when later logic families vary the rule structure.
9. Spatial transform result tasks are split into `task_puzzles__paper_fold__paper_fold_result_label`, `task_puzzles__paper_fold_cut__paper_fold_cut_result_label`, and `task_puzzles__overlay__overlay_result_label`. Each records `query_id=paper_fold_result|paper_fold_cut_result|overlay_result`; paper-fold-cut samples `fold_count=1|2`, and single-fold branches sample `fold_axis=vertical|horizontal`.
10. Spatial transform result tasks use visual `scene_variant` values `fold_strip|fold_card|fold_outline` for fold branches and `overlay_strip|overlay_card|overlay_outline` for overlay branches.
11. The active spatial transform grammar covers marked fold-result, fold-cut unfolded-result, and transparent-sheet overlay option selection under one result-option evidence contract.
12. Cube/voxel spatial reasoning uses `scene_id=voxel_cube` and is split into `task_puzzles__voxel_cube__cube_count`, `task_puzzles__voxel_cube__cube_structure_change_count`, `task_puzzles__voxel_cube__cube_painted_face_count`, `task_puzzles__voxel_cube__cube_visible_projection_count`, `task_puzzles__voxel_cube__cube_projection_match_label`, and `task_puzzles__voxel_cube__cube_projection_consistency_label`. Each records `query_id=cube_count|cube_structure_change_count|painted_face_count|visible_cube_count|projection_match_label|projection_consistency_label`.
13. The split cube tasks use visual `scene_variant` values `stack_strip`, `stack_card`, and `stack_outline` for isometric branches plus `cube_stack` for the projection branch.
14. The active cube-structure grammar covers fixed-view wall-like isometric stack counts, side-by-side change counts, painted-face counts, orthographic visible-cell counts, projection matching, and projection consistency as separate task units.
15. Sliding-block spatial reasoning uses `task_puzzles__sliding_block__sliding_block_blocker_count` and `task_puzzles__sliding_block__sliding_block_move_result_label` on scene `sliding_block`. The fixed branch is recorded as `query_id=blocker_count|move_result_label`, and prompt-facing evidence is `bbox_set` grounding over path blockers or moved-block originals plus the correct result option panel.
16. The sliding-block tasks use visual `scene_variant` values `wooden_tray`, `cool_grid`, and `paper_board`, with `exit_side=right|left|top|bottom`.
24. Polyomino spatial reasoning uses `task_puzzles__polyomino_missing__polyomino_missing_region_piece_label` for static missing-region and rectangle-complement piece selection. The task records `query_id=marked_region_piece_label|rectangle_complement_piece`.
25. The polyomino missing-region task uses visual `scene_variant` values `polyomino_strip`, `polyomino_card`, and `polyomino_outline`; rectangle-complement queries sample `matching_policy=exact_orientation|rotation_reflection_allowed` as a traced parameter.
26. Tetris-like line completion and general buildable-target assembly are intentionally not active puzzle tasks; game-rule row-completion should live under the games Tetris scene.
27. Tangram-style spatial reasoning is split into `task_puzzles__tangram__tangram_missing_piece_label` and `task_puzzles__tangram__tangram_contact_count`. Each records the fixed `query_id` and keeps polygon-piece matching and edge-contact counting separate from cell-based polyomino reasoning.
28. Illustration-style jigsaw and missing-patch image reconstruction belongs under the `illustrations` domain, not the puzzles spatial family.
29. Prompt-facing spatial evidence should stay as one-box `bbox_set` grounding on the winning option image/panel for fold-result, fold-cut, and overlay tasks; as ordered option-plus-target-region boxes for applicable polyomino and tangram missing-piece variants; as counted-piece boxes for tangram contact counts, with marked piece boxes first and every returned box counted; as the ordered two-box structure pair `[original left, remaining right]` for cube-structure comparison tasks; or as the filled query-grid cell `bbox_set` for solid-view projection counts. Do not invent fake per-missing-cube or explanatory projection bboxes.
31. `task_puzzles__cyclic_order__cyclic_order_equivalent_label` exposes the cyclic-order query contract with `query_id=cyclic_order_equivalent_label`.
32. The cyclic-order tasks sample `token_render_style=colored_beads|shape_tokens|colored_shape_tokens|outline_shape_tokens|symbol_badges` and `loop_path_style=ellipse|rounded_rect|polygon_loop|wavy_loop|beaded_string` as non-semantic visual axes, and use visual `scene_variant` values `necklace_board`, `charm_card_grid`, `route_loop_diagram`, and `token_ring_outline`.
33. String-topology component counting is exposed as `task_puzzles__string_topology__string_component_count`; it records the sampled predicate as `query_id=open_rope_count|closed_loop_count|knotted_component_count`.
34. The string-topology task uses visual `scene_variant` values `string_strip`, `string_card`, and `string_outline`.
35. The active topology cyclic-order grammar uses one reference loop above exactly `6` labeled option loops with exactly one equivalent option; equivalent-label queries use `4..5` tokens. Color-bearing token styles should use Lab-separated colors, prompt-facing evidence should be the valid option-image bbox, and the prompt must explicitly say that flipping/reflection is not allowed.
36. The active string-topology grammar uses one diagram of separate open strings, closed rings, and knots; it samples target answer count `3..10` and distractor count `3..10` independently, keeps total visible groups at `6..20`, uses knotted closed loops as open-rope distractors, and uses component bboxes as prompt-facing evidence for open/closed/knotted component counts.
37. Color-gradient visual reasoning uses `task_puzzles__color_gradient__color_gradient_violation_cell_label` and `task_puzzles__color_gradient__color_gradient_completion_label` on scene `color_gradient`. Violation uses fixed `query_id=color_gradient_violation_cell_label` with one-box swatch-cell evidence, while completion uses fixed `query_id=linear_gradient_completion_label` with blank-swatch plus correct-option evidence.
37. Maze topology is split into `task_puzzles__maze__exit_reachability_label` and `task_puzzles__maze__reachable_exit_count`; the label query uses `target_reachability=reachable|unreachable`.
38. Pipe-flow repair uses `task_puzzles__pipe_flow__pipe_flow_repair_tile_label` on scene `pipe_flow`. It uses fixed `query_id=flow_repair_tile_label` and option-plus-gap `bbox_set` evidence for the labeled 2x2 option that can be rotated to fill the black missing region and restore connectivity from the green start marker to the red triangular finish flag. Offshoot branches are attached to the main path and terminate on a grid side.
38. The maze tasks use visual `scene_variant` values `classic_wall_maze`, `paper_labyrinth_maze`, and `block_wall_maze`.
39. The active maze grammar shows a START cell inside an orthogonal wall maze with labeled boundary exits; it samples `6..8` rows, `7..10` columns, and `4..6` exits, constructs reachability from metadata rather than pixels, and projects target or reachable exit label+doorway bboxes.
40. Voxel-ladder topology uses scene `voxel_ladder` with `task_puzzles__voxel_ladder__voxel_ladder_route_label` and `task_puzzles__voxel_ladder__voxel_ladder_route_count`; both record route/count branches in `query_id`.
41. The voxel-ladder grammar shows an isometric cube maze with blue START, red GOAL, colored checkpoints sampled from the canonical TRACE named-color palette, and black ladders. Movement is adjacent same-height cube tops plus ladders for height changes, with prompt-facing `bbox_set` evidence projected from route checkpoints, unreachable checkpoints, reachable checkpoint sets, or route ladders.

## Time Artifact Placement
1. Time-artifact scenes use the same public `domain -> scene_id -> task_id` taxonomy as the rest of TRACE.
2. Clock scenes live in `puzzles`: `analog_clock` and `clock_collection`.
3. Calendar, schedule, and timeline scenes live in `pages`: `calendar`, `schedule`, and `timeline`.
4. Active task ids are `task_pages__calendar__marked_day_class_count`, `task_pages__calendar__weekday_occurrence_date`, `task_puzzles__clock_collection__compare`, `task_puzzles__analog_clock__offset_readout`, `task_pages__schedule__longer_than_reference_count`, `task_pages__schedule__maximum_non_overlapping_count`, `task_pages__schedule__overlap_count`, and `task_pages__timeline__interval_membership_count`.
5. Mirror/query knobs go in `query_id`.
6. Split task ids are used when the reasoning or evidence contract differs: clock readout vs multi-clock comparison, calendar lookup vs marked-date count, and the three schedule reasoning contracts.
7. Mirror/query knobs remain internal: clock compare `earliest|latest`, clock readout `before|after`, calendar marked class `weekend|weekday`, and timeline interval relation `between|outside`.
8. The active time-artifact tasks use visual `scene_variant` values `classic`, `minimal`, and `outline`, except the milestone timeline, which uses `classic|roadmap|minimal`.
9. Non-semantic axes `style_variant=studio|accented|marker`, `accent_color_name`, background style, and mild post-image noise must never change the prompt contract.
10. Evidence stays local to the queried witness: clock hands, winning clock faces, date cells, schedule event blocks, or timeline event cards.

## Physics direction (current)
1. Physics should stay diagram-first: the image should contain the operative values, directions, or placements needed to solve the task.
2. Public task ids are default sampling units. `scene_variant` names the scaffold, and `query_id` names the narrowed query contract inside a shared renderer.
3. The active physics families are `mechanics`, `circuits`, `electrostatics`, `magnetism`, `fluids`, `optics`, `thermodynamics`, and `waves`.
4. `task_physics__pulley__pulley_mechanical_advantage`
   - uses scene variants `open_block|compact_block|tall_block`
   - uses `query_id=force_relation` with `solve_for=effort_force|load_force`
   - keeps integer answers with unordered `bbox_set` evidence over the full supporting strands plus the marked force label
   - keeps the pulley arithmetic tied to ideal mechanical advantage from full connecting strands, while cut strands act only as visual distractors
5. Lever-balance tasks:
   - active ids are `task_physics__lever__side_torque_value` and `task_physics__lever__missing_weight_balance_value`
   - uses scene variants `center_fulcrum|offset_fulcrum|textured_beam`
   - uses `query_id=side_torque|missing_weight_to_balance`, with `torque_side=left|right` as an internal side mirror for side torque
   - keeps integer answers with unordered `bbox_set` evidence over either the relevant side’s weight blocks (`side_torque`) or the marked `?` weight block (`missing_weight_to_balance`)
   - calibrates the public missing-weight task on `textured_beam` only, with answer support `1..6` and lower side clutter
   - samples one non-semantic `accent_color_name` palette for the beam / fulcrum / shown weights while leaving the red `?` weight semantics unchanged
6. Circuit-resistance tasks:
   - active ids are `task_physics__resistor__total_resistance_value` and `task_physics__paired_resistor__missing_resistor_value`
   - uses scene variants `parallel|simple_series_parallel`
   - uses `query_id=total_resistance|missing_resistor_value`
   - keeps integer answers with unordered `bbox_set` evidence over either the full asked resistor set (`total_resistance`) or the marked red `?` resistor in the left circuit (`missing_resistor_value`)
   - requires every scene to contain at least one parallel bank; the single-circuit readout uses `3..4` parallel branches or `4..5` total resistors, while the paired missing-resistor variant uses smaller side-by-side circuits with equal total resistance
   - when `scene_variant` is not fixed for `total_resistance`, samples the target answer from the query-level feasible union support first and then chooses a compatible scene family for that answer
   - samples one non-semantic `accent_color_name` palette for the wires, terminals, and resistor boxes
7. Electrostatics field-map tasks:
   - active ids are `task_physics__electrostatic_field__field_direction_choice`, `task_physics__electrostatic_field__zero_field_point_label`, and `task_physics__electrostatic_field__potential_value`
   - uses scene variants `clean_grid|paper_grid|dense_grid`
   - uses `query_id=field_direction_choice|zero_field_point_label|potential_value`, with `direction_mode=electric_field_direction|force_on_positive_charge|force_on_negative_charge` as an internal axis for direction-choice queries
   - keeps option-letter or signed-integer answers with one-box `bbox_set` evidence over the selected arrow, selected point, or compact potential witness region
   - keeps force-on-negative-charge and similar sign/mode changes inside one public direction task rather than splitting them into separate task ids
8. Magnetism force-field tasks:
   - active id is `task_physics__magnetic_force__force_direction_choice`
   - uses scene variants `clean_panel|field_grid|lab_card`
   - uses `query_id=force_direction_choice`
   - keeps `field_orientation=out_of_page|into_page`, velocity direction, charge sign, and candidate-arrow placement as internal axes
   - calibrates the public task on `field_grid`, with correct-answer letters `B|C|D|E|G|H` while all eight options remain visible
   - keeps option-letter answers with one-box `bbox_set` evidence over the selected candidate force arrow
9. Waves interference-tank tasks:
   - active ids are `task_physics__wave_interference__interference_point_choice` and `task_physics__wave_interference__path_difference_value`
   - uses scene variants `clean_tank|grid_tank|lab_sheet`
   - uses `query_id=interference_point_choice|path_difference_value`
   - keeps `phase_relation=in_phase|opposite_phase`, `target_condition=constructive|destructive`, and candidate-point placement as internal axes
   - uses five candidate labels `A-E` for point choice and path-difference answers `1..4` for the calibrated public mix
   - keeps option-letter or integer `lambda/2` step-count answers with one-box `bbox_set` evidence over the selected candidate point or labeled source-to-`P` path witness
10. Optics ray-trace tasks:
   - active ids are `task_physics__ray_optics__ray_bounce_count` and `task_physics__ray_optics__ray_target_hit_count`
   - uses scene variants `single_mirror|double_mirror|triple_mirror|quad_mirror|five_mirror`
   - uses `query_id=bounce_count|target_hit_count`
   - keeps integer answers with unordered pixel `point_set` evidence over either bounce-point centers or hit target-point centers
   - shows only the initial ray direction in the prompt image, keeps the solved full path in trace/debug artifacts, ties mirror count directly to `scene_variant`, and reserves `five_mirror` for calibrated `bounce_count` while the smaller mirror-count scenes feed `target_hit_count`
   - uses large unlabeled target dots for `target_hit_count` with calibrated answers `1..5`, bounce-count answers `1..5`, no separate bounce circles for `bounce_count`, and one non-semantic `accent_color_name` palette for the board and mirrors while the ray keeps a fixed warm contrast color
11. Spring-extension tasks:
   - active ids are `task_physics__spring__spring_missing_value` and `task_physics__spring__spring_extension_difference`
   - uses scene variants `paired_springs|staggered_springs|textured_spring`
   - uses `query_id=missing_value|extension_difference`, with `solve_for=weight|extension` as an internal inverse axis for missing-value queries
   - keeps integer answers with unordered `bbox_set` evidence over either the two compared value-labeled extension markers (`extension_difference`) or the reference/query weight-marker witness set for the two missing-value variants
   - keeps the two springs explicitly identical within each instance and encodes the proportionality only through the shown weight/extension pair, not through a printed formula
   - calibrates `extension_difference` with scale factor `2` and answer support `2|4|8|10|12`
   - uses one non-semantic `accent_color_name` palette for the card chrome / support bars / springs while the missing-value placeholders remain red
12. Hydraulic piston task:
   - active id is `task_physics__hydraulic__hydraulic_missing_value`
   - uses scene variants `wide_bench|compact_frame|tall_columns`
   - uses `query_id=missing_output_force|missing_input_force|missing_piston_area`
   - keeps integer answers with unordered `bbox_set` evidence over all six visible force and piston-area labels in the connected three-piston system, including the red `?` missing label
   - ties reasoning to Pascal's law, `F_input / A_input = F_middle / A_middle = F_output / A_output`, with integer mechanical-advantage constructions
   - samples one non-semantic `accent_color_name` palette for the chambers, fluid, and pistons while the missing-value placeholder remains red
13. Thermodynamics PV-diagram tasks:
   - active ids are `task_physics__pv_diagram__pv_work_value` and `task_physics__pv_diagram__pv_process_sign_choice`
   - uses scene variants `clean_grid|paper_grid|bold_grid`
   - uses `query_id=work_value|process_sign_choice`; calibrated `work_value` sampling uses `work_mode=single_process`, while `process_sign_choice` uses `target_sign=positive|negative|zero` as an internal axis
   - keeps signed-integer or option-letter answers with one-box `bbox_set` evidence over the highlighted path/cycle or selected candidate process
14. Active physics tasks inherit shared light background variants `solid_light|cool_light|warm_light|paper_light|mint_light|lavender_light` from `configs/domains/physics/base.yaml`; these are visual-only and must not change coordinates, object positions, measurement grids, or evidence semantics.
15. Early physics tasks should prefer light arithmetic over heavy formula derivations, and prompt-facing evidence should stay on the visible witness objects rather than decorative scene chrome.

## Games Direction (Current)
1. Games use public taxonomy `games -> scene_id -> task_id`.
2. One game scene can contain multiple public tasks when the reasoning algorithm or answer/evidence contract differs.
3. Mirror knobs remain params inside a task: player color, board size, row/column axis, threshold direction, and visual style.
4. Active scenes and narrow default tasks:
   - `2048`: `task_games__2048__move_result_value`, `task_games__2048__best_move_label`
   - `bingo`: `task_games__bingo__completed_line_count`, `task_games__bingo__line_sum_extremum_value`
   - `battleship`: `task_games__battleship__ship_status_count`
   - `bowling`: `task_games__bowling__first_pin_hit_label`, `task_games__bowling__spare_path_label`
   - `brick_breaker`: `task_games__brick_breaker__trajectory_target_label`, `task_games__brick_breaker__hit_row_remaining_count`
   - `bubble_shooter`: `task_games__bubble_shooter__shot_effect_count`, `task_games__bubble_shooter__pop_color_label`
   - `cards`: `task_games__cards__reference_condition_count`, `task_games__cards__exact_triple_count`, `task_games__cards__longest_run_length`, `task_games__cards__blackjack_best_hand_label`, `task_games__cards__poker_best_hand_label`, `task_games__cards__trick_taking_winner_label`
   - `checkers`: `task_games__checkers__move_count`, `task_games__checkers__max_capture_chain_length`
   - `chess`: `task_games__chess__marked_piece_destination_count`, `task_games__chess__player_capture_piece_count`, `task_games__chess__check_attacker_count`, `task_games__chess__king_escape_square_count`
   - `chess_variant`: `task_games__chess_variant__marked_piece_destination_count`
   - `connect_four`: `task_games__connect_four__move_count`
   - `crossing`: `task_games__crossing__safe_route_label`, `task_games__crossing__collision_time_value`, `task_games__crossing__moving_object_count`
   - `darts`: `task_games__darts__total_score_option_label`, `task_games__darts__condition_count`
   - `dominoes`: `task_games__dominoes__property_count`, `task_games__dominoes__two_step_extension_label`
   - `dots_and_boxes`: `task_games__dots_and_boxes__three_sided_box_count`, `task_games__dots_and_boxes__capture_move_count`
   - `go`: `task_games__go__group_liberty_count`, `task_games__go__group_adjacent_enemy_count`
   - `hex`: `task_games__hex__winning_move_cell_label`, `task_games__hex__connection_gap_count`
   - `minesweeper`: `task_games__minesweeper__forced_cell_count`, `task_games__minesweeper__satisfied_clue_count`
   - `minigolf`: `task_games__minigolf__first_obstacle_label`, `task_games__minigolf__shot_path_label`
   - `nine_mens_morris`: `task_games__nine_mens_morris__pieces_in_mill_count`
   - `pacman`: `task_games__pacman__route_pellet_count`, `task_games__pacman__next_item_label`
   - `platformer`: `task_games__platformer__jump_landing_label`, `task_games__platformer__collectible_count`
   - `pool`: `task_games__pool__pottable_ball_count`, `task_games__pool__blocking_ball_count`
   - `reversi`: `task_games__reversi__legal_destination_count`, `task_games__reversi__marked_move_flip_count`
   - `snake`: `task_games__snake__safe_direction_count`, `task_games__snake__path_outcome_option_label`
   - `solitaire`: `task_games__solitaire__move_legality_label`, `task_games__solitaire__foundation_ready_count`, `task_games__solitaire__tableau_sequence_count`
   - `space_shooter`: `task_games__space_shooter__clear_shot_count`, `task_games__space_shooter__projectile_intercept_count`, `task_games__space_shooter__highest_threat_label`, `task_games__space_shooter__safe_lane_count`
   - `sudoku`: `task_games__sudoku__marked_cell_value`, `task_games__sudoku__marked_cell_candidate_count`, `task_games__sudoku__unit_missing_digits_count`, `task_games__sudoku__repeated_digit_count`
   - `tetris`: `task_games__tetris__line_clear_count`, `task_games__tetris__drop_result_label`
   - `ultimate_tictactoe`: `task_games__ultimate_tictactoe__small_board_status_count`, `task_games__ultimate_tictactoe__local_tactic_label`
5. Active games tasks use integer or label-string answers and local pixel-grounded `bbox_set` evidence over the visible witness cells, pieces, cards, dominoes, darts, bricks, catch lanes, crossing start pads/routes/vehicles, hex cells, bubbles, color options, or intersections.
6. Shared game renderers and rules should stay under `trace/tasks/games/shared/`; fixed-query public task wrappers should use `trace/tasks/games/shared/fixed_query_task.py`, which delegates shared metadata rewriting to `trace/tasks/shared/fixed_query.py`, instead of duplicating renderer or wrapper logic.

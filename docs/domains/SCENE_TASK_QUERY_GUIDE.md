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
2. **Task = public sampling unit**. A task is unique by one stable scene
   contract plus one stable task contract. The task contract fields are
   `answer_schema`, `annotation_schema`, and `program_schema`; see
   `docs/core/TASK_UNIT_POLICY.md` and
   `docs/core/TRACE_TAXONOMY_DESIGN.md`.
   The program schema must be concrete enough to name the candidate set,
   operand roles, derived computation, final operator, output binding, and
   annotation role template; generic placeholders are draft-only.
3. **Query = internal parameterized branch**. Query ids cover task-internal
   branches that share the same scene contract and task contract. Query ids are
   not public sampling units and must not hide answer-schema, annotation-schema,
   program-schema, or query-facing view-contract changes.
4. Prefer adding query support inside an existing task only when the same scene
   contract and task contract stay intact. Add a new task when any task
   contract field changes, or when one public task would otherwise mix
   materially different query-facing views.
5. Use `query_id` as the canonical metadata field and "query id" as the
   human-facing name.

## Cross-Domain Annotation Shape Policy
1. Prompt-facing annotation should mark the minimal visible object or primitive a
   human would circle/highlight before solving. It should not enumerate every
   graphical primitive used in a derivation.
2. Choose the lowest-burden image annotation that still unambiguously localizes
   the witness:
   - use `point_set` for compact marker-like objects such as pucks, dots,
     graph nodes, charge markers, and point candidates;
   - use `bbox_set` for extended regions, panels, cards, object bodies,
     closed shapes, shaded areas, and text/readout units when the text/readout
     itself is the queried object;
   - use `point_pair_set` or `point_sequence` for line-like witnesses such as
     edges, rays, paths, routes, and ordered construction segments.
3. Use keyed annotation when role identity is necessary for verification or
   prompt clarity, and prefer keyed annotation whenever an unordered set would
   make the requested witnesses ambiguous. The active global homogeneous names
   are `keyed_point_map`, `keyed_point_set_map`, `keyed_bbox_map`, and
   `keyed_bbox_set_map`; do not create domain-specific keyed names. Prefer a keyed map whenever the model must bind specific
   regions or points to their semantic roles, such as `outer_shape` versus
   `shaded_region`, `source_panel` versus `target_panel`,
   `reference_item` versus `candidate_item`, or input versus output
   measurements. The model-facing annotation value is the inner dictionary,
   for example `{"A": [123, 245], "B": [310, 240]}` or
   `{"A": [[123, 245], [140, 245]], "B": [[310, 240]]}` for keyed set maps.
   Avoid mixed point/box annotation unless a task genuinely cannot be redesigned
   around one geometry type.
4. Use unordered set annotation (`bbox_set`, `point_set`, `point_pair_set`) when
   witness identity and order do not matter. This is usually correct for
   counting tasks where annotation cardinality is the answer, and for
   homogeneous support sets where any permutation has the same meaning. Do not
   use an unordered set for fixed-role witnesses merely because all witnesses
   share one geometry type.
5. Numeric labels, coordinate labels, values, and measurement text should
   usually stay as visible annotations plus trace/render metadata, not
   standalone public annotation. Expose them as annotation only when the task is
   explicitly a text/readout/scale-reading task.
6. Do not use selected answer options as annotation unless the selected option is
   a complete visual option image/panel and the scene also contains the
   source/reference/original image or region that the option matches, completes,
   transforms from, or belongs to. In that exception, the option image/panel
   itself may be annotation, and the source/reference region should also be
   grounded when the task contract needs it. Do not use option bboxes for
   ordinary MCQ choices, numeric/text answer labels, or lettered candidate
   objects; ground the underlying source/candidate objects or primitives
   instead.
7. Annotation hints should clearly name the witness category, but they must not
   leak answer cardinality. For counting tasks, say to return annotation for the
   matching/counted objects rather than stating a fixed number of boxes or
   points.
8. Model-facing annotation-format text must be positive-only: state the requested
   witness category/shape and coordinate format, not exclusions or examples of
   things to omit.
9. Semantic visual markers are part of the scene contract when the prompt uses
   them to identify a target, reference, selected option cue, highlighted
   region, route, or marked object. Such markers must be resolved against the
   actual rendered surface and recorded through the shared marker-legibility
   path; they are not ordinary nonsemantic palette choices. Prompt-facing
   annotation should still follow the annotation-shape policy above and need not
   expose marker metadata directly.

## Geometry scene/task rules
1. `measurement` should use **one primary object per image**.
2. Multi-object value-query geometry tasks belong under `comparison` (separate from single-object `measurement`).
3. Multi-object geometry class-membership tasks belong under `counting`; scenes should label whole objects and count how many match one requested class.
4. `analytical` should use panel-label or property-label scenes where the answer is selected from visible candidate panels and grounded by the selected panel annotation.
5. `comparison` should enforce exactly one winner by construction and use one reusable winner-gap policy (`gap_norm >= 0.20` plus optional task-level absolute floors) so scenes stay readable without hand-tuned per-instance ambiguity checks.
6. Keep active geometry task inventory and scene/query/annotation details in `GEOMETRY_TASK_SETUP.md` rather than restating them in skills or planning notes.

## Icons direction (current)
1. `counting` should use a reference panel plus a scene panel rather than raw icon-name prompts.
2. Reference-scene icon counting tasks should answer with an integer count and use scene-only `bbox_set` annotation in final image coordinates.
3. Orientation-sensitive icon tasks should use the curated asymmetric icon subset (`non_symmetry.txt`) so rotated matches remain visually meaningful.
4. Reference-scene icon counting should sample `target_count` and `distractor_count` from explicit supports, derive `object_count` from the pair, place icons randomly under an explicit overlap cap, and keep per-icon noise on the individual icon instances rather than as a full-image post-process.
5. Icons relation tasks should keep one visibly marked `Anchor` icon in the Scene panel, use a smaller spatial count range than global counting, and ground matches with scene-only `bbox_set` annotation.
6. Active icon outputs record query branches such as reference matching, size relation, anchor direction, strip axis, mirror signature, and fixed pattern queries as `query_id`.
7. Keep active icon task inventory, scene/query/annotation details, and asset-manifest policy in `ICON_TASK_SETUP.md` rather than restating them in skills or cross-domain notes.

## Illustrations direction (current)
1. Illustrations use synthetic drawings of recognizable objects, not natural images or generic icon silhouettes.
2. The shared object library should own object geometry, style variants, semantic part metadata, and part bbox projection so tasks do not duplicate object drawers.
3. `mixed_object_canvas` renders non-overlapping animals, vehicles, plants, and household/tool objects on simple non-semantic backgrounds.
4. `environment_object_canvas` renders habitat-aware foreground objects around curved roads/rivers, bridges/crosswalks, optional skylines, and non-counted sky décor.
5. Visible-part counting uses `integer` answers and `bbox_set` annotation with one final-image pixel bbox per counted part.
6. Environment side counting uses `integer` answers and `bbox_set` annotation with one final-image pixel bbox per counted foreground object.
7. Future illustration tasks should reuse the same object/part/feature records for object-type counts, part-presence counts, spatial relation counts, occlusion-visible counts, and paired-panel change reasoning.
8. Keep active illustrations task inventory and renderer policy in `ILLUSTRATIONS_TASK_SETUP.md`.

## Cell-Board Direction
1. Cell-board puzzle tasks should use one board per image and keep public annotation grounded in image pixel points at tile centers, with board coordinates retained only in private trace metadata.
2. Current cell-board scene geometry uses `rectangular_tiling`; square tiles are one sampled aspect-ratio case, not a separate tiling family.
3. Private canonical tile coordinates are zero-based `(row, col)` with top-left origin.
4. New cell-board tasks should prefer public pixel annotation (`point_set`, `point_sequence`) and keep grid coordinates as private verifier metadata.
5. See `PUZZLES_TASK_SETUP.md` for the concrete `puzzles/cell_board` board-geometry, metadata, and annotation contract.
6. Reachability-style cell-board tasks should treat black obstacle cells and marked start cells as semantic board roles, not as generic query colors.

## Charts Direction (Current)
1. Charts uses the public taxonomy `domain -> scene_id -> task_id`; `task_id` is the sampling unit.
2. Semantic branches are recorded as `query_id` and trace params.
3. Visual chart type, table style, palette, background, axis orientation, and mirror directions remain internal scene/query/render params unless they change the reasoning or annotation contract.
4. Detailed active chart scene counts live in `docs/ACTIVE_TASK_INVENTORY.md`, per-task docs, and `trace/core/taxonomy.py`; do not duplicate the full scene inventory here.
5. `table` tasks are chart tasks with public IDs prefixed `task_charts__table__`.

## Graph direction (current)
1. Graph tasks use one simple node-link graph per image in v0; keep graphs unweighted by default, and make directionality or edge weights explicit only when the task semantics truly require them.
2. `task_group` should encode the reasoning family (for example `counting`, `relation`, `path`), while graph layout stays a visual `scene_variant` or trace-only sampling axis inside a task.
3. Node labels are prompt-facing identities; use pixel `point_set` annotation when the witness unit is one or more node centers, and use `bbox_set` when the answer is a visible node label or label box.
4. Layout variation should change readability only, not semantics; graph answers must come from adjacency/topology rather than absolute node position.
5. Keep graph sampling variation split between topology families and layout families so graph semantics remain stable while scenes still vary visually.
6. If a graph task supports directed branches, make the prompt wording, trace metadata, and rendered arrowheads explicit; do not reuse plain `degree` wording for directed in-/out-degree queries.
7. Named-node graph prompts must use canonical visible labels as identities; when `label_variant=named`, prompt-facing labels are quoted, for example node `"Abby"`.
8. Graph background/panel style variation is non-semantic and must stay limited to light canvas/panel tint and border color; do not use it to move graph geometry or change node, edge, arrow, label, or weight-label readability parameters.
9. Structure-option matching uses scene `graph_options` with public tasks `task_graph__graph_options__same_structure_label` and `task_graph__graph_options__contained_subgraph_label`; it samples `edge_mode=undirected|directed` and uses one selected-option panel `bbox_set` as annotation.
10. Binary-tree tasks use scene `binary_tree`, whose top-down layout is semantic: left/right child positions define traversal order. Count queries use node `bbox_set`; node-label relation and heap-property violation queries use role-bound `keyed_bbox_map`; traversal and BST path-operation queries use ordered node `bbox_sequence`.
11. Phylogeny tasks use scene `phylogeny_tree`; leaf labels are semantic taxon identities, internal branch points are unlabeled, and child order/branch length/layout are non-semantic unless selecting among rendered option panels.
12. Pedigree tasks use scene `pedigree_chart`; sex-coded symbols, generation rows, spouse connectors, and descent/sibling connectors are semantic pedigree notation. Relationship and relatedness tasks render answer options in the image and use role-bound `keyed_bbox_map` including the queried people and the selected option bbox. Generic page or organization trees remain `pages/hierarchy`.

## Pages GUI-Like Direction (Current)
1. GUI-like pages tasks use synthetic web and desktop application screens with visible candidate labels for control grounding.
2. `task_group=counting` covers multi-control GUI count tasks where annotation is the full bbox set of counted controls.
3. Control-board counts are split into `task_pages__control_board__disabled_controls_in_group_count` and `task_pages__control_board__selected_enabled_controls_in_group_count`; both use integer answers and full-control `bbox_set` annotation.
4. Record-table row counts are split into `task_pages__record_table__selected_rows_with_status_count`, `task_pages__record_table__enabled_action_for_type_count`, and `task_pages__record_table__value_threshold_in_group_count`; all use integer answers and full-row `bbox_set` annotation.
5. `pages/record_table` is for UI/document record lists with workflow state. Generic analytic row/column/cell table reasoning belongs in `charts/table`.
6. `task_group=relation` covers choosing controls associated with visible context regions.
7. Navigation-flow tasks are split by visual role contract: `task_pages__navigation_flow__menu_path_target_label`, `task_pages__navigation_flow__sidebar_tree_target_label`, and `task_pages__navigation_flow__ribbon_group_command_label`.
8. Command-matrix tasks are split into `task_pages__command_matrix__command_intent_target_label` and `task_pages__command_matrix__dual_guide_command_label`; both use short cue phrases mapped through shuffled guides to object rows and coded action headers.
9. Workspace tasks are split into toolbar-palette, property-panel, canvas-workspace, code-workspace, and file-dialog public task ids, each with query-specific role-keyed cue-card/context-row/code-header/target-control annotation.
10. Web-action tasks are split into `click_target_label`, `type_field_label`, and `select_option_label` public task ids, with role-keyed instruction, cue-guide, context-unit, and target web-control annotation such as `item_card`/`target_button`, `form_section`/`target_input`, or `option_group`/`target_option`.
11. Candidate-label badge bboxes and table cell bboxes are trace metadata; prompt-facing annotation stays on concrete support regions and actionable target units rather than generic placeholders.
12. Keep app-family and visual-style axes non-semantic: they should change screen context and chrome only, never the command/control mapping.
13. GUI style/background variation is color-only and may affect light canvas tint, chrome, panels, rows, controls, and badges; it must not change target geometry, badge placement/size, font sizes, row heights, control spacing, or annotation bboxes.
14. Keep the active pages contract in `PAGES_TASK_SETUP.md` rather than duplicating every command pool in cross-domain notes.

## Pages Structured Artifact Direction (Current)
1. Pages covers page-like structured artifacts, diagrams, static maps, schedules, timelines, schemas, and GUI/web screens.
2. Concrete page query branches are recorded as `query_id`.
3. The active structured-artifact families are `arithmetic`, `concept_map`, `cross_form`, `cycle`, `document_lookup`, `hierarchy`, `infographic`, `map`, `process_flow`, `step_list`, `schedule`, `timeline`, and `schema`.
4. Form-section arithmetic is split into `task_pages__form_section__sum_two_amounts_in_section_value`, `task_pages__form_section__difference_two_amounts_in_section_value`, and `task_pages__form_section__sum_minus_amount_in_section_value`, all with public `scene_id=form_section` and visual `scene_variant` values `form_sheet`, `invoice_sheet`, and `receipt_sheet`.
5. Paired-forms reconciliation is split into `task_pages__paired_forms__total_amount_delta_value`, `task_pages__paired_forms__shortfall_minus_overage_value`, and `task_pages__paired_forms__sum_absolute_quantity_differences_value`; receiving-slip rows are shuffled relative to purchase-order rows, and prompt-facing annotation is the unordered set of full receiving-slip rows whose received quantities differ from the matched ordered quantities.
6. `task_pages__cycle__offset_stage_label` uses `query_id` values `after_offset_stage_label|before_offset_stage_label`, query relationship values `after|before`, visual `scene_variant` value `cycle_ring`, and `cycle_direction` values `clockwise|counterclockwise`.
7. Hierarchy subtree counting is split into `task_pages__hierarchy__subtree_descendant_count` and `task_pages__hierarchy__subtree_leaf_count`, each with counted-node `bbox_set` annotation; `task_pages__hierarchy__path_length_count` uses `query_id=path_length_between_two_nodes` with ordered path-node `bbox_sequence` annotation. All share visual `scene_variant=rooted_tree`.
8. Map navigation is split into `task_pages__map__destination_after_directions_label` and `task_pages__map__landmark_after_route_step_label`, with visual `scene_variant` value `campus_map` and ordered route-landmark `bbox_sequence` annotation.
9. Concept-map count tasks are split into `task_pages__concept_map__branch_child_count` and `task_pages__concept_map__marked_child_count`, both with child-node `bbox_set` annotation; `task_pages__concept_map__ordered_child_label` uses role-keyed parent-branch and answer-child annotation for ranked child lookup.
10. Infographic arithmetic/ranking is split by concrete formula or ranking contract; all infographic tasks share `scene_id=infographic` and use `keyed_bbox_map` annotation over supporting metric-card boxes keyed by visible metric-card labels, with label/value/caption text boxes retained in trace metadata.
11. Step-list tasks are split into `task_pages__step_list__nth_step_title_label`, `task_pages__step_list__nth_step_detail_label`, and `task_pages__step_list__step_after_named_step_label`, with visual `scene_variant` values `vertical_cards|horizontal_cards|two_column_cards` and role-keyed target/source text annotation. It is an ordered instruction-card lookup scene, not a process-flow path scene.
12. Profile-card lookup is split into `task_pages__profile_card_grid__value_for_named_profile_field` and `task_pages__profile_card_grid__profile_for_field_value`, with visual `scene_variant` values `directory_grid|compact_cards` and role-keyed profile-name, field-label, and field-value annotation. It is an entity-card field lookup scene, not a chart/table row-column scene.
13. `task_pages__ranked_list__ordinal_entry_label` keeps `query_id=nth_entry_label|from_end_entry_label`; `task_pages__ranked_list__entry_after_named_entry_label` carries the source-item role. Both use visual `scene_variant` values `two_column_lists|stacked_lists` and role-keyed section/title/item annotation.
14. `task_pages__process_flow__filtered_node_count`, `task_pages__process_flow__condition_path_endpoint_label`, `task_pages__process_flow__all_cross_lane_handoff_count`, and `task_pages__process_flow__lane_filtered_handoff_count` share `scene_id=process_flow`. They use process lanes, status badges, decision labels, and lane handoff semantics rather than graph-theory reachability, degree, or shortest-path semantics. The endpoint-following task uses compact `keyed_bbox_map` annotation to bind path witnesses; handoff-count tasks use `point_pair_set` annotation for counted arrow endpoint pairs.
15. `task_pages__schema__field_role_count` and `task_pages__schema__relationship_count` share `scene_id=schema`. Field-role counts use counted schema-field row `bbox_set` annotation; relationship counts use `point_pair_set` endpoint-pair annotation for counted relationship lines.
16. Prompt-facing arithmetic annotation should stay as operand value boxes only, keyed by operand role when expression order affects the computation.
17. Prompt-facing cross-form annotation should stay on item-code and numeric cells used for matching and computation, with keyed role names that distinguish purchase-order cells from receiving-slip cells.
18. Prompt-facing cycle annotation should stay as one target-stage `bbox_set`.
19. Prompt-facing hierarchy annotation should stay on node boxes: unordered counted-node sets for subtree counting and ordered node-path sequences for path length.
20. Prompt-facing map annotation should stay on ordered route landmark boxes.
21. Prompt-facing step-list/ranked-list annotation should stay on role-keyed section/source text plus exact target answer text. Profile-card annotation should stay on keyed profile-name, field-label, and field-value text.
22. Page text generation should stay typed and short; prefer IDs, dates, amounts, names, and contact fields over long prose in page-like families.

## Puzzles direction (current)
1. Puzzles use `task_group` for hidden-rule reasoning families such as `logic`, `spatial`, `topology`, `visual`, `word`, `counterfactual`, and `cell_board`; avoid splitting families by one-off visual templates when the reasoning contract is still the same.
1. Active puzzle tasks inherit shared render-only treatment and palette primitives from `configs/domains/puzzles/base.yaml` and the shared puzzle/game visual-style helpers; this must not change maze topology, cube geometry, fold/overlay coordinates, option semantics, or annotation semantics.
1. Misc automaton scenes use `agent_automaton`, `life_automaton`, and `turing_tape`. Active tasks are `task_misc__agent_automaton__agent_final_pose_label`, `task_misc__agent_automaton__agent_cell_flip_count`, `task_misc__life_automaton__life_future_grid_label`, `task_misc__life_automaton__life_population_count`, and `task_misc__turing_tape__turing_written_symbol_count`; each records the concrete branch in `query_id`.
2. Logic grid completion is split into `task_puzzles__logic_grid__grid_uniqueness_completion_label` and `task_puzzles__logic_grid__grid_king_non_touch_label`. The uniqueness task records `query_id=grid_uniqueness_completion` with `uniqueness_query=axis_uniqueness|row_and_column_uniqueness` and `uniqueness_axis=row|column` for axis uniqueness, while king non-touch records `query_id=king_non_touch`.
3. The split logic grid tasks use visual `scene_variant` values `logic_strip`, `logic_card`, and `logic_outline`.
4. Raven matrix logic is split into `task_puzzles__raven_matrix__raven_count_progression_label`, `task_puzzles__raven_matrix__raven_spatial_transform_label`, `task_puzzles__raven_matrix__raven_set_operation_label`, `task_puzzles__raven_matrix__raven_analogical_transform_label`, and `task_puzzles__raven_matrix__raven_position_progression_label`. Each records its fixed `query_id`.
5. The split Raven tasks use visual `scene_variant` values `raven_strip`, `raven_card`, and `raven_outline`.
5. Nonogram logic is split into `task_puzzles__nonogram__nonogram_line_completion_label` and `task_puzzles__nonogram__nonogram_candidate_solution_label`. Each uses scene `nonogram` and fixed `query_id=line_completion_label|candidate_solution_label`.
5. The split nonogram tasks use visual `scene_variant` values `nonogram_classic`, `nonogram_card`, and `nonogram_blueprint`; annotation is projected from marked row/option bboxes or clue-rail/candidate bboxes depending on the query.
5. Arithmetic-constraint logic uses `task_puzzles__arithmetic_constraint__consecutive_window_sum_value`, `task_puzzles__arithmetic_constraint__equal_sum_line_constraint_value`, `task_puzzles__arithmetic_constraint__paired_cluster_sum_relation_value`, `task_puzzles__arithmetic_constraint__letter_digit_value`, `task_puzzles__arithmetic_constraint__vertical_arithmetic_hidden_digit_value`, `task_puzzles__arithmetic_constraint__number_wall_value`, and `task_puzzles__arithmetic_constraint__operation_table_cell_value`, `task_puzzles__arithmetic_constraint__row_column_total_missing_value`; each records the internal `query_id` and uses prompt-facing `bbox_set` annotation on the marked target node/cell or highlighted target-letter box, with the full panel recorded only in trace metadata.
5. Tents logic is split into `task_puzzles__tents__tents_missing_tent_cell_label` and `task_puzzles__tents__tents_valid_candidate_count`. Each uses scene `tents` and fixed `query_id=missing_tent_cell_label|valid_candidate_count`; annotation is projected from candidate-cell, marked-tree, and clue boxes. The scene also records render-only `palette_variant=garden|autumn|lake|violet|slate`.
5. Toggle-grid logic uses `task_puzzles__toggle_grid__toggle_result_label` and `task_puzzles__toggle_grid__toggle_repair_switch_label` on scene `toggle_grid`. Result queries record `query_id=toggle_result_label` and choose a resulting grid option after numbered switch presses; repair queries record `query_id=toggle_repair_switch_label` and choose the one lettered switch that transforms the start grid into the target grid. Annotation is projected from the start/target panels, selected option panel, or selected switch cell.
5. Misc dice probability uses `task_misc__dice_probability__single_attribute_probability`, `task_misc__dice_probability__single_threshold_probability`, `task_misc__dice_probability__pair_attribute_combo_probability`, `task_misc__dice_probability__pair_difference_probability`, `task_misc__dice_probability__pair_sum_probability`, `task_misc__dice_probability__pair_sum_threshold_probability`, and `task_misc__dice_probability__dice_conditional_event_value` on scene `dice_probability`. The sampled visible-top event branch is recorded as `query_id`, answers are reduced fraction strings, and prompt-facing annotation is role-keyed tray `keyed_bbox_map` grounding.
5. The dice probability tasks use visual `scene_variant` values `dice_tray_clean`, `dice_tray_felt`, and `dice_tray_notebook`; probability is over uniformly selecting from the shown dice, never over rolling unseen dice.
6. Misc spinner probability uses `task_misc__spinner_probability__single_attribute_probability`, `task_misc__spinner_probability__multi_attribute_and_probability`, `task_misc__spinner_probability__multi_attribute_or_probability` and `task_misc__spinner_probability__spinner_pair_event_value` on scene `spinner_probability`. The sampled event branch is recorded as `query_id`, answers are reduced fraction strings, and prompt-facing annotation is panel-level `bbox_set` grounding.
6. The spinner probability tasks use visual `scene_variant` values `spinner_clean`, `spinner_card`, and `spinner_notebook`; sectors are equal probability by construction. Single-spinner scenes show color plus shape markers, while pair-spinner scenes are color-only to keep product-space probability readable.
6. The active logic-board grammar uses one square board with one explicit `?` cell and exactly six labeled image options.
7. The explicit adjacency logic branch must state whether matching symbols are forbidden by edge only or by edge and corner; the current `king_non_touch` rule forbids both and uses the full six-shape option set so the answer stays unique from the visible neighborhood.
8. Prompt-facing logic annotation should stay as one-box `bbox_set` grounding on the winning option panel; keep the query interaction stable as option selection even when later logic families vary the rule structure.
9. Spatial transform result tasks are split into `task_puzzles__paper_fold__paper_fold_result_label`, `task_puzzles__paper_fold_cut__paper_fold_cut_result_label`, and `task_puzzles__overlay__overlay_result_label`. Each records `query_id=paper_fold_result|paper_fold_cut_result|overlay_result`; paper-fold-cut samples `fold_count=1|2`, and single-fold branches sample `fold_axis=vertical|horizontal`.
10. Spatial transform result tasks use visual `scene_variant` values `fold_strip|fold_card|fold_outline` for fold branches and `overlay_strip|overlay_card|overlay_outline` for overlay branches.
11. The active spatial transform grammar covers marked fold-result, fold-cut unfolded-result, and transparent-sheet overlay option selection under one result-option annotation contract.
12. Cube/voxel spatial reasoning uses `scene_id=voxel_cube` and is split into `task_puzzles__voxel_cube__cube_count`, `task_puzzles__voxel_cube__cube_structure_change_count`, `task_puzzles__voxel_cube__cube_painted_face_count`, `task_puzzles__voxel_cube__cube_visible_projection_count`, `task_puzzles__voxel_cube__cube_projection_match_label`, and `task_puzzles__voxel_cube__cube_projection_consistency_label`. Each records `query_id=cube_count|cube_structure_change_count|painted_face_count|visible_cube_count|projection_match_label|projection_consistency_label`.
13. The split cube tasks use visual `scene_variant` values `stack_strip`, `stack_card`, and `stack_outline` for isometric branches plus `cube_stack` for the projection branch.
14. The active cube-structure grammar covers fixed-view wall-like isometric stack counts, side-by-side change counts, painted-face counts, orthographic visible-cell counts, projection matching, and projection consistency as separate task units.
14. Cube-net spatial reasoning uses scene `cube_net` for `task_puzzles__cube_net__cube_net_face_relation_label`, `task_puzzles__cube_net__cube_rolling_result_label`, and `task_puzzles__cube_net__folded_path_endpoint_label`, `task_puzzles__cube_net__folded_path_face_sequence_label`. The folded surface path task records `query_id=folded_path_endpoint_label|folded_path_face_sequence_label` and uses start-face, instruction-panel, and selected-option annotation.
15. Sudoku grid reasoning uses `task_puzzles__sudoku__marked_cell_candidate_count`, `task_puzzles__sudoku__marked_cell_value`, `task_puzzles__sudoku__repeated_digit_count`, and `task_puzzles__sudoku__unit_missing_digits_count` on scene `sudoku`. The fixed branch is recorded as `query_id=marked_cell_candidate_count|marked_cell_value|repeated_digit_count|unit_missing_digits_count`, and prompt-facing annotation is grounded on the marked cell, repeated-digit cells, or queried row/column/block cells.
16. Sliding-block mechanics are now classified as games because the scene is a recognizable playable state with move rules and state transitions.
24. Polyomino spatial reasoning uses `task_puzzles__polyomino_missing__marked_region_piece_label`, `task_puzzles__polyomino_missing__rectangle_complement_piece` for static missing-region and rectangle-complement piece selection. The task records `query_id=marked_region_piece_label|rectangle_complement_piece`.
25. The polyomino missing-region task uses visual `scene_variant` values `polyomino_strip`, `polyomino_card`, and `polyomino_outline`; rectangle-complement queries sample `matching_policy=exact_orientation|rotation_reflection_allowed` as a traced parameter.
26. Tetris-like line completion and general buildable-target assembly are intentionally not active puzzle tasks; game-rule row-completion should live under the games Tetris scene.
27. Tangram-style spatial reasoning is split into `task_puzzles__tangram__tangram_missing_piece_label` and `task_puzzles__tangram__tangram_contact_count`. Each records the fixed `query_id` and keeps polygon-piece matching and edge-contact counting separate from cell-based polyomino reasoning.
28. Illustration-style jigsaw and missing-patch image reconstruction belongs under the `illustrations` domain, not the puzzles spatial family.
29. Prompt-facing spatial annotation should stay as one-box `bbox_set` grounding on the winning option image/panel for fold-result, fold-cut, and overlay tasks; as ordered option-plus-target-region boxes for applicable polyomino and tangram missing-piece branches; as counted-piece boxes for tangram contact counts, with marked piece boxes first and every returned box counted; as the ordered two-box structure pair `[original left, remaining right]` for cube-structure comparison tasks; or as the filled query-grid cell `bbox_set` for solid-view projection counts. Do not invent fake per-missing-cube or explanatory projection bboxes.
31. `task_puzzles__cyclic_order__cyclic_order_equivalent_label` exposes the cyclic-order query contract with `query_id=cyclic_order_equivalent_label`.
32. The cyclic-order tasks sample `token_render_style=colored_beads|shape_tokens|colored_shape_tokens|outline_shape_tokens|symbol_badges` and `loop_path_style=ellipse|rounded_rect|polygon_loop|wavy_loop|beaded_string` as non-semantic visual axes, and use visual `scene_variant` values `necklace_board`, `charm_card_grid`, `route_loop_diagram`, and `token_ring_outline`.
33. String-topology component counting is exposed as `task_puzzles__string_topology__string_component_count`; it records the sampled predicate as `query_id=open_rope_count|closed_loop_count|knotted_component_count`.
34. The string-topology task uses visual `scene_variant` values `string_strip`, `string_card`, and `string_outline`.
35. The active topology cyclic-order grammar uses one reference loop above exactly `6` labeled option loops with exactly one equivalent option; equivalent-label queries use `4..5` tokens. Color-bearing token styles should use Lab-separated colors, prompt-facing annotation should be the valid option-image bbox, and the prompt must explicitly say that flipping/reflection is not allowed.
36. The active string-topology grammar uses one diagram of separate open strings, closed rings, and knots; it samples target answer count `3..10` and distractor count `3..10` independently, keeps total visible groups at `6..20`, uses knotted closed loops as open-rope distractors, and uses component bboxes as prompt-facing annotation for open/closed/knotted component counts.
37. Color-gradient visual reasoning uses `task_puzzles__color_gradient__color_gradient_violation_cell_label` and `task_puzzles__color_gradient__color_gradient_completion_label` on scene `color_gradient`. Violation uses fixed `query_id=color_gradient_violation_cell_label` with one-box swatch-cell annotation, while completion uses fixed `query_id=linear_gradient_completion_label` with role-keyed `blank_swatch` and `selected_option` annotation.
37. Maze topology is split into `task_puzzles__maze__exit_reachability_label` and `task_puzzles__maze__reachable_exit_count`; the label query uses `target_reachability=reachable|unreachable`.
38. Pipe-flow repair uses `task_puzzles__pipe_flow__pipe_flow_repair_tile_label` on scene `pipe_flow`. It uses fixed `query_id=flow_repair_tile_label` and option-plus-gap `bbox_set` annotation for the labeled 2x2 option that can be rotated to fill the black missing region and restore connectivity from the green start marker to the red triangular finish flag. Offshoot branches are attached to the main path and terminate on a grid side.
38. The maze tasks use visual `scene_variant` values `classic_wall_maze`, `paper_labyrinth_maze`, and `block_wall_maze`.
39. The active maze grammar shows a START cell inside an orthogonal wall maze with labeled boundary exits; it samples `6..8` rows, `7..10` columns, and `4..6` exits, constructs reachability from metadata rather than pixels, and projects target or reachable exit label+doorway bboxes.
40. Voxel-ladder topology uses scene `voxel_ladder` with `task_puzzles__voxel_ladder__checkpoint_sequence_label` and `task_puzzles__voxel_ladder__reachable_checkpoint_count`, `task_puzzles__voxel_ladder__unreachable_checkpoint_label`; the reachability task records `unreachable_checkpoint_label|reachable_checkpoint_count` in `query_id`.
41. The voxel-ladder grammar shows an isometric cube maze with blue START, red GOAL, colored checkpoints sampled from the canonical TRACE named-color palette, and black ladders. Movement is adjacent same-height cube tops plus ladders for height changes, with prompt-facing `bbox_set` annotation projected from route checkpoints, unreachable checkpoints, or reachable checkpoint sets.
42. Misc organic-structure notation uses scene `organic_structure` for `task_misc__organic_structure__bond_order_count`, `task_misc__organic_structure__branch_point_count`, and `task_misc__organic_structure__ring_size_count`. Bond-order count records `query_id=bond_order_count` and `target_bond_order=double|triple`, samples answer support `1..4`, counts only visible double/triple bond notation, and projects prompt-facing `point_pair_set` annotation from matching bond endpoint pairs. Branch-point count records `query_id=branch_point_count`, samples answer support `0..4`, counts line-angle vertices where three or more drawn bonds meet, and projects prompt-facing `point_set` annotation from matching vertex centers. Ring-size count records `query_id=ring_size_count` and `target_ring_size=5|6`, samples answer support `0..4`, counts separated pentagonal or hexagonal rings, and projects prompt-facing `bbox_set` annotation from matching ring boxes. The shared scene grammar enforces basic carbon valence, linear unbranched triple bonds, minimum branch angles, separated-ring geometry for ring-size queries, and curated chain/ring geometry, while atom labels, implicit-carbon totals, formulas, molecule identity, fused-ring interpretation, and chemistry naming/reaction knowledge remain outside these task contracts.
43. Misc Braille-cell notation uses scene `braille_cell` for `task_misc__braille_cell__raised_dot_count` and `task_misc__braille_cell__matching_pattern_label`. Raised-dot count records `query_id=raised_dot_count`, samples answer support `1..6`, counts only filled raised dots in the marked target cell, and projects prompt-facing `point_set` annotation from raised-dot centers. Matching-pattern label records `query_id=matching_pattern_label`, shows one reference cell and exactly six labeled visual options, and projects role-keyed `reference_cell` and `selected_option` bboxes. Empty dot guides are render scaffolding and are not counted.
44. Misc Boolean logic-gate notation uses scene `logic_gate_circuit` for `task_misc__logic_gate_circuit__output_value_count` and `task_misc__logic_gate_circuit__satisfying_assignment_label`. Output-value count records `query_id=output_one_count|output_zero_count`, shows exactly six independent circuits with visible input values, samples answer support `0..6`, and projects prompt-facing `point_set` annotation from matching final `OUT` node centers. Satisfying-assignment label records `query_id=assignment_outputs_one_label|assignment_outputs_zero_label`, shows one source circuit plus exactly six visual candidate assignment rows, enforces a unique satisfying option, and projects role-keyed `source_circuit` and `selected_option` bboxes. Supported gates are `AND`, `OR`, `NOT`, `XOR`, `NAND`, and `NOR`; final output values are computed from metadata and are not printed in the image.
45. Misc abacus readout uses scene `abacus_readout` for `task_misc__abacus_readout__displayed_value_readout`. It records `query_id=displayed_value_readout`, shows exactly three soroban-style columns labeled `100`, `10`, and `1`, computes the integer value from active upper/lower beads, and projects prompt-facing `keyed_point_set_map` annotation keyed as `hundreds_active_beads`, `tens_active_beads`, and `ones_active_beads`. Empty annotation lists are valid when a column digit is `0`; rods, beam, frame, and place labels are not prompt-facing annotation.
46. Misc abacus target-value matching uses scene `abacus_match_panel` for `task_misc__abacus_match_panel__target_value_match_label`. It records `query_id=target_value_match_label`, shows exactly six labeled compact abacus option cards, names the target integer only in the prompt, enforces exactly one option whose bead positions represent that value, and projects prompt-facing one-box `bbox_set` annotation around the selected option card.

## Time Artifact Placement
1. Time-artifact scenes use the same public `domain -> scene_id -> task_id` taxonomy as the rest of TRACE.
2. Clock scenes live in `misc`: `analog_clock`, `clock_collection`, and `clock_match_panel`.
3. Calendar, schedule, and timeline scenes live in `pages`: `calendar`, `schedule`, and `timeline`.
4. Active task ids are `task_pages__calendar__marked_day_class_count`, `task_pages__calendar__weekday_occurrence_date`, `task_pages__calendar__workday_offset_date`, `task_misc__clock_collection__compare`, `task_misc__clock_match_panel__equivalent_time_label`, `task_misc__analog_clock__offset_readout`, `task_pages__schedule__overlap_count`, `task_pages__schedule__longer_than_reference_count`, `task_pages__schedule__maximum_non_overlapping_count`, `task_pages__timeline__interval_membership_count`, and `task_pages__timeline__event_date_gap_value`.
5. Mirror/query knobs go in `query_id`.
6. Split task ids are used when the reasoning or annotation contract differs: clock readout vs multi-clock comparison vs analog/digital option matching, calendar lookup vs marked-date count vs workday-offset traversal, schedule overlap count vs duration comparison vs schedule optimization.
7. Mirror/query knobs remain internal: clock compare `earliest|latest`, clock readout `before|after`, clock match direction `analog_reference_digital_options|digital_reference_analog_options`, calendar marked class `weekend|weekday`, calendar workday direction `before|after`, timeline interval relation `between|outside`, and timeline endpoint prompt order for date-gap queries.
8. The active time-artifact tasks use visual `scene_variant` values `classic`, `minimal`, and `outline`, except the milestone timeline, which uses `classic|roadmap|minimal`.
9. Non-semantic axes `style_variant=studio|accented|marker`, `accent_color_name`, clock-match digital-display palette, background style, and mild post-image noise must never change the prompt contract.
10. Annotation stays local to the queried witness: clock hands, winning clock faces, date cells, schedule event blocks, or timeline event cards.

## Physics direction (current)
1. Physics should stay diagram-first: the image should contain the operative values, directions, or placements needed to solve the task.
2. Public task ids are default sampling units. `scene_variant` names the scaffold, and `query_id` names the narrowed query contract inside a shared renderer. Physics taxonomy rows must use concrete formula/rule schemas rather than generic placeholders such as `formula.solve_unknown`.
3. The active physics families are `mechanics`, `circuits`, `electrostatics`, `magnetism`, `fluids`, `optics`, `thermodynamics`, `measurement`, and `waves`.
4. `task_physics__pulley__pulley_mechanical_advantage`
   - uses scene variants `open_block|compact_block|tall_block`
   - uses `query_id=force_relation` with `solve_for=effort_force|load_force`
   - keeps integer answers with `keyed_bbox_map` annotation over the full supporting strands, shown known-force label, and marked target-force label
   - keeps the pulley arithmetic tied to ideal mechanical advantage from full connecting strands, while cut strands act only as visual distractors
5. Lever-balance tasks:
   - active ids are `task_physics__lever__side_torque_value` and `task_physics__lever__missing_weight_balance_value`
   - uses scene variants `center_fulcrum|offset_fulcrum|textured_beam`
   - uses `query_id=side_torque|missing_weight_to_balance`, with `torque_side=left|right` as an internal side mirror for side torque
   - keeps integer answers with unordered `bbox_set` annotation over the relevant side’s weight blocks for `side_torque`, and `keyed_bbox_set_map` annotation over `known_weights` plus `target_weight` for `missing_weight_to_balance`
   - calibrates the public missing-weight task on `textured_beam` only, with answer support `1..6` and lower side clutter
   - samples one non-semantic `accent_color_name` palette for the beam / fulcrum / shown weights while leaving the red `?` weight semantics unchanged
6. Equivalent-circuit tasks:
   - active ids are `task_physics__circuit_equivalent__total_resistance_value` and `task_physics__circuit_equivalent__total_capacitance_value`
   - uses scene variant `series_parallel` for both public tasks
   - uses `query_id=total_resistance|total_capacitance`
   - every generated circuit contains at least one series component and one or two parallel component blocks
   - keeps integer answers with input-witness `keyed_bbox_map` annotation over visible component labels (`R1`, `R2`, ... or `C1`, `C2`, ...)
   - annotation bboxes enclose each engineering symbol plus its value label, not wires or terminal labels separately
   - samples one non-semantic `accent_color_name` palette for wires, terminals, component labels, and technical-diagram rendering
7. Bulb-circuit brightness task:
   - active id is `task_physics__bulb_circuit__brightness_extremum_label`
   - uses scene variants `series_unequal|parallel_unequal|mixed_branch`
   - uses `query_id=brightest_bulb_label|dimmest_bulb_label`
   - keeps string-label answers such as `B1`, with `keyed_bbox_map` annotation over each visible bulb symbol plus its resistance label for `B1` through `B5`
   - keeps qualitative brightness ranking separate from equivalent-resistance/capacitance tasks; glow intensity is not used to encode the answer
8. Switch-circuit lit-bulb count task:
   - active id is `task_physics__switch_circuit__lit_bulb_count`
   - uses scene variant `mixed_branch`
   - uses `query_id=lit_bulb_count`
   - keeps integer count answers in `0..5`, including valid all-off and all-on cases
   - keeps unordered `bbox_set` annotation over only the bulb symbols that will be on; zero-count examples use an empty annotation array
   - keeps switch-current-flow connectivity separate from equivalent-resistance and bulb-brightness contracts; bulbs are not visually glowed as an answer cue
9. Bridge-circuit missing-resistance task:
   - active id is `task_physics__bridge_circuit__bridge_missing_resistance_value`
   - uses scene variant `rectangular_bridge`
   - uses `query_id=missing_bridge_resistance`, with the missing resistor slot as an internal axis
   - keeps integer-ohm answers with `keyed_bbox_map` annotation over known resistor labels, `target_resistor`, and `zero_meter`
   - keeps bridge-balance reasoning tied to the visible zero-current meter condition rather than treating the scene as an equivalent-resistance network
10. Electrostatics field-map tasks:
   - active ids are `task_physics__electrostatic_field__field_direction_choice`, `task_physics__electrostatic_field__zero_field_point_label`, and `task_physics__electrostatic_field__potential_value`
   - uses scene variants `clean_grid|paper_grid|dense_grid`
   - uses `query_id=field_direction_choice|zero_field_point_label|potential_value`, with `direction_mode=electric_field_direction|force_on_positive_charge|force_on_negative_charge` as an internal axis for direction-choice queries
   - treats direction arrows, zero-field candidate points, and potential distance labels as query-specific view contracts inside the same field-map scene
   - keeps option-letter or signed-integer answers with input-witness `keyed_point_map` annotation over visible neutral charge keys (`Q1`, `Q2`, `Q3`) and, for point-`P` queries, key `P`; zero-field candidate letters remain answer options rather than annotation targets
   - keeps force-on-negative-charge and similar sign/mode changes inside one public direction task rather than splitting them into separate task ids
11. Magnetism force-field tasks:
   - active id is `task_physics__magnetic_force__force_direction_choice`
   - uses scene variants `clean_panel|field_grid|lab_card`
   - uses `query_id=force_direction_choice`
   - keeps `field_orientation=out_of_page|into_page`, velocity direction, charge sign, and candidate-arrow placement as internal axes
   - calibrates the public task on `field_grid`, with correct-answer letters `B|C|D|E|G|H` while all eight options remain visible
   - keeps option-letter answers with input-witness `keyed_bbox_map` annotation over the magnetic-field label, charged particle, and velocity vector; candidate arrows remain answer options rather than annotation targets
12. Waves interference-tank tasks:
   - active ids are `task_physics__wave_interference__interference_point_choice` and `task_physics__wave_interference__path_difference_value`
   - uses scene variants `clean_tank|grid_tank|lab_sheet`
   - uses `query_id=interference_point_choice|path_difference_value`
   - keeps `phase_relation=in_phase|opposite_phase`, `target_condition=constructive|destructive`, and candidate-point placement as internal axes
   - uses five candidate labels `A-E` for point choice and path-difference answers `1..5` for the calibrated public mix
   - keeps option-letter answers with `point_set` annotation over the selected candidate-point center, and integer `lambda/2` step-count answers with `keyed_bbox_map` annotation over the labeled `S1P` and `S2P` path witnesses
13. Waveform-panel task:
   - active id is `task_physics__waveform_panel__wave_property_extremum_label`
   - uses scene variants `clean_stack|grid_stack|lab_sheet`
   - uses `query_id=highest_amplitude_label|lowest_amplitude_label|highest_frequency_label|lowest_frequency_label|longest_wavelength_label|shortest_wavelength_label`
   - keeps panel count `4|5|6`, query property, and correct panel letter as internal axes inside one wave-property extremum contract
   - keeps option-letter answers with unordered `bbox_set` annotation over only the selected waveform panel
   - compares amplitude by vertical displacement and frequency/wavelength by cycle count over a shared horizontal scale
14. Signal-transform tasks:
   - active ids are `task_physics__signal_transform__sinusoid_component_spectrum_match_label`, `task_physics__signal_transform__periodic_harmonic_spectrum_match_label`, and `task_physics__signal_transform__pulse_width_spectrum_match_label`
   - uses scene variants `clean_match|grid_match|lab_sheet`
   - each public task fixes one query id: `sinusoid_component_spectrum`, `periodic_wave_harmonic_spectrum`, or `pulse_width_spectrum`
   - keeps waveform family, spectrum distractors, and correct option letter as internal axes inside the corresponding spectrum-match contract
   - keeps option-letter answers with `keyed_bbox_map` annotation over `input_waveform` and `selected_spectrum`
   - renders visual spectrum options in the image and uses one-sided magnitude spectra for the calibrated public surface
15. Optics ray-trace tasks:
   - active ids are `task_physics__ray_optics__ray_bounce_count` and `task_physics__ray_optics__ray_target_hit_count`
   - uses scene variants `single_mirror|double_mirror|triple_mirror|quad_mirror|five_mirror`
   - uses `query_id=bounce_count|target_hit_count`
   - keeps integer answers with unordered pixel `point_set` annotation over either bounce-point centers or hit target-point centers
   - shows only the initial ray direction in the prompt image, keeps the solved full path in trace/debug artifacts, ties mirror count directly to `scene_variant`, and reserves `five_mirror` for calibrated `bounce_count` while the smaller mirror-count scenes feed `target_hit_count`
   - uses large unlabeled target dots for `target_hit_count` with calibrated answers `1..5`, bounce-count answers `1..5`, and no separate bounce circles for `bounce_count`
   - uses shared technical diagram backgrounds/palettes, one readout font family per board, and whole-board layout placement before point-annotation projection
16. Optics shadow-cause task:
   - active id is `task_physics__shadow_cause__light_source_label`
   - uses scene id `shadow_cause` and `query_id=source_from_shadow_label`
   - keeps option-letter answers over six labeled candidate light sources in the image
   - keeps `keyed_bbox_map` annotation only for `object` and `shadow`, because lamp labels are visual answer options rather than witnesses
   - samples shadow direction, object shape, object color, and correct option letter independently; the answer is the light source opposite the cast-shadow direction from the object
17. Spring-extension tasks:
   - active ids are `task_physics__spring__spring_missing_value` and `task_physics__spring__spring_extension_difference`
   - uses scene variants `paired_springs|staggered_springs|textured_spring`
   - uses `query_id=missing_value|extension_difference`, with `solve_for=weight|extension` as an internal inverse axis for missing-value queries
   - keeps integer answers with `keyed_bbox_map` annotation for missing-value role witnesses (`reference_weight`, `reference_extension`, `query_weight`, `query_extension`) and unordered `bbox_set` annotation over the two compared value-labeled extension markers for `extension_difference`
   - keeps the two springs explicitly identical within each instance and encodes the proportionality only through the shown weight/extension pair, not through a printed formula
   - calibrates `extension_difference` with scale factor `2` and answer support `2|4|8|10|12`
   - uses shared technical-diagram backgrounds/palettes, one readout font family per diagram, and whole-diagram layout placement before annotation projection while the missing-value placeholders remain red
18. Motion-graph tasks:
   - active ids are `task_physics__motion_graph__velocity_sign_choice` and `task_physics__motion_graph__speed_change_state_choice`
   - uses scene variants `clean_grid|paper_grid|bold_grid`
   - uses `query_id=velocity_sign_choice` for position-time slope-sign reasoning and `query_id=speed_change_state_choice` for velocity-time speed-change reasoning
   - keeps position-time slope-sign and velocity-time speed-change questions as separate public contracts
   - keeps option-letter answers with `keyed_bbox_map` annotation over `query_region` and `curve_segment`; visible state-option boxes remain answer options rather than annotation targets
   - rejects ambiguous near-flat slopes or near-zero velocity values unless the intended state is exactly stationary or constant speed
19. Stack-stability task:
   - active id is `task_physics__stack_stability__stability_status_label`
   - uses `query_id=stable_stack_label|tipping_stack_label`
   - keeps stable-vs-tipping selection inside one public stability-status contract
   - keeps option-letter answers with `keyed_bbox_map` annotation over `center_of_mass`, `projection`, and `support_footprint` for the selected stack only
   - varies brick colors and stack offsets independently from the answer except for the intended center-of-mass/support geometry
20. Collision-aftermath cause task:
   - active id is `task_physics__collision__incoming_path_cause_choice`
   - uses scene variants `aftermath_table|aftermath_gridded_table|aftermath_compact_table`
   - uses `query_id=incoming_path_cause_choice`
   - keeps option-letter answers over six labeled incoming path arrows drawn in the scene
   - keeps `keyed_bbox_map` annotation over `impact_point` and `target_after_motion`; candidate arrows remain visual answer options rather than annotation targets
   - samples final motion direction and correct option letter independently, and infers the cause by matching the incoming path vector to the target puck's aftermath trail from the impact point
21. Hydraulic piston task:
   - active id is `task_physics__hydraulic__hydraulic_missing_value`
   - uses scene variants `wide_bench|compact_frame|tall_columns`
   - uses `query_id=missing_output_force|missing_input_force|missing_piston_area|missing_input_area`
   - keeps integer answers with `keyed_bbox_map` annotation over only the known force/area labels needed to compute the missing value; keys bind the visible labels to roles such as `input_force`, `output_force`, `input_area`, and `output_area`
   - ties reasoning to Pascal's law, `F_input / A_input = F_middle / A_middle = F_output / A_output`, with integer mechanical-advantage constructions
   - samples one non-semantic `accent_color_name` palette for the chambers, fluid, and pistons while the missing-value placeholder remains red
22. Buoyancy-density task:
   - active id is `task_physics__buoyancy_density__object_density_value`
   - uses scene variants `rectangular_tank|beaker_tank|wide_tank`
   - uses `query_id=floating_object_density_value`
   - keeps decimal-number answers with `keyed_bbox_map` annotation over `floating_object`, `waterline`, `fluid_density_label`, and `submerged_fraction_marker`
   - treats submerged fraction, liquid density, scene variant, object shape, and target density as query/render arguments inside one object-density contract
   - never ties color or object shape to the answer; these remain non-semantic visual variation axes
23. Thermodynamics PV-diagram tasks:
   - active ids are `task_physics__pv_diagram__pv_work_value` and `task_physics__pv_diagram__pv_process_sign_choice`
   - uses scene variants `clean_grid|paper_grid|bold_grid`
   - uses `query_id=work_value|process_sign_choice`; calibrated `work_value` sampling uses `work_mode=single_process`, while `process_sign_choice` uses `target_sign=positive|negative|zero` as an internal axis
   - keeps signed-integer or option-letter answers with one-box `bbox_set` annotation over the highlighted path/cycle for work values or the process arrow in the correct mini-process option for sign choice
   - uses shared technical diagram backgrounds/palettes, one readout font family per diagram, and whole-diagram layout placement before annotation projection
24. Thermometer conversion task:
   - active id is `task_physics__thermometer__temperature_conversion_value`
   - uses `query_id=celsius_to_fahrenheit_value|fahrenheit_to_celsius_value`
   - keeps thermometer scale profile and source readout as internal axes inside one conversion contract
   - keeps integer answers with `keyed_bbox_map` annotation over `liquid_level`, `scale_region`, and `source_unit_label`
   - includes the conversion formula in the prompt and does not expose a separate simple thermometer-readout task
25. Thermal-mixing task:
   - active id is `task_physics__thermal_mixing__final_temperature_value`
   - uses `query_id=equal_amount_final_temperature`
   - keeps cup count `2..4` as an internal axis inside one equal-amount final-temperature contract
   - keeps integer Celsius answers with unordered `bbox_set` annotation over the initial cups and visible temperature labels
   - asks for the final equilibrium temperature after equal amounts of the same liquid are mixed in an insulated system
26. Vernier-caliper measurement task:
   - active id is `task_physics__vernier_caliper__length_readout_value`
   - uses `query_id=main_scale_vernier_mm`
   - keeps main-scale reading, aligned vernier tick, and target answer as internal axes inside one readout contract
   - keeps one-decimal numeric answers in millimeters with `keyed_bbox_map` annotation over `main_scale_region`, `vernier_zero`, `vernier_scale_region`, and `aligned_vernier_tick`
   - states or shows the `0.1 mm` vernier resolution and does not expose integer-only ruler-style readout as a query branch
27. Active audited physics tasks use shared `technical_diagram_style` backgrounds/palettes/frame modes plus post-render noise; these are visual-only and must not change coordinates, object positions, measurement grids, or annotation semantics.
28. Early physics tasks should prefer light arithmetic over heavy formula derivations, and prompt-facing annotation should stay on the visible witness objects rather than decorative scene chrome.

## Games Direction (Current)
1. Games use public taxonomy `games -> scene_id -> task_id`.
2. One game scene can contain multiple public tasks when the reasoning algorithm or answer/annotation contract differs.
3. Mirror knobs remain params inside a task: player color, board size, row/column axis, threshold direction, and visual style.
4. Active scenes and narrow default tasks:
   - `2048`: `task_games__2048__max_tile_value`, `task_games__2048__merge_count`, `task_games__2048__move_result_board_label`, `task_games__2048__score_value`
   - `backgammon`: `task_games__backgammon__blocked_destination_count`, `task_games__backgammon__legal_move_count`
   - `battleship`: `task_games__battleship__last_ship_cell_label`, `task_games__battleship__ship_cell_status_count`, `task_games__battleship__ship_status_count`
   - `bingo`: `task_games__bingo__called_number_mark_count`, `task_games__bingo__completed_line_count`, `task_games__bingo__line_sum_extremum_value`, `task_games__bingo__near_complete_line_count`
   - `bowling`: `task_games__bowling__first_pin_hit_label`, `task_games__bowling__spare_path_label`
   - `brick_breaker`: `task_games__brick_breaker__hit_row_remaining_count`, `task_games__brick_breaker__next_hit_label`, `task_games__brick_breaker__paddle_catch_label`
   - `bubble_shooter`: `task_games__bubble_shooter__drop_count`, `task_games__bubble_shooter__pop_color_label`, `task_games__bubble_shooter__pop_count`
   - `cards`: `task_games__cards__blackjack_best_hand_label`, `task_games__cards__exact_triple_count`, `task_games__cards__higher_than_reference_count`, `task_games__cards__longest_run_length`, `task_games__cards__missing_card_to_complete_hand_label`, `task_games__cards__poker_best_hand_label`, `task_games__cards__same_suit_as_reference_count`, `task_games__cards__trick_taking_winner_label`
   - `checkers`: `task_games__checkers__max_capture_chain_length`, `task_games__checkers__move_count`, `task_games__checkers__piece_mobility_count`
   - `chess`: `task_games__chess__colored_piece_kind_count`, `task_games__chess__king_escape_square_count`, `task_games__chess__marked_piece_blocker_count`, `task_games__chess__marked_piece_destination_count`, `task_games__chess__piece_kind_count`, `task_games__chess__player_capture_piece_count`, `task_games__chess__target_square_attacker_count`
   - `chess_variant`: `task_games__chess_variant__marked_piece_destination_count`, `task_games__chess_variant__target_square_reacher_count`
   - `circular_chess`: `task_games__circular_chess__marked_piece_destination_count`, `task_games__circular_chess__target_cell_reacher_count`
   - `connect_four`: `task_games__connect_four__safe_move_count`, `task_games__connect_four__winning_move_column_label`, `task_games__connect_four__winning_move_count`
   - `crossing`: `task_games__crossing__moving_object_count`, `task_games__crossing__moving_object_direction_count`
   - `darts`: `task_games__darts__ring_count`, `task_games__darts__threshold_score_count`, `task_games__darts__total_score_option_label`
   - `dominoes`: `task_games__dominoes__double_count`, `task_games__dominoes__extendable_first_play_count`, `task_games__dominoes__higher_sum_than_reference_count`, `task_games__dominoes__matching_end_count`, `task_games__dominoes__second_play_candidate_count`, `task_games__dominoes__sum_to_target_count`
   - `dots_and_boxes`: `task_games__dots_and_boxes__capture_move_count`, `task_games__dots_and_boxes__three_sided_box_count`
   - `go`: `task_games__go__group_adjacent_enemy_count`, `task_games__go__group_liberty_count`, `task_games__go__stone_group_count`
   - `hex`: `task_games__hex__candidate_neighbor_count`, `task_games__hex__connection_gap_count`, `task_games__hex__winning_move_cell_label`
   - `irregular_link_board`: `task_games__irregular_link_board__capture_move_count`, `task_games__irregular_link_board__marked_piece_destination_count`
   - `lane_runner`: `task_games__lane_runner__path_coin_count`, `task_games__lane_runner__safe_path_label`
   - `ludo_board`: `task_games__ludo_board__capture_roll_option_label`, `task_games__ludo_board__move_result_option_label`, `task_games__ludo_board__winning_roll_value`
   - `mancala_pit_board`: `task_games__mancala_pit_board__post_sow_pit_count_value`, `task_games__mancala_pit_board__sowing_landing_pit_label`
   - `marble_chain`: `task_games__marble_chain__max_pop_direction_label`, `task_games__marble_chain__shot_effect_value`, `task_games__marble_chain__target_pop_direction_label`
   - `match3`: `task_games__match3__gem_count`, `task_games__match3__max_clear_swap_label`, `task_games__match3__target_clear_swap_label`
   - `minecraft`: `task_games__minecraft__reachable_ore_stack_count`, `task_games__minecraft__resource_route_cost`, `task_games__minecraft__stack_height_condition_count`, `task_games__minecraft__top_ore_stack_count`
   - `minesweeper`: `task_games__minesweeper__forced_cell_count`, `task_games__minesweeper__remaining_mine_count_value`, `task_games__minesweeper__reveal_outcome_label`, `task_games__minesweeper__satisfied_clue_count`
   - `minigolf`: `task_games__minigolf__first_obstacle_label`, `task_games__minigolf__shot_path_label`
   - `nine_mens_morris`: `task_games__nine_mens_morris__mill_completion_point_count`, `task_games__nine_mens_morris__pieces_in_mill_count`
   - `pacman`: `task_games__pacman__next_item_label`, `task_games__pacman__path_pellet_count`, `task_games__pacman__pellet_count_before_ghost`, `task_games__pacman__route_score_value`
   - `pinball_table`: `task_games__pinball_table__first_hit_object_label`, `task_games__pinball_table__path_score_value`
   - `platformer`: `task_games__platformer__collectible_count`, `task_games__platformer__jump_collectible_score_value`, `task_games__platformer__jump_landing_label`
   - `pool`: `task_games__pool__blocking_ball_count`, `task_games__pool__group_ball_count`
   - `reversi`: `task_games__reversi__legal_destination_count`, `task_games__reversi__marked_move_flip_count`
   - `rhythm`: `task_games__rhythm__earliest_hit_lane_label`, `task_games__rhythm__lane_color_hit_count`, `task_games__rhythm__lane_hit_count`, `task_games__rhythm__most_hits_lane_label`
   - `rule_override_board`: `task_games__rule_override_board__line_result_count`, `task_games__rule_override_board__piece_result_count`
   - `snake`: `task_games__snake__path_outcome_option_label`, `task_games__snake__safe_direction_count`, `task_games__snake__shortest_food_path_length`
   - `snakes_ladders`: `task_games__snakes_ladders__best_roll_value`, `task_games__snakes_ladders__move_outcome_value`
   - `solitaire`: `task_games__solitaire__foundation_ready_count`, `task_games__solitaire__move_legality_label`, `task_games__solitaire__same_suit_run_length_value`, `task_games__solitaire__tableau_sequence_count`
   - `sliding_block`: `task_games__sliding_block__sliding_block_blocker_count`, `task_games__sliding_block__movable_block_count`, `task_games__sliding_block__sliding_block_move_result_label`
   - `sokoban`: `task_games__sokoban__box_target_manhattan_rank_label`, `task_games__sokoban__nearest_counterpart_label`, `task_games__sokoban__path_validity_sequence_label`, `task_games__sokoban__shortest_path_sequence_label`
   - `space_shooter`: `task_games__space_shooter__clear_shot_count`, `task_games__space_shooter__clear_shot_score_value`, `task_games__space_shooter__highest_threat_label`, `task_games__space_shooter__projectile_intercept_count`, `task_games__space_shooter__safe_lane_count`
   - `tetris`: `task_games__tetris__drop_collision_time_value`, `task_games__tetris__drop_result_label`, `task_games__tetris__line_clear_count`, `task_games__tetris__row_occupancy_status_count`
   - `tic_tac_toe_3d`: `task_games__tic_tac_toe_3d__layer_piece_count`, `task_games__tic_tac_toe_3d__winning_move_cell_label`
   - `tower_draughts_board`: `task_games__tower_draughts_board__controlled_stack_count`, `task_games__tower_draughts_board__marked_stack_capture_count`, `task_games__tower_draughts_board__marked_stack_destination_count`
   - `ultimate_tictactoe`: `task_games__ultimate_tictactoe__line_completion_move_label`, `task_games__ultimate_tictactoe__macro_threat_board_count`, `task_games__ultimate_tictactoe__small_board_status_count`
5. Active games tasks use integer or label-string answers and local pixel-grounded annotation over the visible witnesses: usually `bbox_set` over cells, pieces, cards, dominoes, bricks, catch lanes, crossing vehicles/route cells, hex cells, bubbles, color options, or intersections; `point_set` for compact marker-like witnesses such as darts; and `point_pair_set` for line-like trajectory/path cues.
6. Shared game renderers and rules should stay under `trace/tasks/games/shared/`; fixed-query public task wrappers should use `trace/tasks/games/shared/fixed_query_task.py`, which delegates shared metadata rewriting to `trace/tasks/shared/fixed_query.py`, instead of duplicating renderer or wrapper logic.

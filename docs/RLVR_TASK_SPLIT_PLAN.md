# TRACE RLVR Task Split Plan

This note defines the planned task-level train/test split for TRACE RLVR. It is
a planning document for the final task surface, not a generated manifest.

## Goal

Target final active task count is about `960` tasks across `11` domains. Use a
fixed held-out test set of `100` tasks and train on the remaining `860` tasks.

The test set should measure two kinds of generalization:

1. `known_scene`: the scene remains in train, but one or more objectives from
   that scene are held out.
2. `new_scene`: the entire scene is absent from train, so all tasks in that
   held-out scene are test tasks.

The target split is roughly 50/50 between known-scene and new-scene test tasks.
Do not force exact 50/50 when scene sizes make it unnatural. Every domain must
contribute at least five test tasks, and the domain test counts should remain
roughly proportional to the domain task counts.

## Current Inventory Snapshot

As of the current generated inventory, TRACE has `977` default tasks:

| Domain | Current tasks | Current scenes |
| --- | ---: | ---: |
| charts | 180 | 42 |
| games | 160 | 52 |
| geometry | 168 | 40 |
| graph | 60 | 10 |
| icons | 40 | 16 |
| illustrations | 60 | 12 |
| pages | 80 | 26 |
| physics | 50 | 36 |
| puzzles | 60 | 20 |
| symbolic | 59 | 14 |
| three_d | 60 | 8 |

The final expected count is closer to `960`; the table below uses the intended
final target counts, not the transient current inventory.

## Domain Test Allocation

| Domain | Final target tasks | Test tasks | Train tasks | Known-scene test | New-scene test |
| --- | ---: | ---: | ---: | ---: | ---: |
| charts | 180 | 19 | 161 | 9 | 10 |
| games | 160 | 17 | 143 | 9 | 8 |
| geometry | 150 | 16 | 134 | 8 | 8 |
| graph | 60 | 6 | 54 | 2 | 4 |
| icons | 40 | 5 | 35 | 3 | 2 |
| illustrations | 60 | 6 | 54 | 2 | 4 |
| symbolic | 60 | 6 | 54 | 3 | 3 |
| pages | 80 | 8 | 72 | 4 | 4 |
| physics | 50 | 5 | 45 | 3 | 2 |
| puzzles | 60 | 6 | 54 | 3 | 3 |
| three_d | 60 | 6 | 54 | 3 | 3 |
| **Total** | **960** | **100** | **860** | **49** | **51** |

The `graph` and `illustrations` rows intentionally deviate from exact 50/50.
Graph scenes have no one-task scenes, so a three-task new-scene holdout is not
possible. Illustration scenes start at four tasks, so a three-task new-scene
holdout is also not possible.

## Candidate New-Scene Holdouts

These are candidate scene-level holdouts that satisfy the desired counts using
the current scene structure. Final selection should use accepted, review-clean,
calibrated scenes. If any candidate scene is retired or not accepted, replace it
with another scene of the same size where possible.

| Domain | Candidate held-out scenes | New-scene test tasks |
| --- | --- | ---: |
| charts | `annotated_series` + `radial_sankey` + `contour_density` + `surface_3d` | 10 |
| games | `backgammon` + `pinball_table` + `mancala_pit_board` + `tic_tac_toe_3d` | 8 |
| geometry | `area_partition` + `circle_centerline_overlap` + `cone_net` + `solid_cross_section` + `bearing_route` | 8 |
| graph | `flow_network` + `pedigree_chart` | 4 |
| icons | `icon_cutout` + `venn_field` | 2 |
| illustrations | `isometric_harbor` | 4 |
| symbolic | `braille_cell` | 3 |
| pages | `schema` | 4 |
| physics | `collision` | 2 |
| puzzles | `sheet_transform` | 3 |
| three_d | `street` | 3 |
| **Total** |  | **51** |

These scene names are recommendations, not locked choices. They were chosen to
hit the count targets with small or medium scenes, avoid consuming a large
fraction of a domain test budget with one oversized scene, and reduce visual
and reasoning overlap among held-out scenes. For example, avoid holding out
both `charts/candlestick` and `charts/boxplot` as unseen scenes because both
are compact range/distribution glyph grammars; likewise, do not use
`three_d/object_scene` as a new-scene holdout for the six-task three_d test
budget because it has fifteen tasks.

## Known-Scene Holdout Selection

Known-scene test tasks should be selected after the final active task inventory
and review status are stable. Use these rules:

1. Pick only tasks whose scene still has at least two train tasks after the
   holdout.
2. Prefer larger scenes so a held-out objective is not the only representation
   of that visual grammar.
3. Avoid holding out a task that is a near-duplicate of a train task unless the
   objective contract is genuinely different.
4. Cover answer schemas and annotation schemas: integer counts, numeric values,
   option labels, string labels, bbox-family annotation, point-family
   annotation, segment-family annotation, and map/sequence contracts where
   available.
5. Keep solve-rate and review status balanced. Do not let the test set become
   mostly failed, pending, or very-hard tasks.
6. Prefer one held-out task per scene before taking multiple known-scene
   holdouts from the same scene, unless the domain has very few scenes.

Recommended known-scene sources by domain:

| Domain | Known-scene count | Prefer scenes like |
| --- | ---: | --- |
| charts | 9 | `single_series`, `region_map`, `curve_panels`, `dashboard`, `combo_mark`, `table`, `composition_panels`, `multiseries`, `pictogram` |
| games | 9 | `cards`, `chess`, `dominoes`, `tetris`, `space_shooter`, `solitaire`, `bingo`, `sliding_block`, `ultimate_tictactoe` |
| geometry | 8 | `circle_theorem`, `graph_paper`, `triangle_relations`, `coordinate_plane`, `composite_shape`, `polygon_equation_diagram`, `function_panels`, `sector` |
| graph | 2 | `node_link`, `binary_tree` |
| icons | 3 | `named_field`, `reference_canvas`, `sequence_strip` |
| illustrations | 2 | `pixel_village`, `rpg_tactical_map` |
| symbolic | 3 | `music_staff`, `clock`, `truth_table` |
| pages | 4 | `infographic`, `mixed_infographic_page`, `profile_card_grid`, `step_list` |
| physics | 3 | `electrostatic_field`, `motion_graph`, `ray_optics` |
| puzzles | 3 | `raven_matrix`, `voxel_cube`, `arithmetic_panel` |
| three_d | 3 | `object_scene`, `object_cluster`, `conveyor` |

## Candidate Task-Level Test Split

This is a diversity-audited candidate manifest, not the final frozen split. It
is generated from the current active inventory. `test_new_scene` holds out
every active task in the listed scene. `test_known_scene` holds out one
objective from a scene that should remain represented in training by other
objectives. Known-scene candidates were selected to vary objective contracts
within each domain instead of taking the first task from each scene.

### charts

- `test_known_scene` candidates (9):
  - `single_series`: `task_charts__single_series__remaining_mean_after_removal`
  - `region_map`: `task_charts__region_map__named_region_set_total_value`
  - `curve_panels`: `task_charts__curve_panels__curve_intersection_count`
  - `dashboard`: `task_charts__dashboard__source_rank_target_value`
  - `combo_mark`: `task_charts__combo_mark__dual_threshold_condition_count`
  - `table`: `task_charts__table__filtered_column_mean`
  - `composition_panels`: `task_charts__composition_panels__top_k_by_segment_then_sum_other_segment_count`
  - `multiseries`: `task_charts__multiseries__ranked_pair_ratio_extremum_label`
  - `pictogram`: `task_charts__pictogram__target_value_nearest_category_label`
- `test_new_scene` candidates (10):
  - `annotated_series`: `task_charts__annotated_series__callout_endpoint_change_value`
  - `radial_sankey`: `task_charts__radial_sankey__dominant_endpoint_label`
  - `radial_sankey`: `task_charts__radial_sankey__transfer_total_value`
  - `contour_density`: `task_charts__contour_density__density_extremum_region_label`
  - `contour_density`: `task_charts__contour_density__density_threshold_region_count`
  - `contour_density`: `task_charts__contour_density__reference_distance_extremum_label`
  - `contour_density`: `task_charts__contour_density__spread_extremum_region_label`
  - `surface_3d`: `task_charts__surface_3d__panel_variation_label`
  - `surface_3d`: `task_charts__surface_3d__reference_nearest_label`
  - `surface_3d`: `task_charts__surface_3d__series_trend_label`

### games

- `test_known_scene` candidates (9):
  - `cards`: `task_games__cards__missing_card_to_complete_hand_label`
  - `chess`: `task_games__chess__king_escape_square_count`
  - `dominoes`: `task_games__dominoes__longest_chain_length_value`
  - `tetris`: `task_games__tetris__line_clear_count`
  - `space_shooter`: `task_games__space_shooter__safe_lane_count`
  - `solitaire`: `task_games__solitaire__foundation_ready_count`
  - `bingo`: `task_games__bingo__near_complete_line_count`
  - `sliding_block`: `task_games__sliding_block__sliding_block_blocker_count`
  - `ultimate_tictactoe`: `task_games__ultimate_tictactoe__macro_threat_board_count`
- `test_new_scene` candidates (8):
  - `backgammon`: `task_games__backgammon__destination_count`
  - `backgammon`: `task_games__backgammon__point_state_count`
  - `pinball_table`: `task_games__pinball_table__first_hit_object_label`
  - `pinball_table`: `task_games__pinball_table__scoreable_object_count`
  - `mancala_pit_board`: `task_games__mancala_pit_board__post_sow_pit_count_value`
  - `mancala_pit_board`: `task_games__mancala_pit_board__sowing_landing_option_label`
  - `tic_tac_toe_3d`: `task_games__tic_tac_toe_3d__layer_piece_count`
  - `tic_tac_toe_3d`: `task_games__tic_tac_toe_3d__winning_move_cell_label`

### geometry

- `test_known_scene` candidates (8):
  - `circle_theorem`: `task_geometry__circle_theorem__multi_step_angle_value`
  - `graph_paper`: `task_geometry__graph_paper__polygon_area_value`
  - `triangle_relations`: `task_geometry__triangle_relations__similar_triangles_side_length`
  - `coordinate_plane`: `task_geometry__coordinate_plane__rotated_point_label`
  - `composite_shape`: `task_geometry__composite_shape__rectangle_triangle_cutout_area`
  - `polygon_equation_diagram`: `task_geometry__polygon_equation_diagram__side_expression_perimeter_value`
  - `function_panels`: `task_geometry__function_panels__x_axis_symmetry_label`
  - `sector`: `task_geometry__sector__sector_area_from_complement_angle_value`
- `test_new_scene` candidates (8):
  - `area_partition`: `task_geometry__area_partition__total_area_value`
  - `circle_centerline_overlap`: `task_geometry__circle_centerline_overlap__segment_length_value`
  - `cone_net`: `task_geometry__cone_net__base_radius_from_sector_angle`
  - `cone_net`: `task_geometry__cone_net__height_from_sector_angle`
  - `solid_cross_section`: `task_geometry__solid_cross_section__cone_parallel_slice_area`
  - `solid_cross_section`: `task_geometry__solid_cross_section__square_pyramid_parallel_slice_area`
  - `bearing_route`: `task_geometry__bearing_route__endpoint_position_label`
  - `bearing_route`: `task_geometry__bearing_route__final_bearing_value`

### graph

- `test_known_scene` candidates (2):
  - `node_link`: `task_graph__node_link__mst_weight`
  - `binary_tree`: `task_graph__binary_tree__traversal_kth_label`
- `test_new_scene` candidates (4):
  - `flow_network`: `task_graph__flow_network__max_flow_value`
  - `flow_network`: `task_graph__flow_network__min_cut_edge_count`
  - `pedigree_chart`: `task_graph__pedigree_chart__relatedness_coefficient_label`
  - `pedigree_chart`: `task_graph__pedigree_chart__relationship_label`

### icons

- `test_known_scene` candidates (3):
  - `named_field`: `task_icons__named_field__counterfactual_attribute_count`
  - `reference_canvas`: `task_icons__reference_canvas__reference_type_color_rotation_match_count`
  - `sequence_strip`: `task_icons__sequence_strip__rotation_progression_completion_label`
- `test_new_scene` candidates (2):
  - `icon_cutout`: `task_icons__icon_cutout__partial_match_label`
  - `venn_field`: `task_icons__venn_field__scoped_attribute_count`

### illustrations

- `test_known_scene` candidates (2):
  - `pixel_village`: `task_illustrations__pixel_village__territory_object_count`
  - `rpg_tactical_map`: `task_illustrations__rpg_tactical_map__movement_sequence_endpoint_label`
- `test_new_scene` candidates (4):
  - `isometric_harbor`: `task_illustrations__isometric_harbor__boat_heading_status_count`
  - `isometric_harbor`: `task_illustrations__isometric_harbor__boat_mooring_status_count`
  - `isometric_harbor`: `task_illustrations__isometric_harbor__boat_side_count`
  - `isometric_harbor`: `task_illustrations__isometric_harbor__shoreline_nearest_boat_label`

### symbolic

- `test_known_scene` candidates (3):
  - `music_staff`: `task_symbolic__music_staff__interval_name_label`
  - `clock`: `task_symbolic__clock__elapsed_time_value`
  - `truth_table`: `task_symbolic__truth_table__satisfying_row_count`
- `test_new_scene` candidates (3):
  - `braille_cell`: `task_symbolic__braille_cell__braille_word_read_label`
  - `braille_cell`: `task_symbolic__braille_cell__matching_pattern_label`
  - `braille_cell`: `task_symbolic__braille_cell__word_braille_match_label`

### pages

- `test_known_scene` candidates (4):
  - `infographic`: `task_pages__infographic__section_extrema_arithmetic_value`
  - `mixed_infographic_page`: `task_pages__mixed_infographic_page__module_two_field_condition_item_label`
  - `profile_card_grid`: `task_pages__profile_card_grid__value_for_named_profile_field`
  - `step_list`: `task_pages__step_list__step_after_named_step_label`
- `test_new_scene` candidates (4):
  - `schema`: `task_pages__schema__field_role_count`
  - `schema`: `task_pages__schema__relationship_cardinality_label`
  - `schema`: `task_pages__schema__relationship_count`
  - `schema`: `task_pages__schema__relationship_endpoint_label`

### physics

- `test_known_scene` candidates (3):
  - `electrostatic_field`: `task_physics__electrostatic_field__potential_value`
  - `motion_graph`: `task_physics__motion_graph__speed_change_state_choice`
  - `ray_optics`: `task_physics__ray_optics__ray_target_hit_count`
- `test_new_scene` candidates (2):
  - `collision`: `task_physics__collision__sticky_collision_direction_choice`
  - `collision`: `task_physics__collision__sticky_collision_speed_value`

### puzzles

- `test_known_scene` candidates (3):
  - `raven_matrix`: `task_puzzles__raven_matrix__raven_set_operation_label`
  - `voxel_cube`: `task_puzzles__voxel_cube__cube_visible_projection_count`
  - `arithmetic_panel`: `task_puzzles__arithmetic_panel__vertical_arithmetic_hidden_digit_value`
- `test_new_scene` candidates (3):
  - `sheet_transform`: `task_puzzles__sheet_transform__fold_cut_result_label`
  - `sheet_transform`: `task_puzzles__sheet_transform__fold_projection_result_label`
  - `sheet_transform`: `task_puzzles__sheet_transform__overlay_union_result_label`

### three_d

- `test_known_scene` candidates (3):
  - `object_scene`: `task_three_d__object_scene__occlusion_order_label`
  - `object_cluster`: `task_three_d__object_cluster__multi_attribute_xor_count`
  - `conveyor`: `task_three_d__conveyor__color_ordered_adjacent_pair_count`
- `test_new_scene` candidates (3):
  - `street`: `task_three_d__street__intersection_nearest_label`
  - `street`: `task_three_d__street__lane_ahead_object_label`
  - `street`: `task_three_d__street__same_road_arm_reference_label`

## Final Manifest Rules

When the active task surface is finalized, generate explicit split manifests:

```text
rlvr_train_tasks.json
rlvr_test_known_scene_tasks.json
rlvr_test_new_scene_tasks.json
rlvr_test_tasks.json
```

Each manifest row should include:

```json
{
  "task_id": "task_<domain>__<scene_id>__<objective_contract>",
  "domain": "<domain>",
  "scene_id": "<scene_id>",
  "split": "train | test_known_scene | test_new_scene",
  "holdout_reason": "...",
  "review_status": "...",
  "solve_rate_status": "..."
}
```

Hard constraints for manifest generation:

1. A `test_new_scene` scene must have zero tasks in train.
2. A `test_known_scene` task's scene must have at least one train task, and
   preferably at least two.
3. No task can appear in more than one split.
4. Every domain must have at least five test tasks.
5. The final test set should be exactly `100` tasks unless the user explicitly
   changes the evaluation size.
6. If final domain counts differ from the target table, keep the same policy:
   minimum five per domain, allocate remaining test slots by proportional
   largest remainder, then choose whole-scene holdouts that land near a 50/50
   known/new split.

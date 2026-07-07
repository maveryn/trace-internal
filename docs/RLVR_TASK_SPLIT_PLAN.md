# TRACE RLVR Task Split

This document freezes the task-level TRACE RLVR train/test split for the 1000
active public tasks listed in `docs/ACTIVE_TASK_INVENTORY.md`.

Source snapshot:

- Inventory file: `docs/ACTIVE_TASK_INVENTORY.md`
- Inventory SHA-256:
  `a4e6b07c3fba8a24f5efddd70270e95615bfd962c17addf2b25fc31c3d56bd5b`
- Active tasks: `1000`
- Train tasks: `900`
- Test tasks: `100`

Train is the complement of the test tasks listed below. No separate train task
list is needed unless a dataset build script needs a materialized manifest.

## Split Semantics

- `test_seen_scene`: the task is held out, but at least one other task from the
  same scene remains in train.
- `test_unseen_scene`: every active task from that scene is held out, so the
  scene is absent from train.

The split is task-level, not sample-level. Generated instances for a test task
must stay in evaluation splits even if their visual style, prompt variant, or
generation parameters resemble train instances.

## Domain Allocation

| Domain | Active tasks | Train tasks | Test tasks | Seen-scene test | Unseen-scene test |
| --- | ---: | ---: | ---: | ---: | ---: |
| charts | 180 | 162 | 18 | 9 | 9 |
| games | 170 | 153 | 17 | 8 | 9 |
| geometry | 170 | 153 | 17 | 8 | 9 |
| graph | 60 | 54 | 6 | 2 | 4 |
| icons | 50 | 45 | 5 | 3 | 2 |
| illustrations | 60 | 54 | 6 | 2 | 4 |
| pages | 80 | 72 | 8 | 4 | 4 |
| physics | 50 | 45 | 5 | 3 | 2 |
| puzzles | 60 | 54 | 6 | 3 | 3 |
| symbolic | 60 | 54 | 6 | 3 | 3 |
| three_d | 60 | 54 | 6 | 3 | 3 |
| **Total** | **1000** | **900** | **100** | **48** | **52** |

The seen/unseen split is near-even rather than exactly 50/50 because unseen
scene holds must include whole scenes. For example, graph has no three-task
scene available for an exact 3/3 split.

## Unseen Scene Holds

| Domain | Held-out scenes | Test tasks |
| --- | --- | ---: |
| charts | `annotated_series`, `area`, `candlestick`, `matrix` | 9 |
| games | `backgammon`, `bowling`, `mancala_pit_board` | 9 |
| geometry | `area_partition`, `circle_centerline_overlap`, `circle_pair_tangents`, `cone_net`, `solid_cross_section`, `bearing_route` | 9 |
| graph | `flow_network`, `pedigree_chart` | 4 |
| icons | `venn_field` | 2 |
| illustrations | `isometric_harbor` | 4 |
| pages | `cycle`, `timeline` | 4 |
| physics | `collision` | 2 |
| puzzles | `sheet_transform` | 3 |
| symbolic | `braille_cell` | 3 |
| three_d | `street` | 3 |
| **Total** |  | **52** |

## Test Task Manifest

### charts

`test_seen_scene`

- `single_series`: `task_charts__single_series__remaining_mean_after_removal`
- `region_map`: `task_charts__region_map__named_region_set_total_value`
- `curve_panels`: `task_charts__curve_panels__curve_intersection_count`
- `dashboard`: `task_charts__dashboard__source_rank_target_value`
- `combo_mark`: `task_charts__combo_mark__dual_threshold_condition_count`
- `table`: `task_charts__table__filtered_column_mean`
- `composition_panels`: `task_charts__composition_panels__top_k_by_segment_then_sum_other_segment_count`
- `multiseries`: `task_charts__multiseries__ranked_pair_ratio_extremum_label`
- `pictogram`: `task_charts__pictogram__target_value_nearest_category_label`

`test_unseen_scene`

- `annotated_series`: `task_charts__annotated_series__callout_endpoint_change_value`
- `area`: `task_charts__area__interval_area_value`
- `area`: `task_charts__area__stacked_band_dominance_label`
- `area`: `task_charts__area__stacked_band_interval_sum_value`
- `candlestick`: `task_charts__candlestick__counterfactual_close_value`
- `candlestick`: `task_charts__candlestick__range_extremum_label`
- `matrix`: `task_charts__matrix__axis_extremum_label`
- `matrix`: `task_charts__matrix__off_diagonal_confusion_label`
- `matrix`: `task_charts__matrix__threshold_cell_count`

### games

`test_seen_scene`

- `cards`: `task_games__cards__missing_card_to_complete_hand_label`
- `chess`: `task_games__chess__king_escape_square_count`
- `dominoes`: `task_games__dominoes__longest_chain_length_value`
- `tetris`: `task_games__tetris__line_clear_count`
- `space_shooter`: `task_games__space_shooter__safe_lane_count`
- `solitaire`: `task_games__solitaire__foundation_ready_count`
- `sliding_block`: `task_games__sliding_block__sliding_block_blocker_count`
- `ultimate_tictactoe`: `task_games__ultimate_tictactoe__macro_threat_board_count`

`test_unseen_scene`

- `backgammon`: `task_games__backgammon__destination_count`
- `backgammon`: `task_games__backgammon__pip_count_value`
- `backgammon`: `task_games__backgammon__point_state_count`
- `bowling`: `task_games__bowling__first_pin_hit_label`
- `bowling`: `task_games__bowling__path_hit_count`
- `bowling`: `task_games__bowling__spare_path_label`
- `mancala_pit_board`: `task_games__mancala_pit_board__max_post_sow_option_label`
- `mancala_pit_board`: `task_games__mancala_pit_board__post_sow_pit_count_value`
- `mancala_pit_board`: `task_games__mancala_pit_board__sowing_landing_option_label`

### geometry

`test_seen_scene`

- `circle_theorem`: `task_geometry__circle_theorem__multi_step_angle_value`
- `graph_paper`: `task_geometry__graph_paper__polygon_area_value`
- `triangle_relations`: `task_geometry__triangle_relations__similar_triangles_side_length`
- `coordinate_plane`: `task_geometry__coordinate_plane__rotated_point_label`
- `composite_shape`: `task_geometry__composite_shape__rectangle_triangle_cutout_area`
- `polygon_equation_diagram`: `task_geometry__polygon_equation_diagram__side_expression_perimeter_value`
- `function_panels`: `task_geometry__function_panels__x_axis_symmetry_label`
- `sector`: `task_geometry__sector__sector_area_from_complement_angle_value`

`test_unseen_scene`

- `area_partition`: `task_geometry__area_partition__total_area_value`
- `circle_centerline_overlap`: `task_geometry__circle_centerline_overlap__segment_length_value`
- `circle_pair_tangents`: `task_geometry__circle_pair_tangents__external_tangent_segment_length_value`
- `cone_net`: `task_geometry__cone_net__base_radius_from_sector_angle`
- `cone_net`: `task_geometry__cone_net__height_from_sector_angle`
- `solid_cross_section`: `task_geometry__solid_cross_section__cone_parallel_slice_area`
- `solid_cross_section`: `task_geometry__solid_cross_section__square_pyramid_parallel_slice_area`
- `bearing_route`: `task_geometry__bearing_route__endpoint_position_label`
- `bearing_route`: `task_geometry__bearing_route__final_bearing_value`

### graph

`test_seen_scene`

- `node_link`: `task_graph__node_link__mst_weight`
- `binary_tree`: `task_graph__binary_tree__traversal_kth_label`

`test_unseen_scene`

- `flow_network`: `task_graph__flow_network__max_flow_value`
- `flow_network`: `task_graph__flow_network__min_cut_edge_count`
- `pedigree_chart`: `task_graph__pedigree_chart__relatedness_coefficient_label`
- `pedigree_chart`: `task_graph__pedigree_chart__relationship_label`

### icons

`test_seen_scene`

- `named_field`: `task_icons__named_field__reference_distance_rank_label`
- `reference_canvas`: `task_icons__reference_canvas__reference_metric_relation_count`
- `sequence_strip`: `task_icons__sequence_strip__rotation_progression_completion_label`

`test_unseen_scene`

- `venn_field`: `task_icons__venn_field__same_region_as_reference_count`
- `venn_field`: `task_icons__venn_field__scoped_attribute_count`

### illustrations

`test_seen_scene`

- `pixel_village`: `task_illustrations__pixel_village__territory_object_count`
- `rpg_tactical_map`: `task_illustrations__rpg_tactical_map__movement_sequence_endpoint_label`

`test_unseen_scene`

- `isometric_harbor`: `task_illustrations__isometric_harbor__boat_heading_status_count`
- `isometric_harbor`: `task_illustrations__isometric_harbor__boat_mooring_status_count`
- `isometric_harbor`: `task_illustrations__isometric_harbor__boat_side_count`
- `isometric_harbor`: `task_illustrations__isometric_harbor__shoreline_nearest_boat_label`

### pages

`test_seen_scene`

- `infographic`: `task_pages__infographic__global_metric_ranked_item_label`
- `mixed_infographic_page`: `task_pages__mixed_infographic_page__module_field_ranked_item_label`
- `profile_card_grid`: `task_pages__profile_card_grid__filtered_ranked_profile_label`
- `step_list`: `task_pages__step_list__relative_offset_step_label`

`test_unseen_scene`

- `cycle`: `task_pages__cycle__offset_stage_label`
- `timeline`: `task_pages__timeline__date_threshold_event_count`
- `timeline`: `task_pages__timeline__interval_membership_count`
- `timeline`: `task_pages__timeline__relative_position_event_label`

### physics

`test_seen_scene`

- `electrostatic_field`: `task_physics__electrostatic_field__zero_field_point_label`
- `motion_graph`: `task_physics__motion_graph__interval_displacement_value`
- `ray_optics`: `task_physics__ray_optics__ray_target_hit_count`

`test_unseen_scene`

- `collision`: `task_physics__collision__sticky_collision_direction_choice`
- `collision`: `task_physics__collision__sticky_collision_speed_value`

### puzzles

`test_seen_scene`

- `raven_matrix`: `task_puzzles__raven_matrix__raven_feature_binding_label`
- `voxel_cube`: `task_puzzles__voxel_cube__cube_projection_match_label`
- `arithmetic_panel`: `task_puzzles__arithmetic_panel__number_wall_value`

`test_unseen_scene`

- `sheet_transform`: `task_puzzles__sheet_transform__fold_cut_result_label`
- `sheet_transform`: `task_puzzles__sheet_transform__fold_projection_result_label`
- `sheet_transform`: `task_puzzles__sheet_transform__overlay_union_result_label`

### symbolic

`test_seen_scene`

- `music_staff`: `task_symbolic__music_staff__note_name_label`
- `clock`: `task_symbolic__clock__elapsed_time_value`
- `truth_table`: `task_symbolic__truth_table__satisfying_row_count`

`test_unseen_scene`

- `braille_cell`: `task_symbolic__braille_cell__braille_word_read_label`
- `braille_cell`: `task_symbolic__braille_cell__matching_pattern_label`
- `braille_cell`: `task_symbolic__braille_cell__word_braille_match_label`

### three_d

`test_seen_scene`

- `object_scene`: `task_three_d__object_scene__reference_nearest_label`
- `object_cluster`: `task_three_d__object_cluster__total_object_count`
- `conveyor`: `task_three_d__conveyor__scoped_belt_object_type_count`

`test_unseen_scene`

- `street`: `task_three_d__street__intersection_nearest_label`
- `street`: `task_three_d__street__lane_ahead_object_label`
- `street`: `task_three_d__street__same_road_arm_reference_label`

## Validation Rules

Any materialized split manifest or dataset build using this split must enforce:

1. Exactly `1000` active task ids are present in the source inventory.
2. Exactly `100` task ids are assigned to test.
3. Exactly `900` active task ids remain in train by complement.
4. Test task ids are unique and all exist in the active inventory.
5. Every `test_unseen_scene` scene has all active tasks from that scene in
   test and no task from that scene in train.
6. Every `test_seen_scene` task's scene retains at least one active train task.
7. If the active inventory changes, regenerate this split or explicitly freeze
   the old inventory before building datasets from it.

# Trace RLVR Task Split

This document freezes the task-level Trace RLVR train/test split for the 1000
active public tasks listed in `docs/ACTIVE_TASK_INVENTORY.md`.

Source snapshot:

- Split id: `trace_rlvr_task_split_v1`
- Status: finalized
- Finalized date: `2026-07-07`
- Inventory file: `docs/ACTIVE_TASK_INVENTORY.md`
- Inventory SHA-256:
  `a4e6b07c3fba8a24f5efddd70270e95615bfd962c17addf2b25fc31c3d56bd5b`
- Active tasks: `1000`
- Train tasks: `900`
- Test tasks: `100`

Train is the complement of the test tasks listed below. No separate train task
list is needed unless a dataset build script needs a materialized manifest. Any
future task-surface change should either preserve this frozen v1 split against
the recorded inventory or create a new explicitly named split.

## Split Semantics

- `test_seen_scene`: the task is held out, but at least one other task from the
  same scene remains in train.
- `test_unseen_scene`: every active task from that scene is held out, so the
  scene is absent from train.

The split is task-level, not sample-level. Generated instances for a test task
must stay in evaluation splits even if their visual style, prompt variant, or
generation parameters resemble train instances.

## Export Defaults

The current RLVR dataset export for this split uses seed `42`, stores both
answer-only and answer-plus-annotation prompt fields, and caps embedded images
at `1_280_000` pixels.

- Train export: `900` train tasks x `256` samples per task = `230,400` rows.
- Validation export: `100` test tasks x `25` samples per task = `2,500` rows.

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
| charts | `hexbin_density`, `error_interval`, `matrix`, `radial_sankey` | 9 |
| games | `battleship`, `minigolf`, `slot_machine` | 9 |
| geometry | `area_partition`, `circle_centerline_overlap`, `circle_pair_tangents`, `paper_fold`, `solid_cross_section`, `bearing_route` | 9 |
| graph | `pipe_network` | 4 |
| icons | `venn_field` | 2 |
| illustrations | `isometric_harbor` | 4 |
| pages | `cycle`, `timeline` | 4 |
| physics | `analog_meter`, `electromagnetic_induction` | 2 |
| puzzles | `polyomino_assembly` | 3 |
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

- `hexbin_density`: `task_charts__hexbin_density__threshold_bin_count`
- `error_interval`: `task_charts__error_interval__interval_width_rank_label`
- `error_interval`: `task_charts__error_interval__reference_containment_count`
- `error_interval`: `task_charts__error_interval__reference_exclusion_side_count`
- `matrix`: `task_charts__matrix__axis_extremum_label`
- `matrix`: `task_charts__matrix__off_diagonal_confusion_label`
- `matrix`: `task_charts__matrix__threshold_cell_count`
- `radial_sankey`: `task_charts__radial_sankey__dominant_endpoint_label`
- `radial_sankey`: `task_charts__radial_sankey__transfer_total_value`

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

- `battleship`: `task_games__battleship__last_ship_cell_label`
- `battleship`: `task_games__battleship__remaining_ship_shape_label`
- `battleship`: `task_games__battleship__ship_cell_status_count`
- `battleship`: `task_games__battleship__ship_status_count`
- `minigolf`: `task_games__minigolf__first_obstacle_label`
- `minigolf`: `task_games__minigolf__shot_path_label`
- `slot_machine`: `task_games__slot_machine__paytable_score_value`
- `slot_machine`: `task_games__slot_machine__reel_completion_label`
- `slot_machine`: `task_games__slot_machine__winning_payline_count`

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
- `paper_fold`: `task_geometry__paper_fold__folded_segment_length_value`
- `paper_fold`: `task_geometry__paper_fold__paper_fold_angle_value`
- `solid_cross_section`: `task_geometry__solid_cross_section__cone_parallel_slice_area`
- `solid_cross_section`: `task_geometry__solid_cross_section__square_pyramid_parallel_slice_area`
- `bearing_route`: `task_geometry__bearing_route__endpoint_position_label`
- `bearing_route`: `task_geometry__bearing_route__final_bearing_value`

### graph

`test_seen_scene`

- `node_link`: `task_graph__node_link__mst_weight`
- `binary_tree`: `task_graph__binary_tree__traversal_kth_label`

`test_unseen_scene`

- `pipe_network`: `task_graph__pipe_network__bridge_count`
- `pipe_network`: `task_graph__pipe_network__pipe_exact_distance_count`
- `pipe_network`: `task_graph__pipe_network__pipe_reachable_junction_count`
- `pipe_network`: `task_graph__pipe_network__shortest_path_length`

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
- `calendar_event_grid`: `task_pages__calendar_event_grid__busiest_date_label`
- `schema`: `task_pages__schema__join_path_length_value`

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

- `analog_meter`: `task_physics__analog_meter__meter_readout_value`
- `electromagnetic_induction`: `task_physics__electromagnetic_induction__induced_current_direction_count`

### puzzles

`test_seen_scene`

- `raven_matrix`: `task_puzzles__raven_matrix__raven_feature_binding_label`
- `voxel_cube`: `task_puzzles__voxel_cube__cube_projection_match_label`
- `arithmetic_panel`: `task_puzzles__arithmetic_panel__number_wall_value`

`test_unseen_scene`

- `polyomino_assembly`: `task_puzzles__polyomino_assembly__composition_result_label`
- `polyomino_assembly`: `task_puzzles__polyomino_assembly__decomposition_pair_label`
- `polyomino_assembly`: `task_puzzles__polyomino_assembly__hole_fill_piece_label`

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

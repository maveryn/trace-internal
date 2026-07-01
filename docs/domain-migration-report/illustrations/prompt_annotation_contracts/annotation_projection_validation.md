# Annotation Projection Validation

- sampled instances: `74`
- query ids covered: `74`
- annotation projection/geometry issues: `0`
- annotation types: `{'bbox': 19, 'bbox_map': 10, 'bbox_set': 37, 'point_set': 7, 'point_set_map': 1}`
- tasks with incomplete coverage or generation errors: `0`

## Coverage

| task | expected query ids | collected counts | generated | issues |
| --- | --- | --- | ---: | --- |
| task_illustrations__construction_site__equipment_zone_count | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__construction_site__missing_patch_label | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__construction_site__rotated_tile_label | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__construction_site__worker_attribute_count | `hard_hat_color_worker_count, vest_color_worker_count` | `{'hard_hat_color_worker_count': 1, 'vest_color_worker_count': 1}` | 2 | `` |
| task_illustrations__environment__crossing_feature_count | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__environment__feature_relation_object_count | `above_feature, below_feature, on_feature` | `{'above_feature': 1, 'below_feature': 1, 'on_feature': 1}` | 3 | `` |
| task_illustrations__environment__lit_window_count | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__environment__missing_patch_label | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__environment__rotated_tile_label | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__indoor_room__furniture_side_count | `left_side, right_side` | `{'left_side': 1, 'right_side': 1}` | 2 | `` |
| task_illustrations__indoor_room__missing_patch_label | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__indoor_room__rotated_tile_label | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__indoor_room__surface_object_count | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__indoor_room__swapped_tile_pair_label | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__isometric_farmstead__farmer_same_level_tile_label | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__isometric_farmstead__highest_terrain_tile_count | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__isometric_farmstead__terrain_elevation_extremum_label | `highest_terrain_tile, lowest_terrain_tile` | `{'highest_terrain_tile': 1, 'lowest_terrain_tile': 1}` | 2 | `` |
| task_illustrations__isometric_farmstead__terrain_level_object_count | `highest_terrain_object_count, lowest_terrain_object_count` | `{'highest_terrain_object_count': 1, 'lowest_terrain_object_count': 1}` | 2 | `` |
| task_illustrations__isometric_harbor__boat_heading_status_count | `away_from_shoreline_boat_count, toward_shoreline_boat_count` | `{'away_from_shoreline_boat_count': 1, 'toward_shoreline_boat_count': 1}` | 2 | `` |
| task_illustrations__isometric_harbor__boat_mooring_status_count | `moored_boat_count, open_water_boat_count` | `{'moored_boat_count': 1, 'open_water_boat_count': 1}` | 2 | `` |
| task_illustrations__isometric_harbor__boat_side_count | `left_side_boat_count, right_side_boat_count` | `{'left_side_boat_count': 1, 'right_side_boat_count': 1}` | 2 | `` |
| task_illustrations__isometric_harbor__shoreline_nearest_boat_label | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__isometric_quarry__highest_terrain_tile_count | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__isometric_quarry__terrain_elevation_extremum_label | `highest_terrain_tile, lowest_terrain_tile` | `{'highest_terrain_tile': 1, 'lowest_terrain_tile': 1}` | 2 | `` |
| task_illustrations__isometric_quarry__terrain_level_object_count | `highest_terrain_object_count, lowest_terrain_object_count` | `{'highest_terrain_object_count': 1, 'lowest_terrain_object_count': 1}` | 2 | `` |
| task_illustrations__isometric_quarry__worker_same_level_tile_label | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__library__books_in_section_count | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__library__filtered_book_in_section_count | `book_color_in_section_count, horizontal_book_in_section_count, upright_book_in_section_count` | `{'book_color_in_section_count': 1, 'horizontal_book_in_section_count': 1, 'upright_book_in_section_count': 1}` | 3 | `` |
| task_illustrations__library__missing_patch_label | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__library__rotated_tile_label | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__library__swapped_tile_pair_label | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__park_playground__jigsaw_arrangement_label | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__park_playground__missing_patch_label | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__park_playground__person_count | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__park_playground__playground_equipment_count | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__park_playground__rotated_tile_label | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__park_playground__swapped_tile_pair_label | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__pixel_village__missing_patch_label | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__pixel_village__object_type_count | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__pixel_village__person_path_count | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__pixel_village__river_side_object_count | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__pixel_village__rotated_tile_label | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__pixel_village__swapped_tile_pair_label | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__pixel_village__territory_object_count | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__rpg_dungeon__missing_patch_label | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__rpg_dungeon__monster_chamber_count | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__rpg_dungeon__reachable_chest_count | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__rpg_dungeon__safe_reachable_chest_count | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__rpg_house__door_state_count | `closed_door_count, open_door_count` | `{'closed_door_count': 1, 'open_door_count': 1}` | 2 | `` |
| task_illustrations__rpg_house__missing_patch_label | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__rpg_house__reachable_room_count | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__rpg_house__room_count | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__rpg_house__swapped_tile_pair_label | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__rpg_tactical_map__counterfactual_terrain_conversion_cost_value | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__rpg_tactical_map__movement_cost_value | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__rpg_tactical_map__movement_reachable_tile_count | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__rpg_tactical_map__movement_reachable_tile_label | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__rpg_tactical_map__movement_sequence_endpoint_label | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__rpg_tactical_map__terrain_type_tile_count | `single` | `{'single': 1}` | 2 | `` |
| task_illustrations__rpg_tactical_map__water_barrier_unreachable_tile_label | `single` | `{'single': 1}` | 2 | `` |

## Issues

No issues found.

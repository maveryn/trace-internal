# Bbox Minimum-Side Audit From Existing Task Reviews

- Checked at: `2026-06-28T09:29:53Z`
- Review root: `review/task-reviews`
- Minimum required side: `24.0 px`
- Scenes: `12`
- Tasks: `60`
- Bbox-family runtime tasks: `55`
- Samples inspected: `6000`
- Bboxes inspected: `13960`
- Failing bbox tasks: `0`
- Invalid bbox tasks: `0`
- Missing review-artifact tasks: `0`
- Doc/runtime annotation mismatches: `0`

## Bbox-Family Task Observations

| Domain | Scene | Task | Runtime Type | Samples | Bboxes | Min W | Min H | Min Side | Status |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| illustrations | construction_site | `task_illustrations__construction_site__equipment_zone_count` | ['bbox_set'] | 100 | 209 | 132.143 | 70.4 | 70.4 | pass |
| illustrations | construction_site | `task_illustrations__construction_site__missing_patch_label` | ['bbox_map'] | 100 | 200 | 108 | 107.765 | 107.765 | pass |
| illustrations | construction_site | `task_illustrations__construction_site__rotated_tile_label` | ['bbox'] | 100 | 100 | 320 | 320 | 320 | pass |
| illustrations | construction_site | `task_illustrations__construction_site__worker_attribute_count` | ['bbox_set'] | 100 | 244 | 44.015 | 70.4 | 44.015 | pass |
| illustrations | environment | `task_illustrations__environment__crossing_feature_count` | ['bbox_set'] | 100 | 307 | 44 | 70.802 | 44 | pass |
| illustrations | environment | `task_illustrations__environment__feature_relation_object_count` | ['bbox_set'] | 100 | 703 | 24.4 | 29.16 | 24.4 | pass |
| illustrations | environment | `task_illustrations__environment__lit_window_count` | ['bbox_set'] | 100 | 309 | 26 | 26 | 26 | pass |
| illustrations | environment | `task_illustrations__environment__missing_patch_label` | ['bbox_map'] | 100 | 200 | 102.139 | 107.765 | 102.139 | pass |
| illustrations | environment | `task_illustrations__environment__rotated_tile_label` | ['bbox'] | 100 | 100 | 320 | 320 | 320 | pass |
| illustrations | indoor_room | `task_illustrations__indoor_room__furniture_side_count` | ['bbox_set'] | 100 | 323 | 27.2 | 28.831 | 27.2 | pass |
| illustrations | indoor_room | `task_illustrations__indoor_room__missing_patch_label` | ['bbox_map'] | 100 | 200 | 104.551 | 110.928 | 104.551 | pass |
| illustrations | indoor_room | `task_illustrations__indoor_room__rotated_tile_label` | ['bbox'] | 100 | 100 | 320 | 320 | 320 | pass |
| illustrations | indoor_room | `task_illustrations__indoor_room__surface_object_count` | ['bbox_set'] | 100 | 305 | 25.84 | 25.12 | 25.12 | pass |
| illustrations | indoor_room | `task_illustrations__indoor_room__swapped_tile_pair_label` | ['bbox_set'] | 100 | 200 | 266 | 266 | 266 | pass |
| illustrations | isometric_farmstead | `task_illustrations__isometric_farmstead__farmer_same_level_tile_label` | ['bbox'] | 100 | 100 | 60 | 30 | 30 | pass |
| illustrations | isometric_farmstead | `task_illustrations__isometric_farmstead__highest_terrain_tile_count` | ['bbox'] | 100 | 100 | 150 | 75 | 75 | pass |
| illustrations | isometric_farmstead | `task_illustrations__isometric_farmstead__terrain_elevation_extremum_label` | ['bbox'] | 100 | 100 | 60 | 30 | 30 | pass |
| illustrations | isometric_farmstead | `task_illustrations__isometric_farmstead__terrain_level_object_count` | ['bbox_set'] | 100 | 253 | 27.6 | 25.2 | 25.2 | pass |
| illustrations | isometric_harbor | `task_illustrations__isometric_harbor__boat_heading_status_count` | ['bbox_set'] | 100 | 282 | 71.908 | 40.954 | 40.954 | pass |
| illustrations | isometric_harbor | `task_illustrations__isometric_harbor__boat_mooring_status_count` | ['bbox_set'] | 100 | 329 | 28.318 | 24.5 | 24.5 | pass |
| illustrations | isometric_harbor | `task_illustrations__isometric_harbor__boat_side_count` | ['bbox_set'] | 100 | 244 | 75.166 | 42.583 | 42.583 | pass |
| illustrations | isometric_harbor | `task_illustrations__isometric_harbor__shoreline_nearest_boat_label` | ['bbox'] | 100 | 100 | 71.908 | 40.954 | 40.954 | pass |
| illustrations | isometric_quarry | `task_illustrations__isometric_quarry__highest_terrain_tile_count` | ['bbox'] | 100 | 100 | 150 | 75 | 75 | pass |
| illustrations | isometric_quarry | `task_illustrations__isometric_quarry__terrain_elevation_extremum_label` | ['bbox'] | 100 | 100 | 60 | 30 | 30 | pass |
| illustrations | isometric_quarry | `task_illustrations__isometric_quarry__terrain_level_object_count` | ['bbox_set'] | 100 | 250 | 31.2 | 28.224 | 28.224 | pass |
| illustrations | isometric_quarry | `task_illustrations__isometric_quarry__worker_same_level_tile_label` | ['bbox'] | 100 | 100 | 60 | 30 | 30 | pass |
| illustrations | library | `task_illustrations__library__missing_patch_label` | ['bbox_map'] | 100 | 200 | 111.655 | 107.765 | 107.765 | pass |
| illustrations | library | `task_illustrations__library__rotated_tile_label` | ['bbox'] | 100 | 100 | 320 | 320 | 320 | pass |
| illustrations | library | `task_illustrations__library__swapped_tile_pair_label` | ['bbox_set'] | 100 | 200 | 266 | 266 | 266 | pass |
| illustrations | park_playground | `task_illustrations__park_playground__jigsaw_arrangement_label` | ['bbox'] | 100 | 100 | 433.963 | 431.818 | 431.818 | pass |
| illustrations | park_playground | `task_illustrations__park_playground__missing_patch_label` | ['bbox_map'] | 100 | 200 | 109.544 | 108.581 | 108.581 | pass |
| illustrations | park_playground | `task_illustrations__park_playground__person_count` | ['bbox_set'] | 100 | 823 | 42.857 | 68.032 | 42.857 | pass |
| illustrations | park_playground | `task_illustrations__park_playground__playground_equipment_count` | ['bbox_set'] | 100 | 334 | 94.003 | 24.5 | 24.5 | pass |
| illustrations | park_playground | `task_illustrations__park_playground__rotated_tile_label` | ['bbox'] | 100 | 100 | 320 | 320 | 320 | pass |
| illustrations | park_playground | `task_illustrations__park_playground__swapped_tile_pair_label` | ['bbox_set'] | 100 | 200 | 266 | 266 | 266 | pass |
| illustrations | pixel_village | `task_illustrations__pixel_village__missing_patch_label` | ['bbox_map'] | 100 | 200 | 117.211 | 116.116 | 116.116 | pass |
| illustrations | pixel_village | `task_illustrations__pixel_village__object_type_count` | ['bbox_set'] | 100 | 361 | 48 | 48 | 48 | pass |
| illustrations | pixel_village | `task_illustrations__pixel_village__person_path_count` | ['bbox_set'] | 100 | 371 | 48 | 48 | 48 | pass |
| illustrations | pixel_village | `task_illustrations__pixel_village__river_side_object_count` | ['bbox_set'] | 100 | 300 | 48 | 48 | 48 | pass |
| illustrations | pixel_village | `task_illustrations__pixel_village__rotated_tile_label` | ['bbox'] | 100 | 100 | 336 | 336 | 336 | pass |
| illustrations | pixel_village | `task_illustrations__pixel_village__swapped_tile_pair_label` | ['bbox_set'] | 100 | 200 | 286.333 | 277.193 | 277.193 | pass |
| illustrations | pixel_village | `task_illustrations__pixel_village__territory_object_count` | ['bbox_set'] | 100 | 584 | 48 | 48 | 48 | pass |
| illustrations | rpg_dungeon | `task_illustrations__rpg_dungeon__missing_patch_label` | ['bbox_map'] | 100 | 200 | 116.069 | 111.846 | 111.846 | pass |
| illustrations | rpg_dungeon | `task_illustrations__rpg_dungeon__monster_chamber_count` | ['bbox_set'] | 100 | 249 | 48 | 48 | 48 | pass |
| illustrations | rpg_dungeon | `task_illustrations__rpg_dungeon__reachable_chest_count` | ['bbox_set'] | 100 | 224 | 96 | 48 | 48 | pass |
| illustrations | rpg_dungeon | `task_illustrations__rpg_dungeon__safe_reachable_chest_count` | ['bbox_set'] | 100 | 200 | 96 | 48 | 48 | pass |
| illustrations | rpg_house | `task_illustrations__rpg_house__missing_patch_label` | ['bbox_map'] | 100 | 200 | 110.764 | 111.846 | 110.764 | pass |
| illustrations | rpg_house | `task_illustrations__rpg_house__swapped_tile_pair_label` | ['bbox_set'] | 100 | 200 | 286.333 | 277.193 | 277.193 | pass |
| illustrations | rpg_tactical_map | `task_illustrations__rpg_tactical_map__counterfactual_terrain_conversion_cost_value` | ['bbox_map'] | 100 | 300 | 80 | 80 | 80 | pass |
| illustrations | rpg_tactical_map | `task_illustrations__rpg_tactical_map__movement_cost_value` | ['bbox_map'] | 100 | 200 | 80 | 80 | 80 | pass |
| illustrations | rpg_tactical_map | `task_illustrations__rpg_tactical_map__movement_reachable_tile_count` | ['bbox_set'] | 100 | 1044 | 80 | 80 | 80 | pass |
| illustrations | rpg_tactical_map | `task_illustrations__rpg_tactical_map__movement_reachable_tile_label` | ['bbox'] | 100 | 100 | 80 | 80 | 80 | pass |
| illustrations | rpg_tactical_map | `task_illustrations__rpg_tactical_map__movement_sequence_endpoint_label` | ['bbox'] | 100 | 100 | 80 | 80 | 80 | pass |
| illustrations | rpg_tactical_map | `task_illustrations__rpg_tactical_map__terrain_type_tile_count` | ['bbox_set'] | 100 | 912 | 80 | 80 | 80 | pass |
| illustrations | rpg_tactical_map | `task_illustrations__rpg_tactical_map__water_barrier_unreachable_tile_label` | ['bbox'] | 100 | 100 | 80 | 80 | 80 | pass |

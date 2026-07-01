# Prompt Concision Audit

- rendered prompts: `148`
- tasks covered: `60`
- observed query ids covered: `74`

## Variant Coverage

- tasks with incomplete query ids or generation errors: `0`

| task | expected_query_ids | collected_query_id_counts | generated | issues |
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

## Longest Prompts

### task_illustrations__rpg_tactical_map__counterfactual_terrain_conversion_cost_value / answer_and_annotation / sample 6238966390302142

- `query_id`: `single`
- `instance_seed`: `6238966390302142`
- `word_count`: `167`
- `body_word_count`: `96`

```text
The scene shows a grid-based tactical map from above, with a blue unit, varied terrain, and one marked destination tile. The blue unit starts on its current tile. Grass, roads, and bridges cost 1 movement point; forests cost 2; mountains cost 3; water cannot be entered. Moves are only up, down, left, or right. Before moving, exactly one water, mountain, or forest tile may be changed into a road tile. After that conversion, how many movement points are needed to reach the marked destination tile using the cheapest path?
Return JSON with keys "annotation" and "answer".
Format for the "annotation" field: set "annotation" to an object with keys "player_cell", "target_cell", and "changed_cell", each mapping to one [x0, y0, x1, y1] pixel bounding box around that tile.
Format for the "answer" field: set "answer" to the fewest number of movement points needed after the best single terrain-to-road conversion.
Example JSON:
{"annotation":{"player_cell":[160,320,240,400],"target_cell":[320,320,400,400],"changed_cell":[240,320,320,400]},"answer":5}
```

### task_illustrations__rpg_tactical_map__movement_cost_value / answer_and_annotation / sample 5297355580750692

- `query_id`: `single`
- `instance_seed`: `5297355580750692`
- `word_count`: `143`
- `body_word_count`: `78`

```text
This illustration shows a tactical RPG grid map where a blue unit can move across terrain toward the marked target tile. The blue unit starts on its current tile. Grass, roads, and bridges cost 1 movement point; forests cost 2; mountains cost 3; water cannot be entered. Moves are only up, down, left, or right. How many movement points are needed to reach the marked destination tile using the cheapest path?
Return JSON with keys "annotation" and "answer".
Format for the "annotation" field: set "annotation" to an object with keys "player_cell" and "target_cell", each mapping to one [x0, y0, x1, y1] pixel bounding box around that tile.
Format for the "answer" field: set "answer" to the fewest number of movement points needed to reach the marked target tile.
Example JSON:
{"annotation":{"player_cell":[160,320,240,400],"target_cell":[320,320,400,400]},"answer":7}
```

### task_illustrations__rpg_tactical_map__movement_reachable_tile_count / answer_and_annotation / sample 4239604344828419

- `query_id`: `single`
- `instance_seed`: `4239604344828419`
- `word_count`: `121`
- `body_word_count`: `67`

```text
This illustration shows a tactical RPG grid map where a blue unit can move across terrain. With up to 2 movement points, count the tiles the blue unit can reach, excluding its starting tile. Grass, roads, and bridges cost 1 movement point; forests cost 2; mountains cost 3; water cannot be entered. Moves are only up, down, left, or right.
Return JSON with keys "annotation" and "answer".
Final answer format: set "answer" to the number of reachable tiles, excluding the blue unit's starting tile.
Annotation format: set "annotation" to a list of [x0, y0, x1, y1] pixel bounding boxes around each counted reachable tile.
Example JSON:
{"annotation":[[240,160,320,240],[320,160,400,240],[240,240,320,320]],"answer":3}
```

### task_illustrations__rpg_tactical_map__counterfactual_terrain_conversion_cost_value / answer_only / sample 6238966390302142

- `query_id`: `single`
- `instance_seed`: `6238966390302142`
- `word_count`: `116`
- `body_word_count`: `94`

```text
The scene shows a grid-based tactical map from above, with a blue unit, varied terrain, and one marked destination tile. The blue unit starts on its current tile. Grass, roads, and bridges cost 1 movement point; forests cost 2; mountains cost 3; water cannot be entered. Moves are only up, down, left, or right. Before moving, exactly one water, mountain, or forest tile may be changed into a road tile. After that conversion, how many movement points are needed to reach the marked destination tile using the cheapest path?
Return JSON with key "answer".
Answer format: set "answer" to the fewest number of movement points needed after the best single terrain-to-road conversion.
Example JSON:
{"answer":5}
```

### task_illustrations__rpg_tactical_map__movement_reachable_tile_label / answer_and_annotation / sample 3336864314380235

- `query_id`: `single`
- `instance_seed`: `3336864314380235`
- `word_count`: `110`
- `body_word_count`: `72`

```text
The canvas contains a top-down RPG battle map with grass, roads, forests, water, bridges, mountains, one blue unit, and lettered tiles. The blue unit starts on its current tile. It has 6 movement points. Grass, roads, and bridges cost 1 movement point; forests cost 2; mountains cost 3; water cannot be entered. Moves are only up, down, left, or right. Which lettered tile is reachable?
Return JSON with keys "annotation" and "answer".
Final answer format: set "answer" to the letter of the reachable tile.
Annotation format: set "annotation" to one [x0, y0, x1, y1] pixel bounding box around the selected tile.
Example JSON:
{"annotation":[320,160,400,240],"answer":"C"}
```

### task_illustrations__rpg_dungeon__safe_reachable_chest_count / answer_and_annotation / sample 427078276929202

- `query_id`: `single`
- `instance_seed`: `427078276929202`
- `word_count`: `106`
- `body_word_count`: `47`

```text
The scene shows a top-down RPG-style dungeon map with walkable floor, blocked passages, treasure chests, and monsters inside some chambers. How many treasure chests can the player reach without passing through boulder-blocked paths, after excluding chests in chambers with monsters?
Return JSON with keys "annotation" and "answer".
Final answer format: set "answer" to the number of reachable treasure chests after excluding chests in monster chambers.
Annotation format: set "annotation" to a list containing one [x0, y0, x1, y1] bounding box around each counted chest; use an empty list when the answer is 0.
Example JSON:
{"annotation":[[236,156,284,204],[596,156,644,204]],"answer":2}
```

### task_illustrations__rpg_house__reachable_room_count / answer_and_annotation / sample 1974223144035174

- `query_id`: `single`
- `instance_seed`: `1974223144035174`
- `word_count`: `105`
- `body_word_count`: `42`

```text
The canvas contains a top-down RPG house map with enclosed rooms, walls, and doorways. Starting from the room with the player, how many other rooms can the player reach by passing only through open doors?
Return JSON with keys "annotation" and "answer".
Annotation format: set "annotation" to an object with keys "player" and "reachable_rooms"; "player" contains one [x, y] point on the player, and "reachable_rooms" contains one [x, y] point near the center of each counted room.
Answer field: set "answer" to the number of other rooms reachable from the player's room.
Example JSON:
{"annotation":{"player":[[420,360]],"reachable_rooms":[[260,180],[620,180]]},"answer":2}
```

### task_illustrations__rpg_tactical_map__water_barrier_unreachable_tile_label / answer_and_annotation / sample 4375500550605400

- `query_id`: `single`
- `instance_seed`: `4375500550605400`
- `word_count`: `105`
- `body_word_count`: `66`

```text
The scene shows a grid-based tactical map from above, with a blue unit, one water barrier crossing the map, and lettered target tiles. Using only the water-blocking rule, choose the lettered tile that cannot be reached from the blue unit. Water tiles cannot be crossed; all non-water tiles can be crossed. Moves are only up, down, left, or right.
Return JSON with keys "annotation" and "answer".
Final answer format: set "answer" to the letter of the unreachable tile.
Annotation format: set "annotation" to one [x0, y0, x1, y1] pixel bounding box around the selected unreachable tile.
Example JSON:
{"annotation":[480,160,560,240],"answer":"D"}
```

### task_illustrations__environment__feature_relation_object_count / answer_and_annotation / sample 7624335182456

- `query_id`: `above_feature`
- `instance_seed`: `7624335182456`
- `word_count`: `102`
- `body_word_count`: `32`

```text
The scene shows a city canal setting with foreground objects placed around visible roads, rivers, buildings, or crossings. How many foreground objects are above the river? If none are there, answer 0.
Format for the "annotation" field: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around each counted foreground object above the river; use [] if none match.
Format for the "answer" field: set "answer" to the count of foreground objects above the river as an integer, using 0 if none match.
Example JSON:
{"annotation":[[238,390,322,474],[468,460,560,556]],"answer":2}
```

### task_illustrations__environment__feature_relation_object_count / answer_and_annotation / sample 8101331177712953

- `query_id`: `on_feature`
- `instance_seed`: `8101331177712953`
- `word_count`: `99`
- `body_word_count`: `31`

```text
The image shows a meadow river setting with illustrated foreground objects and visible environmental features. How many foreground objects are in or on the river? If none are there, answer 0.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around each counted foreground object in or on the river; use [] if none match.
Answer field: set "answer" to the count of foreground objects in or on the river as an integer, using 0 if none match.
Example JSON:
{"annotation":[[238,390,322,474],[468,460,560,556]],"answer":2}
```

### task_illustrations__construction_site__equipment_zone_count / answer_and_annotation / sample 4940091535128350

- `query_id`: `single`
- `instance_seed`: `4940091535128350`
- `word_count`: `98`
- `body_word_count`: `30`

```text
The image shows a construction site with 5 workers, labeled work zones, materials, and equipment. How many construction vehicles are in the Roadwork Zone? If none are there, answer 0.
Required annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around each counted construction vehicle in the Roadwork Zone; use [] if none match.
Required answer format: set "answer" to the count of construction vehicles in the Roadwork Zone as an integer, using 0 if none match.
Example JSON:
{"annotation":[[326,432,458,540],[474,449,614,557]],"answer":2}
```

### task_illustrations__rpg_tactical_map__movement_cost_value / answer_only / sample 5297355580750692

- `query_id`: `single`
- `instance_seed`: `5297355580750692`
- `word_count`: `98`
- `body_word_count`: `94`

```text
This illustration shows a tactical RPG grid map where a blue unit can move across terrain toward the marked target tile. The blue unit starts on its current tile. Grass, roads, and bridges cost 1 movement point; forests cost 2; mountains cost 3; water cannot be entered. Moves are only up, down, left, or right. How many movement points are needed to reach the marked destination tile using the cheapest path?
Return JSON with key "answer".
Answer field: set "answer" to the fewest number of movement points needed to reach the marked target tile.
Example JSON:
{"answer":7}
```

### task_illustrations__construction_site__worker_attribute_count / answer_and_annotation / sample 2102135614655452

- `query_id`: `hard_hat_color_worker_count`
- `instance_seed`: `2102135614655452`
- `word_count`: `97`
- `body_word_count`: `30`

```text
The image shows a construction site with 13 workers, labeled work zones, materials, and equipment. How many workers are wearing yellow [#EEC240] hard hats? If none are there, answer 0.
Format for the "annotation" field: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around each counted worker; use [] if none match.
Format for the "answer" field: set "answer" to the count of workers wearing yellow [#EEC240] hard hats as an integer, using 0 if none match.
Example JSON:
{"annotation":[[584,386,640,492],[676,460,732,566]],"answer":2}
```

### task_illustrations__isometric_harbor__boat_side_count / answer_and_annotation / sample 1938497325456926

- `query_id`: `left_side_boat_count`
- `instance_seed`: `1938497325456926`
- `word_count`: `95`
- `body_word_count`: `38`

```text
This illustration shows a harbor drawn on isometric tiles, with a main dock running from the shore into the water and boats beside it. What is the number of boats touching the image-left side of the main dock?
Final answer format: set "answer" to the number of boats docked on the image-left side of the main dock.
Annotation format: set "annotation" to a list of [x0, y0, x1, y1] pixel bounding boxes around each counted boat; use [] when the count is 0.
Example JSON:
{"annotation":[[236,420,282,470],[520,300,560,352]],"answer":2}
```

### task_illustrations__environment__lit_window_count / answer_and_annotation / sample 489258556382749

- `query_id`: `single`
- `instance_seed`: `489258556382749`
- `word_count`: `94`
- `body_word_count`: `29`

```text
The canvas contains a city canal setting with illustrated foreground objects and scene features. How many lit windows are shown on the buildings? If none are there, answer 0.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around each counted lit windows; use [] if none match.
Answer format: set "answer" to the count of lit windows on the buildings as an integer, using 0 if none match.
Example JSON:
{"annotation":[[444,162,468,186],[486,162,510,186],[444,210,468,234]],"answer":3}
```

### task_illustrations__isometric_harbor__boat_mooring_status_count / answer_and_annotation / sample 6746984510344832

- `query_id`: `open_water_boat_count`
- `instance_seed`: `6746984510344832`
- `word_count`: `94`
- `body_word_count`: `37`

```text
The scene shows a pixel-art isometric harbor where boats are moored beside a main dock that extends from land into the water. Count only the boats in open water that are not tied along the main dock.
Annotation format: set "annotation" to a list of [x0, y0, x1, y1] pixel bounding boxes around each counted boat; use [] when the count is 0.
Answer format: set "answer" to the number of boats in open water that are not tied to the dock.
Example JSON:
{"annotation":[[188,408,252,452],[514,275,580,320]],"answer":2}
```

### task_illustrations__isometric_harbor__boat_side_count / answer_and_annotation / sample 5812149659608152

- `query_id`: `right_side_boat_count`
- `instance_seed`: `5812149659608152`
- `word_count`: `93`
- `body_word_count`: `37`

```text
This illustration shows a harbor drawn on isometric tiles, with a main dock running from the shore into the water and boats beside it. Count only the boats on the image-right side of the wooden main dock.
Annotation format: set "annotation" to a list of [x0, y0, x1, y1] pixel bounding boxes around each counted boat; use [] when the count is 0.
Answer format: set "answer" to the number of boats docked on the image-right side of the main dock.
Example JSON:
{"annotation":[[236,420,282,470],[520,300,560,352]],"answer":2}
```

### task_illustrations__environment__crossing_feature_count / answer_and_annotation / sample 2436141688808723

- `query_id`: `single`
- `instance_seed`: `2436141688808723`
- `word_count`: `92`
- `body_word_count`: `33`

```text
The image shows an outdoor setting with both a road and a river with illustrated foreground objects and visible environmental features. How many bridges cross the river? If none are there, answer 0.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around each counted bridges; use [] if none match.
Answer format: set "answer" to the count of bridges crossing the river as an integer, using 0 if none match.
Example JSON:
{"annotation":[[334,420,470,472],[644,412,776,464]],"answer":2}
```

### task_illustrations__environment__feature_relation_object_count / answer_and_annotation / sample 897151723143361

- `query_id`: `below_feature`
- `instance_seed`: `897151723143361`
- `word_count`: `92`
- `body_word_count`: `28`

```text
The canvas contains a meadow river setting with illustrated foreground objects and scene features. How many foreground objects are below the river? If none are there, answer 0.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around each counted foreground object below the river; use [] if none match.
Answer field: set "answer" to the count of foreground objects below the river as an integer, using 0 if none match.
Example JSON:
{"annotation":[[238,390,322,474],[468,460,560,556]],"answer":2}
```

### task_illustrations__construction_site__worker_attribute_count / answer_and_annotation / sample 7766186932261832

- `query_id`: `vest_color_worker_count`
- `instance_seed`: `7766186932261832`
- `word_count`: `91`
- `body_word_count`: `30`

```text
The canvas contains a construction site with 11 workers, labeled work zones, materials, and equipment. How many workers are wearing red [#C6493E] safety vests? If none are there, answer 0.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around each counted worker; use [] if none match.
Answer format: set "answer" to the count of workers wearing red [#C6493E] safety vests as an integer, using 0 if none match.
Example JSON:
{"annotation":[[584,386,640,492],[676,460,732,566]],"answer":2}
```

### task_illustrations__isometric_quarry__terrain_level_object_count / answer_and_annotation / sample 3049234290294462

- `query_id`: `lowest_terrain_object_count`
- `instance_seed`: `3049234290294462`
- `word_count`: `91`
- `body_word_count`: `36`

```text
The image shows an isometric quarry made of raised terrain tiles, ore veins, mine carts, and simple quarry equipment. How many ore veins are on the lowest terrain level?
Return JSON with keys "annotation" and "answer".
Format for the "annotation" field: set "annotation" to a list of [x0, y0, x1, y1] pixel bounding boxes around each counted object; use [] when the count is 0.
Format for the "answer" field: set "answer" to the number of matching ore veins.
Example JSON:
{"annotation":[[236,420,282,470],[520,300,560,352]],"answer":2}
```

### task_illustrations__rpg_dungeon__reachable_chest_count / answer_and_annotation / sample 8356286202215882

- `query_id`: `single`
- `instance_seed`: `8356286202215882`
- `word_count`: `91`
- `body_word_count`: `35`

```text
The picture shows a pixel-art dungeon from above, including corridors, chambers, blockers, and treasure chests. From the player's position, how many chests are connected by unblocked floor paths?
Return JSON with keys "annotation" and "answer".
Annotation format: set "annotation" to a list containing one [x0, y0, x1, y1] bounding box around each counted reachable chest; use an empty list when the answer is 0.
Answer field: set "answer" to the number of treasure chests reachable from the player.
Example JSON:
{"annotation":[[236,156,284,204],[596,156,644,204]],"answer":2}
```

### task_illustrations__rpg_tactical_map__movement_sequence_endpoint_label / answer_and_annotation / sample 5676302829751498

- `query_id`: `single`
- `instance_seed`: `5676302829751498`
- `word_count`: `91`
- `body_word_count`: `43`

```text
The picture shows a pixel-art tactical movement map containing terrain tiles, a blue unit, and lettered candidate tiles. Follow this ordered move list from the blue unit: left, up, up, up. Select the final lettered tile.
Return JSON with keys "annotation" and "answer".
Format for the "annotation" field: set "annotation" to one [x0, y0, x1, y1] pixel bounding box around the selected ending tile.
Format for the "answer" field: set "answer" to the letter of the tile where the blue unit ends.
Example JSON:
{"annotation":[320,160,400,240],"answer":"C"}
```

### task_illustrations__indoor_room__furniture_side_count / answer_and_annotation / sample 1567454047398235

- `query_id`: `right_side`
- `instance_seed`: `1567454047398235`
- `word_count`: `88`
- `body_word_count`: `21`

```text
The scene shows a kitchen with small objects. What is the number of teapot objects to the right of the table?
Required annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around each counted teapot object to the right of the table.
Required answer format: set "answer" to the count of teapot objects to the right of the table as an integer.
Example JSON:
{"annotation":[[147,461,207,521],[254,504,314,564],[331,431,391,491]],"answer":3}
```

### task_illustrations__isometric_quarry__terrain_level_object_count / answer_and_annotation / sample 45657914092847

- `query_id`: `highest_terrain_object_count`
- `instance_seed`: `45657914092847`
- `word_count`: `88`
- `body_word_count`: `33`

```text
The scene shows a pixel-art isometric quarry with varied rock levels and clearly separated quarry objects. Count the mine carts placed on the highest quarry terrace.
Return JSON with keys "annotation" and "answer".
Format for the "annotation" field: set "annotation" to a list of [x0, y0, x1, y1] pixel bounding boxes around each counted object; use [] when the count is 0.
Format for the "answer" field: set "answer" to the number of matching mine carts.
Example JSON:
{"annotation":[[236,420,282,470],[520,300,560,352]],"answer":2}
```

## Repeated Scaffolding Terms

### task_illustrations__rpg_tactical_map__movement_cost_value / answer_only / sample 5297355580750692

- `query_id`: `single`
- `instance_seed`: `5297355580750692`
- `word_count`: `98`
- `body_word_count`: `94`
- `repeated_terms`: `{'answer': 3}`

```text
This illustration shows a tactical RPG grid map where a blue unit can move across terrain toward the marked target tile. The blue unit starts on its current tile. Grass, roads, and bridges cost 1 movement point; forests cost 2; mountains cost 3; water cannot be entered. Moves are only up, down, left, or right. How many movement points are needed to reach the marked destination tile using the cheapest path?
Return JSON with key "answer".
Answer field: set "answer" to the fewest number of movement points needed to reach the marked target tile.
Example JSON:
{"answer":7}
```

### task_illustrations__construction_site__rotated_tile_label / answer_and_annotation / sample 3189475449252120

- `query_id`: `single`
- `instance_seed`: `3189475449252120`
- `word_count`: `70`
- `body_word_count`: `29`
- `repeated_terms`: `{'image': 3}`

```text
The image shows a construction-site image divided into lettered tiles. One of the lettered tiles is rotated relative to the rest of the construction-site image. Which tile is it?
Required annotation format: set "annotation" to one [x0, y0, x1, y1] box around the rotated tile in image pixel coordinates.
Required answer format: set "answer" to the letter of the rotated tile.
Example JSON:
{"annotation":[350,42,670,362],"answer":"B"}
```

### task_illustrations__rpg_tactical_map__movement_sequence_endpoint_label / answer_only / sample 5676302829751498

- `query_id`: `single`
- `instance_seed`: `5676302829751498`
- `word_count`: `60`
- `body_word_count`: `56`
- `repeated_terms`: `{'answer': 3}`

```text
The picture shows a pixel-art tactical movement map containing terrain tiles, a blue unit, and lettered candidate tiles. Follow this ordered move list from the blue unit: left, up, up, up. Select the final lettered tile.
Return JSON with key "answer".
Answer field: set "answer" to the letter of the tile where the blue unit ends.
Example JSON:
{"answer":"C"}
```

### task_illustrations__rpg_house__reachable_room_count / answer_only / sample 1974223144035174

- `query_id`: `single`
- `instance_seed`: `1974223144035174`
- `word_count`: `59`
- `body_word_count`: `55`
- `repeated_terms`: `{'answer': 3}`

```text
The canvas contains a top-down RPG house map with enclosed rooms, walls, and doorways. Starting from the room with the player, how many other rooms can the player reach by passing only through open doors?
Return JSON with key "answer".
Answer field: set "answer" to the number of other rooms reachable from the player's room.
Example JSON:
{"answer":2}
```

### task_illustrations__environment__feature_relation_object_count / answer_only / sample 8101331177712953

- `query_id`: `on_feature`
- `instance_seed`: `8101331177712953`
- `word_count`: `58`
- `body_word_count`: `54`
- `repeated_terms`: `{'answer': 3}`

```text
The image shows a meadow river setting with illustrated foreground objects and visible environmental features. How many foreground objects are in or on the river? If none are there, answer 0.
Answer field: set "answer" to the count of foreground objects in or on the river as an integer, using 0 if none match.
Example JSON:
{"answer":0}
```

### task_illustrations__isometric_farmstead__terrain_level_object_count / answer_only / sample 568031449300319

- `query_id`: `highest_terrain_object_count`
- `instance_seed`: `568031449300319`
- `word_count`: `50`
- `body_word_count`: `46`
- `repeated_terms`: `{'answer': 3}`

```text
The picture shows an isometric farmstead where terrain tiles sit at different elevations with farm animals and trees placed on the ground. How many trees sit on the highest elevated terrain?
Return JSON with key "answer".
Answer field: set "answer" to the number of matching trees.
Example JSON:
{"answer":2}
```

### task_illustrations__isometric_farmstead__terrain_level_object_count / answer_only / sample 2883323222734954

- `query_id`: `lowest_terrain_object_count`
- `instance_seed`: `2883323222734954`
- `word_count`: `49`
- `body_word_count`: `45`
- `repeated_terms`: `{'answer': 3}`

```text
The image shows an isometric farmstead made of raised terrain tiles with visible side faces, farm animals, and trees. Count the farm animals placed on the lowest farm ground.
Return JSON with key "answer".
Answer field: set "answer" to the number of matching farm animals.
Example JSON:
{"answer":2}
```

### task_illustrations__rpg_house__door_state_count / answer_only / sample 3931454571182550

- `query_id`: `open_door_count`
- `instance_seed`: `3931454571182550`
- `word_count`: `48`
- `body_word_count`: `44`
- `repeated_terms`: `{'answer': 3}`

```text
The picture shows a pixel-art house interior from above, including rooms, walls, and doors. How many doors are open enough for a player to pass through?
Return JSON with key "answer".
Answer field: set "answer" to the number of doors in the requested state.
Example JSON:
{"answer":3}
```

### task_illustrations__isometric_quarry__terrain_elevation_extremum_label / answer_only / sample 8962469735831868

- `query_id`: `highest_terrain_tile`
- `instance_seed`: `8962469735831868`
- `word_count`: `45`
- `body_word_count`: `41`
- `repeated_terms`: `{'answer': 3}`

```text
This illustration shows a quarry drawn on isometric tiles, with raised rock shelves, gravel cuts, and lettered terrain tiles. Which candidate letter marks the highest terrain tile?
Return JSON with key "answer".
Answer field: set "answer" to the selected ground-tile letter.
Example JSON:
{"answer":"D"}
```

### task_illustrations__rpg_tactical_map__terrain_type_tile_count / answer_only / sample 237409349525424

- `query_id`: `single`
- `instance_seed`: `237409349525424`
- `word_count`: `45`
- `body_word_count`: `41`
- `repeated_terms`: `{'answer': 3}`

```text
This illustration shows a tactical RPG grid map where a blue unit can move across terrain. How many visible mountain tiles are in the map?
Return JSON with key "answer".
Answer field: set "answer" to the number of visible {terrain_label} tiles.
Example JSON:
{"answer":3}
```

### task_illustrations__construction_site__rotated_tile_label / answer_only / sample 3189475449252120

- `query_id`: `single`
- `instance_seed`: `3189475449252120`
- `word_count`: `44`
- `body_word_count`: `29`
- `repeated_terms`: `{'image': 3}`

```text
The image shows a construction-site image divided into lettered tiles. One of the lettered tiles is rotated relative to the rest of the construction-site image. Which tile is it?
Answer format: set "answer" to the letter of the rotated tile.
Example JSON:
{"answer":"B"}
```

### task_illustrations__rpg_house__door_state_count / answer_only / sample 3860058099758893

- `query_id`: `closed_door_count`
- `instance_seed`: `3860058099758893`
- `word_count`: `44`
- `body_word_count`: `40`
- `repeated_terms`: `{'answer': 3}`

```text
The scene shows a top-down RPG-style house layout with rooms connected by doorways. Count each closed door once. What is the total?
Return JSON with key "answer".
Answer field: set "answer" to the number of doors in the requested state.
Example JSON:
{"answer":3}
```

### task_illustrations__rpg_dungeon__missing_patch_label / answer_only / sample 3804151825947741

- `query_id`: `single`
- `instance_seed`: `3804151825947741`
- `word_count`: `43`
- `body_word_count`: `39`
- `repeated_terms`: `{'answer': 3}`

```text
This illustration shows a top-down dungeon layout with one missing patch and candidate replacements. Which option matches the removed part of the dungeon scene?
Return JSON with key "answer".
Answer field: set "answer" to the selected patch option letter.
Example JSON:
{"answer":"C"}
```

## All Prompt Samples

### task_illustrations__construction_site__equipment_zone_count / single / answer_and_annotation / sample 4940091535128350

- `instance_seed`: `4940091535128350`
- `word_count`: `98`
- `body_word_count`: `30`

```text
The image shows a construction site with 5 workers, labeled work zones, materials, and equipment. How many construction vehicles are in the Roadwork Zone? If none are there, answer 0.
Required annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around each counted construction vehicle in the Roadwork Zone; use [] if none match.
Required answer format: set "answer" to the count of construction vehicles in the Roadwork Zone as an integer, using 0 if none match.
Example JSON:
{"annotation":[[326,432,458,540],[474,449,614,557]],"answer":2}
```

### task_illustrations__construction_site__equipment_zone_count / single / answer_only / sample 4940091535128350

- `instance_seed`: `4940091535128350`
- `word_count`: `56`
- `body_word_count`: `30`

```text
The image shows a construction site with 5 workers, labeled work zones, materials, and equipment. How many construction vehicles are in the Roadwork Zone? If none are there, answer 0.
Answer format: set "answer" to the count of construction vehicles in the Roadwork Zone as an integer, using 0 if none match.
Example JSON:
{"answer":0}
```

### task_illustrations__construction_site__missing_patch_label / single / answer_and_annotation / sample 3945059923642344

- `instance_seed`: `3945059923642344`
- `word_count`: `81`
- `body_word_count`: `22`

```text
The canvas contains a construction-site source panel with one missing region and lettered patch options. Which option exactly fills the missing region?
Format for the "annotation" field: set "annotation" to a JSON object with keys "missing_region" and "selected_option", each mapped to a [x0, y0, x1, y1] box in image pixel coordinates.
Format for the "answer" field: set "answer" to the selected option letter as a string.
Example JSON:
{"annotation":{"missing_region":[214,128,374,252],"selected_option":[562,676,722,800]},"answer":"C"}
```

### task_illustrations__construction_site__missing_patch_label / single / answer_only / sample 3945059923642344

- `instance_seed`: `3945059923642344`
- `word_count`: `39`
- `body_word_count`: `22`

```text
The canvas contains a construction-site source panel with one missing region and lettered patch options. Which option exactly fills the missing region?
Required answer format: set "answer" to the selected option letter as a string.
Example JSON:
{"answer":"C"}
```

### task_illustrations__construction_site__rotated_tile_label / single / answer_and_annotation / sample 3189475449252120

- `instance_seed`: `3189475449252120`
- `word_count`: `70`
- `body_word_count`: `29`

```text
The image shows a construction-site image divided into lettered tiles. One of the lettered tiles is rotated relative to the rest of the construction-site image. Which tile is it?
Required annotation format: set "annotation" to one [x0, y0, x1, y1] box around the rotated tile in image pixel coordinates.
Required answer format: set "answer" to the letter of the rotated tile.
Example JSON:
{"annotation":[350,42,670,362],"answer":"B"}
```

### task_illustrations__construction_site__rotated_tile_label / single / answer_only / sample 3189475449252120

- `instance_seed`: `3189475449252120`
- `word_count`: `44`
- `body_word_count`: `29`

```text
The image shows a construction-site image divided into lettered tiles. One of the lettered tiles is rotated relative to the rest of the construction-site image. Which tile is it?
Answer format: set "answer" to the letter of the rotated tile.
Example JSON:
{"answer":"B"}
```

### task_illustrations__construction_site__worker_attribute_count / hard_hat_color_worker_count / answer_and_annotation / sample 2102135614655452

- `instance_seed`: `2102135614655452`
- `word_count`: `97`
- `body_word_count`: `30`

```text
The image shows a construction site with 13 workers, labeled work zones, materials, and equipment. How many workers are wearing yellow [#EEC240] hard hats? If none are there, answer 0.
Format for the "annotation" field: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around each counted worker; use [] if none match.
Format for the "answer" field: set "answer" to the count of workers wearing yellow [#EEC240] hard hats as an integer, using 0 if none match.
Example JSON:
{"annotation":[[584,386,640,492],[676,460,732,566]],"answer":2}
```

### task_illustrations__construction_site__worker_attribute_count / hard_hat_color_worker_count / answer_only / sample 2102135614655452

- `instance_seed`: `2102135614655452`
- `word_count`: `59`
- `body_word_count`: `30`

```text
The image shows a construction site with 13 workers, labeled work zones, materials, and equipment. How many workers are wearing yellow [#EEC240] hard hats? If none are there, answer 0.
Format for the "answer" field: set "answer" to the count of workers wearing yellow [#EEC240] hard hats as an integer, using 0 if none match.
Example JSON:
{"answer":0}
```

### task_illustrations__construction_site__worker_attribute_count / vest_color_worker_count / answer_and_annotation / sample 7766186932261832

- `instance_seed`: `7766186932261832`
- `word_count`: `91`
- `body_word_count`: `30`

```text
The canvas contains a construction site with 11 workers, labeled work zones, materials, and equipment. How many workers are wearing red [#C6493E] safety vests? If none are there, answer 0.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around each counted worker; use [] if none match.
Answer format: set "answer" to the count of workers wearing red [#C6493E] safety vests as an integer, using 0 if none match.
Example JSON:
{"annotation":[[584,386,640,492],[676,460,732,566]],"answer":2}
```

### task_illustrations__construction_site__worker_attribute_count / vest_color_worker_count / answer_only / sample 7766186932261832

- `instance_seed`: `7766186932261832`
- `word_count`: `57`
- `body_word_count`: `30`

```text
The canvas contains a construction site with 11 workers, labeled work zones, materials, and equipment. How many workers are wearing red [#C6493E] safety vests? If none are there, answer 0.
Final answer format: set "answer" to the count of workers wearing red [#C6493E] safety vests as an integer, using 0 if none match.
Example JSON:
{"answer":0}
```

### task_illustrations__environment__crossing_feature_count / single / answer_and_annotation / sample 2436141688808723

- `instance_seed`: `2436141688808723`
- `word_count`: `92`
- `body_word_count`: `33`

```text
The image shows an outdoor setting with both a road and a river with illustrated foreground objects and visible environmental features. How many bridges cross the river? If none are there, answer 0.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around each counted bridges; use [] if none match.
Answer format: set "answer" to the count of bridges crossing the river as an integer, using 0 if none match.
Example JSON:
{"annotation":[[334,420,470,472],[644,412,776,464]],"answer":2}
```

### task_illustrations__environment__crossing_feature_count / single / answer_only / sample 2436141688808723

- `instance_seed`: `2436141688808723`
- `word_count`: `57`
- `body_word_count`: `33`

```text
The image shows an outdoor setting with both a road and a river with illustrated foreground objects and visible environmental features. How many bridges cross the river? If none are there, answer 0.
Answer format: set "answer" to the count of bridges crossing the river as an integer, using 0 if none match.
Example JSON:
{"answer":0}
```

### task_illustrations__environment__feature_relation_object_count / above_feature / answer_and_annotation / sample 7624335182456

- `instance_seed`: `7624335182456`
- `word_count`: `102`
- `body_word_count`: `32`

```text
The scene shows a city canal setting with foreground objects placed around visible roads, rivers, buildings, or crossings. How many foreground objects are above the river? If none are there, answer 0.
Format for the "annotation" field: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around each counted foreground object above the river; use [] if none match.
Format for the "answer" field: set "answer" to the count of foreground objects above the river as an integer, using 0 if none match.
Example JSON:
{"annotation":[[238,390,322,474],[468,460,560,556]],"answer":2}
```

### task_illustrations__environment__feature_relation_object_count / above_feature / answer_only / sample 7624335182456

- `instance_seed`: `7624335182456`
- `word_count`: `58`
- `body_word_count`: `32`

```text
The scene shows a city canal setting with foreground objects placed around visible roads, rivers, buildings, or crossings. How many foreground objects are above the river? If none are there, answer 0.
Final answer format: set "answer" to the count of foreground objects above the river as an integer, using 0 if none match.
Example JSON:
{"answer":0}
```

### task_illustrations__environment__feature_relation_object_count / below_feature / answer_and_annotation / sample 897151723143361

- `instance_seed`: `897151723143361`
- `word_count`: `92`
- `body_word_count`: `28`

```text
The canvas contains a meadow river setting with illustrated foreground objects and scene features. How many foreground objects are below the river? If none are there, answer 0.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around each counted foreground object below the river; use [] if none match.
Answer field: set "answer" to the count of foreground objects below the river as an integer, using 0 if none match.
Example JSON:
{"annotation":[[238,390,322,474],[468,460,560,556]],"answer":2}
```

### task_illustrations__environment__feature_relation_object_count / below_feature / answer_only / sample 897151723143361

- `instance_seed`: `897151723143361`
- `word_count`: `54`
- `body_word_count`: `28`

```text
The canvas contains a meadow river setting with illustrated foreground objects and scene features. How many foreground objects are below the river? If none are there, answer 0.
Required answer format: set "answer" to the count of foreground objects below the river as an integer, using 0 if none match.
Example JSON:
{"answer":0}
```

### task_illustrations__environment__feature_relation_object_count / on_feature / answer_and_annotation / sample 8101331177712953

- `instance_seed`: `8101331177712953`
- `word_count`: `99`
- `body_word_count`: `31`

```text
The image shows a meadow river setting with illustrated foreground objects and visible environmental features. How many foreground objects are in or on the river? If none are there, answer 0.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around each counted foreground object in or on the river; use [] if none match.
Answer field: set "answer" to the count of foreground objects in or on the river as an integer, using 0 if none match.
Example JSON:
{"annotation":[[238,390,322,474],[468,460,560,556]],"answer":2}
```

### task_illustrations__environment__feature_relation_object_count / on_feature / answer_only / sample 8101331177712953

- `instance_seed`: `8101331177712953`
- `word_count`: `58`
- `body_word_count`: `54`

```text
The image shows a meadow river setting with illustrated foreground objects and visible environmental features. How many foreground objects are in or on the river? If none are there, answer 0.
Answer field: set "answer" to the count of foreground objects in or on the river as an integer, using 0 if none match.
Example JSON:
{"answer":0}
```

### task_illustrations__environment__lit_window_count / single / answer_and_annotation / sample 489258556382749

- `instance_seed`: `489258556382749`
- `word_count`: `94`
- `body_word_count`: `29`

```text
The canvas contains a city canal setting with illustrated foreground objects and scene features. How many lit windows are shown on the buildings? If none are there, answer 0.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around each counted lit windows; use [] if none match.
Answer format: set "answer" to the count of lit windows on the buildings as an integer, using 0 if none match.
Example JSON:
{"annotation":[[444,162,468,186],[486,162,510,186],[444,210,468,234]],"answer":3}
```

### task_illustrations__environment__lit_window_count / single / answer_only / sample 489258556382749

- `instance_seed`: `489258556382749`
- `word_count`: `55`
- `body_word_count`: `29`

```text
The canvas contains a city canal setting with illustrated foreground objects and scene features. How many lit windows are shown on the buildings? If none are there, answer 0.
Required answer format: set "answer" to the count of lit windows on the buildings as an integer, using 0 if none match.
Example JSON:
{"answer":0}
```

### task_illustrations__environment__missing_patch_label / single / answer_and_annotation / sample 5154653450374057

- `instance_seed`: `5154653450374057`
- `word_count`: `81`
- `body_word_count`: `27`

```text
The canvas contains an outdoor setting with both a road and a river with illustrated foreground objects and scene features. Which option exactly fills the missing region?
Final answer format: set "answer" to the selected option letter as a string.
Annotation format: set "annotation" to a JSON object with keys "missing_region" and "selected_option", each mapped to a [x0, y0, x1, y1] box in image pixel coordinates.
Example JSON:
{"annotation":{"missing_region":[214,128,374,252],"selected_option":[562,676,722,800]},"answer":"C"}
```

### task_illustrations__environment__missing_patch_label / single / answer_only / sample 5154653450374057

- `instance_seed`: `5154653450374057`
- `word_count`: `43`
- `body_word_count`: `27`

```text
The canvas contains an outdoor setting with both a road and a river with illustrated foreground objects and scene features. Which option exactly fills the missing region?
Answer format: set "answer" to the selected option letter as a string.
Example JSON:
{"answer":"C"}
```

### task_illustrations__environment__rotated_tile_label / single / answer_and_annotation / sample 2743857934555488

- `instance_seed`: `2743857934555488`
- `word_count`: `82`
- `body_word_count`: `43`

```text
The scene shows an outdoor setting with both a road and a river with foreground objects placed around visible roads, rivers, buildings, or crossings. One of the lettered tiles is rotated relative to the rest of the environment image. Which tile is it?
Annotation format: set "annotation" to one [x0, y0, x1, y1] box around the rotated tile in image pixel coordinates.
Answer field: set "answer" to the letter of the rotated tile.
Example JSON:
{"annotation":[350,42,670,362],"answer":"B"}
```

### task_illustrations__environment__rotated_tile_label / single / answer_only / sample 2743857934555488

- `instance_seed`: `2743857934555488`
- `word_count`: `59`
- `body_word_count`: `43`

```text
The scene shows an outdoor setting with both a road and a river with foreground objects placed around visible roads, rivers, buildings, or crossings. One of the lettered tiles is rotated relative to the rest of the environment image. Which tile is it?
Required answer format: set "answer" to the letter of the rotated tile.
Example JSON:
{"answer":"B"}
```

### task_illustrations__indoor_room__furniture_side_count / left_side / answer_and_annotation / sample 8503956876329645

- `instance_seed`: `8503956876329645`
- `word_count`: `83`
- `body_word_count`: `18`

```text
This indoor illustration shows a bedroom. How many drawn candle objects lie to the left of the table?
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around each counted candle object to the left of the table.
Answer field: set "answer" to the count of candle objects to the left of the table as an integer.
Example JSON:
{"annotation":[[147,461,207,521],[254,504,314,564],[331,431,391,491]],"answer":3}
```

### task_illustrations__indoor_room__furniture_side_count / left_side / answer_only / sample 8503956876329645

- `instance_seed`: `8503956876329645`
- `word_count`: `42`
- `body_word_count`: `18`

```text
This indoor illustration shows a bedroom. How many drawn candle objects lie to the left of the table?
Required answer format: set "answer" to the count of candle objects to the left of the table as an integer.
Example JSON:
{"answer":3}
```

### task_illustrations__indoor_room__furniture_side_count / right_side / answer_and_annotation / sample 1567454047398235

- `instance_seed`: `1567454047398235`
- `word_count`: `88`
- `body_word_count`: `21`

```text
The scene shows a kitchen with small objects. What is the number of teapot objects to the right of the table?
Required annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around each counted teapot object to the right of the table.
Required answer format: set "answer" to the count of teapot objects to the right of the table as an integer.
Example JSON:
{"annotation":[[147,461,207,521],[254,504,314,564],[331,431,391,491]],"answer":3}
```

### task_illustrations__indoor_room__furniture_side_count / right_side / answer_only / sample 1567454047398235

- `instance_seed`: `1567454047398235`
- `word_count`: `45`
- `body_word_count`: `21`

```text
The scene shows a kitchen with small objects. What is the number of teapot objects to the right of the table?
Required answer format: set "answer" to the count of teapot objects to the right of the table as an integer.
Example JSON:
{"answer":3}
```

### task_illustrations__indoor_room__missing_patch_label / single / answer_and_annotation / sample 8837408893689039

- `instance_seed`: `8837408893689039`
- `word_count`: `71`
- `body_word_count`: `17`

```text
The image shows a study. Select the option that restores the missing part of the room image.
Final answer format: set "answer" to the selected option letter as a string.
Annotation format: set "annotation" to a JSON object with keys "missing_region" and "selected_option", each mapped to a [x0, y0, x1, y1] box in image pixel coordinates.
Example JSON:
{"annotation":{"missing_region":[214,128,374,252],"selected_option":[562,676,722,800]},"answer":"C"}
```

### task_illustrations__indoor_room__missing_patch_label / single / answer_only / sample 8837408893689039

- `instance_seed`: `8837408893689039`
- `word_count`: `33`
- `body_word_count`: `17`

```text
The image shows a study. Select the option that restores the missing part of the room image.
Answer format: set "answer" to the selected option letter as a string.
Example JSON:
{"answer":"C"}
```

### task_illustrations__indoor_room__rotated_tile_label / single / answer_and_annotation / sample 1094030308465037

- `instance_seed`: `1094030308465037`
- `word_count`: `63`
- `body_word_count`: `23`

```text
The picture shows a bedroom with small objects. The indoor room is split into lettered tiles. Identify the tile that has been rotated.
Final answer format: set "answer" to the letter of the rotated tile.
Annotation format: set "annotation" to one [x0, y0, x1, y1] box around the rotated tile in image pixel coordinates.
Example JSON:
{"annotation":[350,42,670,362],"answer":"B"}
```

### task_illustrations__indoor_room__rotated_tile_label / single / answer_only / sample 1094030308465037

- `instance_seed`: `1094030308465037`
- `word_count`: `39`
- `body_word_count`: `23`

```text
The picture shows a bedroom with small objects. The indoor room is split into lettered tiles. Identify the tile that has been rotated.
Required answer format: set "answer" to the letter of the rotated tile.
Example JSON:
{"answer":"B"}
```

### task_illustrations__indoor_room__surface_object_count / single / answer_and_annotation / sample 1151963382969190

- `instance_seed`: `1151963382969190`
- `word_count`: `68`
- `body_word_count`: `12`

```text
The image shows a kitchen. Count the ruler objects on the table.
Final answer format: set "answer" to the count of ruler objects on the table as an integer.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around each counted ruler object on the table.
Example JSON:
{"annotation":[[462,347,522,407],[596,344,660,404]],"answer":2}
```

### task_illustrations__indoor_room__surface_object_count / single / answer_only / sample 1151963382969190

- `instance_seed`: `1151963382969190`
- `word_count`: `32`
- `body_word_count`: `12`

```text
The image shows a kitchen. Count the ruler objects on the table.
Answer format: set "answer" to the count of ruler objects on the table as an integer.
Example JSON:
{"answer":2}
```

### task_illustrations__indoor_room__swapped_tile_pair_label / single / answer_and_annotation / sample 1757597108555829

- `instance_seed`: `1757597108555829`
- `word_count`: `63`
- `body_word_count`: `20`

```text
The scene shows a living room with small objects. Which lettered option identifies the two numbered cells that changed places?
Annotation format: set "annotation" to a JSON array containing two [x0, y0, x1, y1] boxes around the two swapped numbered cells.
Answer format: set "answer" to the selected option letter.
Example JSON:
{"annotation":[[0,0,400,266],[800,532,1200,798]],"answer":"C"}
```

### task_illustrations__indoor_room__swapped_tile_pair_label / single / answer_only / sample 1757597108555829

- `instance_seed`: `1757597108555829`
- `word_count`: `33`
- `body_word_count`: `20`

```text
The scene shows a living room with small objects. Which lettered option identifies the two numbered cells that changed places?
Answer format: set "answer" to the selected option letter.
Example JSON:
{"answer":"C"}
```

### task_illustrations__isometric_farmstead__farmer_same_level_tile_label / single / answer_and_annotation / sample 3498160771595964

- `instance_seed`: `3498160771595964`
- `word_count`: `76`
- `body_word_count`: `40`

```text
The scene shows a pixel-art isometric farm with varied terrain levels, an unlettered farmer reference, and lettered candidate ground tiles. Which candidate terrain tile is on the same raised level as the farmer?
Return JSON with keys "annotation" and "answer".
Annotation format: set "annotation" to one [x0, y0, x1, y1] pixel bounding box around the selected terrain tile.
Answer format: set "answer" to the selected ground-tile letter.
Example JSON:
{"annotation":[420,260,486,294],"answer":"B"}
```

### task_illustrations__isometric_farmstead__farmer_same_level_tile_label / single / answer_only / sample 3498160771595964

- `instance_seed`: `3498160771595964`
- `word_count`: `54`
- `body_word_count`: `38`

```text
The scene shows a pixel-art isometric farm with varied terrain levels, an unlettered farmer reference, and lettered candidate ground tiles. Which candidate terrain tile is on the same raised level as the farmer?
Return JSON with key "answer".
Format for the "answer" field: set "answer" to the selected ground-tile letter.
Example JSON:
{"answer":"B"}
```

### task_illustrations__isometric_farmstead__highest_terrain_tile_count / single / answer_and_annotation / sample 8526691899252549

- `instance_seed`: `8526691899252549`
- `word_count`: `80`
- `body_word_count`: `34`

```text
The picture shows an isometric farmstead where terrain tiles form raised layers with visible tile borders. How many visible terrain tiles are on the highest elevation layer?
Return JSON with keys "annotation" and "answer".
Final answer format: set "answer" to the number of visible top-surface terrain tiles on the highest elevation layer.
Annotation format: set "annotation" to one [x0, y0, x1, y1] pixel bounding box around the whole highest-elevation top layer.
Example JSON:
{"annotation":[380,180,640,330],"answer":12}
```

### task_illustrations__isometric_farmstead__highest_terrain_tile_count / single / answer_only / sample 8526691899252549

- `instance_seed`: `8526691899252549`
- `word_count`: `54`
- `body_word_count`: `32`

```text
The picture shows an isometric farmstead where terrain tiles form raised layers with visible tile borders. How many visible terrain tiles are on the highest elevation layer?
Return JSON with key "answer".
Required answer format: set "answer" to the number of visible top-surface terrain tiles on the highest elevation layer.
Example JSON:
{"answer":12}
```

### task_illustrations__isometric_farmstead__terrain_elevation_extremum_label / highest_terrain_tile / answer_and_annotation / sample 8170733315224915

- `instance_seed`: `8170733315224915`
- `word_count`: `76`
- `body_word_count`: `39`

```text
This illustration shows a farmstead drawn on isometric tiles, with raised ground levels, connected farm areas, and lettered terrain tiles. Among the lettered ground tiles, which one is at the highest elevation?
Return JSON with keys "annotation" and "answer".
Final answer format: set "answer" to the selected ground-tile letter.
Annotation format: set "annotation" to one [x0, y0, x1, y1] pixel bounding box around the selected terrain tile.
Example JSON:
{"annotation":[420,260,486,294],"answer":"D"}
```

### task_illustrations__isometric_farmstead__terrain_elevation_extremum_label / highest_terrain_tile / answer_only / sample 8170733315224915

- `instance_seed`: `8170733315224915`
- `word_count`: `51`
- `body_word_count`: `37`

```text
This illustration shows a farmstead drawn on isometric tiles, with raised ground levels, connected farm areas, and lettered terrain tiles. Among the lettered ground tiles, which one is at the highest elevation?
Return JSON with key "answer".
Required answer format: set "answer" to the selected ground-tile letter.
Example JSON:
{"answer":"D"}
```

### task_illustrations__isometric_farmstead__terrain_elevation_extremum_label / lowest_terrain_tile / answer_and_annotation / sample 6728224672519310

- `instance_seed`: `6728224672519310`
- `word_count`: `81`
- `body_word_count`: `43`

```text
The scene shows a pixel-art isometric farm with varied terrain levels, connected farm patches, farm animals or trees, and lettered ground tiles. Choose the letter of the terrain tile that sits lowest in the farm scene.
Return JSON with keys "annotation" and "answer".
Required annotation format: set "annotation" to one [x0, y0, x1, y1] pixel bounding box around the selected terrain tile.
Required answer format: set "answer" to the selected ground-tile letter.
Example JSON:
{"annotation":[420,260,486,294],"answer":"D"}
```

### task_illustrations__isometric_farmstead__terrain_elevation_extremum_label / lowest_terrain_tile / answer_only / sample 6728224672519310

- `instance_seed`: `6728224672519310`
- `word_count`: `54`
- `body_word_count`: `41`

```text
The scene shows a pixel-art isometric farm with varied terrain levels, connected farm patches, farm animals or trees, and lettered ground tiles. Choose the letter of the terrain tile that sits lowest in the farm scene.
Return JSON with key "answer".
Answer format: set "answer" to the selected ground-tile letter.
Example JSON:
{"answer":"D"}
```

### task_illustrations__isometric_farmstead__terrain_level_object_count / highest_terrain_object_count / answer_and_annotation / sample 568031449300319

- `instance_seed`: `568031449300319`
- `word_count`: `86`
- `body_word_count`: `38`

```text
The picture shows an isometric farmstead where terrain tiles sit at different elevations with farm animals and trees placed on the ground. How many trees sit on the highest elevated terrain?
Return JSON with keys "annotation" and "answer".
Annotation format: set "annotation" to a list of [x0, y0, x1, y1] pixel bounding boxes around each counted object; use [] when the count is 0.
Answer field: set "answer" to the number of matching trees.
Example JSON:
{"annotation":[[236,420,282,470],[520,300,560,352]],"answer":2}
```

### task_illustrations__isometric_farmstead__terrain_level_object_count / highest_terrain_object_count / answer_only / sample 568031449300319

- `instance_seed`: `568031449300319`
- `word_count`: `50`
- `body_word_count`: `46`

```text
The picture shows an isometric farmstead where terrain tiles sit at different elevations with farm animals and trees placed on the ground. How many trees sit on the highest elevated terrain?
Return JSON with key "answer".
Answer field: set "answer" to the number of matching trees.
Example JSON:
{"answer":2}
```

### task_illustrations__isometric_farmstead__terrain_level_object_count / lowest_terrain_object_count / answer_and_annotation / sample 2883323222734954

- `instance_seed`: `2883323222734954`
- `word_count`: `85`
- `body_word_count`: `36`

```text
The image shows an isometric farmstead made of raised terrain tiles with visible side faces, farm animals, and trees. Count the farm animals placed on the lowest farm ground.
Return JSON with keys "annotation" and "answer".
Annotation format: set "annotation" to a list of [x0, y0, x1, y1] pixel bounding boxes around each counted object; use [] when the count is 0.
Answer format: set "answer" to the number of matching farm animals.
Example JSON:
{"annotation":[[236,420,282,470],[520,300,560,352]],"answer":2}
```

### task_illustrations__isometric_farmstead__terrain_level_object_count / lowest_terrain_object_count / answer_only / sample 2883323222734954

- `instance_seed`: `2883323222734954`
- `word_count`: `49`
- `body_word_count`: `45`

```text
The image shows an isometric farmstead made of raised terrain tiles with visible side faces, farm animals, and trees. Count the farm animals placed on the lowest farm ground.
Return JSON with key "answer".
Answer field: set "answer" to the number of matching farm animals.
Example JSON:
{"answer":2}
```

### task_illustrations__isometric_harbor__boat_heading_status_count / away_from_shoreline_boat_count / answer_and_annotation / sample 2846196643336637

- `instance_seed`: `2846196643336637`
- `word_count`: `78`
- `body_word_count`: `30`

```text
This illustration shows a tiled isometric harbor with a visible shore edge, a dock, and boats floating on the water. Count the boats whose bows point away from the shore.
Required annotation format: set "annotation" to a list of [x0, y0, x1, y1] pixel bounding boxes around each counted boat.
Required answer format: set "answer" to the number of boats facing away from the shoreline.
Example JSON:
{"annotation":[[188,408,252,452],[514,275,580,320]],"answer":2}
```

### task_illustrations__isometric_harbor__boat_heading_status_count / away_from_shoreline_boat_count / answer_only / sample 2846196643336637

- `instance_seed`: `2846196643336637`
- `word_count`: `51`
- `body_word_count`: `30`

```text
This illustration shows a tiled isometric harbor with a visible shore edge, a dock, and boats floating on the water. Count the boats whose bows point away from the shore.
Format for the "answer" field: set "answer" to the number of boats facing away from the shoreline.
Example JSON:
{"answer":2}
```

### task_illustrations__isometric_harbor__boat_heading_status_count / toward_shoreline_boat_count / answer_and_annotation / sample 5318216600359120

- `instance_seed`: `5318216600359120`
- `word_count`: `75`
- `body_word_count`: `30`

```text
The scene shows a pixel-art isometric harbor with land at the shore, a wooden dock, and boats floating in the water. Count the boats whose bows point toward the shore.
Annotation format: set "annotation" to a list of [x0, y0, x1, y1] pixel bounding boxes around each counted boat.
Answer format: set "answer" to the number of boats facing toward the shoreline.
Example JSON:
{"annotation":[[188,408,252,452],[514,275,580,320]],"answer":2}
```

### task_illustrations__isometric_harbor__boat_heading_status_count / toward_shoreline_boat_count / answer_only / sample 5318216600359120

- `instance_seed`: `5318216600359120`
- `word_count`: `47`
- `body_word_count`: `30`

```text
The scene shows a pixel-art isometric harbor with land at the shore, a wooden dock, and boats floating in the water. Count the boats whose bows point toward the shore.
Answer format: set "answer" to the number of boats facing toward the shoreline.
Example JSON:
{"answer":2}
```

### task_illustrations__isometric_harbor__boat_mooring_status_count / moored_boat_count / answer_and_annotation / sample 2557503802660890

- `instance_seed`: `2557503802660890`
- `word_count`: `85`
- `body_word_count`: `33`

```text
The image shows an isometric harbor with a shoreline, blue water tiles, a connected wooden main dock, dock posts, cargo objects, and small boats. How many boats are tied along the main dock?
Annotation format: set "annotation" to a list of [x0, y0, x1, y1] pixel bounding boxes around each counted boat; use [] when the count is 0.
Answer format: set "answer" to the number of boats tied along the main dock.
Example JSON:
{"annotation":[[188,408,252,452],[514,275,580,320]],"answer":2}
```

### task_illustrations__isometric_harbor__boat_mooring_status_count / moored_boat_count / answer_only / sample 2557503802660890

- `instance_seed`: `2557503802660890`
- `word_count`: `54`
- `body_word_count`: `33`

```text
The image shows an isometric harbor with a shoreline, blue water tiles, a connected wooden main dock, dock posts, cargo objects, and small boats. How many boats are tied along the main dock?
Format for the "answer" field: set "answer" to the number of boats tied along the main dock.
Example JSON:
{"answer":2}
```

### task_illustrations__isometric_harbor__boat_mooring_status_count / open_water_boat_count / answer_and_annotation / sample 6746984510344832

- `instance_seed`: `6746984510344832`
- `word_count`: `94`
- `body_word_count`: `37`

```text
The scene shows a pixel-art isometric harbor where boats are moored beside a main dock that extends from land into the water. Count only the boats in open water that are not tied along the main dock.
Annotation format: set "annotation" to a list of [x0, y0, x1, y1] pixel bounding boxes around each counted boat; use [] when the count is 0.
Answer format: set "answer" to the number of boats in open water that are not tied to the dock.
Example JSON:
{"annotation":[[188,408,252,452],[514,275,580,320]],"answer":2}
```

### task_illustrations__isometric_harbor__boat_mooring_status_count / open_water_boat_count / answer_only / sample 6746984510344832

- `instance_seed`: `6746984510344832`
- `word_count`: `63`
- `body_word_count`: `37`

```text
The scene shows a pixel-art isometric harbor where boats are moored beside a main dock that extends from land into the water. Count only the boats in open water that are not tied along the main dock.
Format for the "answer" field: set "answer" to the number of boats in open water that are not tied to the dock.
Example JSON:
{"answer":2}
```

### task_illustrations__isometric_harbor__boat_side_count / left_side_boat_count / answer_and_annotation / sample 1938497325456926

- `instance_seed`: `1938497325456926`
- `word_count`: `95`
- `body_word_count`: `38`

```text
This illustration shows a harbor drawn on isometric tiles, with a main dock running from the shore into the water and boats beside it. What is the number of boats touching the image-left side of the main dock?
Final answer format: set "answer" to the number of boats docked on the image-left side of the main dock.
Annotation format: set "annotation" to a list of [x0, y0, x1, y1] pixel bounding boxes around each counted boat; use [] when the count is 0.
Example JSON:
{"annotation":[[236,420,282,470],[520,300,560,352]],"answer":2}
```

### task_illustrations__isometric_harbor__boat_side_count / left_side_boat_count / answer_only / sample 1938497325456926

- `instance_seed`: `1938497325456926`
- `word_count`: `61`
- `body_word_count`: `38`

```text
This illustration shows a harbor drawn on isometric tiles, with a main dock running from the shore into the water and boats beside it. What is the number of boats touching the image-left side of the main dock?
Final answer format: set "answer" to the number of boats docked on the image-left side of the main dock.
Example JSON:
{"answer":2}
```

### task_illustrations__isometric_harbor__boat_side_count / right_side_boat_count / answer_and_annotation / sample 5812149659608152

- `instance_seed`: `5812149659608152`
- `word_count`: `93`
- `body_word_count`: `37`

```text
This illustration shows a harbor drawn on isometric tiles, with a main dock running from the shore into the water and boats beside it. Count only the boats on the image-right side of the wooden main dock.
Annotation format: set "annotation" to a list of [x0, y0, x1, y1] pixel bounding boxes around each counted boat; use [] when the count is 0.
Answer format: set "answer" to the number of boats docked on the image-right side of the main dock.
Example JSON:
{"annotation":[[236,420,282,470],[520,300,560,352]],"answer":2}
```

### task_illustrations__isometric_harbor__boat_side_count / right_side_boat_count / answer_only / sample 5812149659608152

- `instance_seed`: `5812149659608152`
- `word_count`: `59`
- `body_word_count`: `55`

```text
This illustration shows a harbor drawn on isometric tiles, with a main dock running from the shore into the water and boats beside it. Count only the boats on the image-right side of the wooden main dock.
Answer field: set "answer" to the number of boats docked on the image-right side of the main dock.
Example JSON:
{"answer":2}
```

### task_illustrations__isometric_harbor__shoreline_nearest_boat_label / single / answer_and_annotation / sample 5290260914883436

- `instance_seed`: `5290260914883436`
- `word_count`: `63`
- `body_word_count`: `29`

```text
The scene shows a pixel-art isometric harbor with land at the shore, a wooden dock, and boats floating in the water. Which lettered boat is closest to the shoreline?
Annotation format: set "annotation" to [x0, y0, x1, y1] pixel bounding box around the selected boat.
Answer format: set "answer" to the selected boat letter.
Example JSON:
{"annotation":[188,408,252,452],"answer":"C"}
```

### task_illustrations__isometric_harbor__shoreline_nearest_boat_label / single / answer_only / sample 5290260914883436

- `instance_seed`: `5290260914883436`
- `word_count`: `45`
- `body_word_count`: `29`

```text
The scene shows a pixel-art isometric harbor with land at the shore, a wooden dock, and boats floating in the water. Which lettered boat is closest to the shoreline?
Format for the "answer" field: set "answer" to the selected boat letter.
Example JSON:
{"answer":"C"}
```

### task_illustrations__isometric_quarry__highest_terrain_tile_count / single / answer_and_annotation / sample 5812974075308396

- `instance_seed`: `5812974075308396`
- `word_count`: `87`
- `body_word_count`: `36`

```text
The canvas contains an isometric quarry scene with multiple rock heights and a clearly visible highest layer. Count the top-surface terrain tiles that make up the highest quarry terrace.
Return JSON with keys "annotation" and "answer".
Format for the "annotation" field: set "annotation" to one [x0, y0, x1, y1] pixel bounding box around the whole highest-elevation top layer.
Format for the "answer" field: set "answer" to the number of visible top-surface terrain tiles on the highest elevation layer.
Example JSON:
{"annotation":[380,180,640,330],"answer":12}
```

### task_illustrations__isometric_quarry__highest_terrain_tile_count / single / answer_only / sample 5812974075308396

- `instance_seed`: `5812974075308396`
- `word_count`: `55`
- `body_word_count`: `34`

```text
The canvas contains an isometric quarry scene with multiple rock heights and a clearly visible highest layer. Count the top-surface terrain tiles that make up the highest quarry terrace.
Return JSON with key "answer".
Answer format: set "answer" to the number of visible top-surface terrain tiles on the highest elevation layer.
Example JSON:
{"answer":12}
```

### task_illustrations__isometric_quarry__terrain_elevation_extremum_label / highest_terrain_tile / answer_and_annotation / sample 8962469735831868

- `instance_seed`: `8962469735831868`
- `word_count`: `70`
- `body_word_count`: `34`

```text
This illustration shows a quarry drawn on isometric tiles, with raised rock shelves, gravel cuts, and lettered terrain tiles. Which candidate letter marks the highest terrain tile?
Return JSON with keys "annotation" and "answer".
Annotation format: set "annotation" to one [x0, y0, x1, y1] pixel bounding box around the selected terrain tile.
Answer format: set "answer" to the selected ground-tile letter.
Example JSON:
{"annotation":[420,260,486,294],"answer":"D"}
```

### task_illustrations__isometric_quarry__terrain_elevation_extremum_label / highest_terrain_tile / answer_only / sample 8962469735831868

- `instance_seed`: `8962469735831868`
- `word_count`: `45`
- `body_word_count`: `41`

```text
This illustration shows a quarry drawn on isometric tiles, with raised rock shelves, gravel cuts, and lettered terrain tiles. Which candidate letter marks the highest terrain tile?
Return JSON with key "answer".
Answer field: set "answer" to the selected ground-tile letter.
Example JSON:
{"answer":"D"}
```

### task_illustrations__isometric_quarry__terrain_elevation_extremum_label / lowest_terrain_tile / answer_and_annotation / sample 3190502157014012

- `instance_seed`: `3190502157014012`
- `word_count`: `74`
- `body_word_count`: `38`

```text
The canvas contains an isometric quarry scene with multiple rock heights, industrial context objects, and lettered candidate ground tiles. Among the lettered ground tiles, which one is at the lowest elevation?
Return JSON with keys "annotation" and "answer".
Annotation format: set "annotation" to one [x0, y0, x1, y1] pixel bounding box around the selected terrain tile.
Answer format: set "answer" to the selected ground-tile letter.
Example JSON:
{"annotation":[420,260,486,294],"answer":"D"}
```

### task_illustrations__isometric_quarry__terrain_elevation_extremum_label / lowest_terrain_tile / answer_only / sample 3190502157014012

- `instance_seed`: `3190502157014012`
- `word_count`: `50`
- `body_word_count`: `36`

```text
The canvas contains an isometric quarry scene with multiple rock heights, industrial context objects, and lettered candidate ground tiles. Among the lettered ground tiles, which one is at the lowest elevation?
Return JSON with key "answer".
Final answer format: set "answer" to the selected ground-tile letter.
Example JSON:
{"answer":"D"}
```

### task_illustrations__isometric_quarry__terrain_level_object_count / highest_terrain_object_count / answer_and_annotation / sample 45657914092847

- `instance_seed`: `45657914092847`
- `word_count`: `88`
- `body_word_count`: `33`

```text
The scene shows a pixel-art isometric quarry with varied rock levels and clearly separated quarry objects. Count the mine carts placed on the highest quarry terrace.
Return JSON with keys "annotation" and "answer".
Format for the "annotation" field: set "annotation" to a list of [x0, y0, x1, y1] pixel bounding boxes around each counted object; use [] when the count is 0.
Format for the "answer" field: set "answer" to the number of matching mine carts.
Example JSON:
{"annotation":[[236,420,282,470],[520,300,560,352]],"answer":2}
```

### task_illustrations__isometric_quarry__terrain_level_object_count / highest_terrain_object_count / answer_only / sample 45657914092847

- `instance_seed`: `45657914092847`
- `word_count`: `47`
- `body_word_count`: `31`

```text
The scene shows a pixel-art isometric quarry with varied rock levels and clearly separated quarry objects. Count the mine carts placed on the highest quarry terrace.
Return JSON with key "answer".
Required answer format: set "answer" to the number of matching mine carts.
Example JSON:
{"answer":2}
```

### task_illustrations__isometric_quarry__terrain_level_object_count / lowest_terrain_object_count / answer_and_annotation / sample 3049234290294462

- `instance_seed`: `3049234290294462`
- `word_count`: `91`
- `body_word_count`: `36`

```text
The image shows an isometric quarry made of raised terrain tiles, ore veins, mine carts, and simple quarry equipment. How many ore veins are on the lowest terrain level?
Return JSON with keys "annotation" and "answer".
Format for the "annotation" field: set "annotation" to a list of [x0, y0, x1, y1] pixel bounding boxes around each counted object; use [] when the count is 0.
Format for the "answer" field: set "answer" to the number of matching ore veins.
Example JSON:
{"annotation":[[236,420,282,470],[520,300,560,352]],"answer":2}
```

### task_illustrations__isometric_quarry__terrain_level_object_count / lowest_terrain_object_count / answer_only / sample 3049234290294462

- `instance_seed`: `3049234290294462`
- `word_count`: `50`
- `body_word_count`: `34`

```text
The image shows an isometric quarry made of raised terrain tiles, ore veins, mine carts, and simple quarry equipment. How many ore veins are on the lowest terrain level?
Return JSON with key "answer".
Final answer format: set "answer" to the number of matching ore veins.
Example JSON:
{"answer":2}
```

### task_illustrations__isometric_quarry__worker_same_level_tile_label / single / answer_and_annotation / sample 5610501457885160

- `instance_seed`: `5610501457885160`
- `word_count`: `74`
- `body_word_count`: `37`

```text
The scene shows a pixel-art isometric quarry with varied rock levels, a worker, and lettered candidate ground tiles. Among the lettered ground tiles, which one matches the worker's terrain elevation?
Return JSON with keys "annotation" and "answer".
Final answer format: set "answer" to the selected ground-tile letter.
Annotation format: set "annotation" to one [x0, y0, x1, y1] pixel bounding box around the selected terrain tile.
Example JSON:
{"annotation":[420,260,486,294],"answer":"B"}
```

### task_illustrations__isometric_quarry__worker_same_level_tile_label / single / answer_only / sample 5610501457885160

- `instance_seed`: `5610501457885160`
- `word_count`: `48`
- `body_word_count`: `35`

```text
The scene shows a pixel-art isometric quarry with varied rock levels, a worker, and lettered candidate ground tiles. Among the lettered ground tiles, which one matches the worker's terrain elevation?
Return JSON with key "answer".
Answer format: set "answer" to the selected ground-tile letter.
Example JSON:
{"answer":"B"}
```

### task_illustrations__library__books_in_section_count / single / answer_and_annotation / sample 7122912296169102

- `instance_seed`: `7122912296169102`
- `word_count`: `73`
- `body_word_count`: `19`

```text
The image shows an illustrated library with 4 labeled shelf sections. How many books are in the Art section?
Annotation format: set "annotation" to a JSON array of [x, y] center points in image pixel coordinates for every counted book in the Art section.
Answer field: set "answer" to the count of books in the Art section as an integer.
Example JSON:
{"annotation":[[101,222],[124,225],[148,217],[188,212]],"answer":4}
```

### task_illustrations__library__books_in_section_count / single / answer_only / sample 7122912296169102

- `instance_seed`: `7122912296169102`
- `word_count`: `39`
- `body_word_count`: `35`

```text
The image shows an illustrated library with 4 labeled shelf sections. How many books are in the Art section?
Answer field: set "answer" to the count of books in the Art section as an integer.
Example JSON:
{"answer":4}
```

### task_illustrations__library__filtered_book_in_section_count / book_color_in_section_count / answer_and_annotation / sample 1971350506334509

- `instance_seed`: `1971350506334509`
- `word_count`: `79`
- `body_word_count`: `17`

```text
The picture shows 5 labeled library shelf sections. Count the magenta [#D02C91] books in the Math section.
Format for the "annotation" field: set "annotation" to a JSON array of [x, y] center points in image pixel coordinates for every counted magenta [#D02C91] book in the Math section.
Format for the "answer" field: set "answer" to the count of magenta [#D02C91] books in the Math section as an integer.
Example JSON:
{"annotation":[[253,220],[297,222],[361,216]],"answer":3}
```

### task_illustrations__library__filtered_book_in_section_count / book_color_in_section_count / answer_only / sample 1971350506334509

- `instance_seed`: `1971350506334509`
- `word_count`: `40`
- `body_word_count`: `17`

```text
The picture shows 5 labeled library shelf sections. Count the magenta [#D02C91] books in the Math section.
Required answer format: set "answer" to the count of magenta [#D02C91] books in the Math section as an integer.
Example JSON:
{"answer":3}
```

### task_illustrations__library__filtered_book_in_section_count / horizontal_book_in_section_count / answer_and_annotation / sample 6495505457773683

- `instance_seed`: `6495505457773683`
- `word_count`: `76`
- `body_word_count`: `20`

```text
The scene shows a library room containing 5 labeled book sections. How many horizontal books are in the History section?
Required annotation format: set "annotation" to a JSON array of [x, y] center points in image pixel coordinates for every counted horizontal book in the History section.
Required answer format: set "answer" to the count of horizontal books in the History section as an integer.
Example JSON:
{"annotation":[[491,224],[535,218],[637,214]],"answer":3}
```

### task_illustrations__library__filtered_book_in_section_count / horizontal_book_in_section_count / answer_only / sample 6495505457773683

- `instance_seed`: `6495505457773683`
- `word_count`: `41`
- `body_word_count`: `37`

```text
The scene shows a library room containing 5 labeled book sections. How many horizontal books are in the History section?
Answer field: set "answer" to the count of horizontal books in the History section as an integer.
Example JSON:
{"answer":3}
```

### task_illustrations__library__filtered_book_in_section_count / upright_book_in_section_count / answer_and_annotation / sample 8415597127285372

- `instance_seed`: `8415597127285372`
- `word_count`: `77`
- `body_word_count`: `22`

```text
The scene shows a library room containing 4 labeled book sections. What is the number of upright books in the History section?
Final answer format: set "answer" to the count of upright books in the History section as an integer.
Annotation format: set "annotation" to a JSON array of [x, y] center points in image pixel coordinates for every counted upright book in the History section.
Example JSON:
{"annotation":[[491,224],[535,218],[637,214]],"answer":3}
```

### task_illustrations__library__filtered_book_in_section_count / upright_book_in_section_count / answer_only / sample 8415597127285372

- `instance_seed`: `8415597127285372`
- `word_count`: `43`
- `body_word_count`: `39`

```text
The scene shows a library room containing 4 labeled book sections. What is the number of upright books in the History section?
Answer field: set "answer" to the count of upright books in the History section as an integer.
Example JSON:
{"answer":3}
```

### task_illustrations__library__missing_patch_label / single / answer_and_annotation / sample 4049792788931245

- `instance_seed`: `4049792788931245`
- `word_count`: `74`
- `body_word_count`: `20`

```text
The image shows an illustrated library with 4 labeled shelf sections. Choose the patch option that completes the library illustration.
Final answer format: set "answer" to the selected option letter as a string.
Annotation format: set "annotation" to a JSON object with keys "missing_region" and "selected_option", each mapped to a [x0, y0, x1, y1] box in image pixel coordinates.
Example JSON:
{"annotation":{"missing_region":[214,128,374,252],"selected_option":[562,676,722,800]},"answer":"C"}
```

### task_illustrations__library__missing_patch_label / single / answer_only / sample 4049792788931245

- `instance_seed`: `4049792788931245`
- `word_count`: `37`
- `body_word_count`: `20`

```text
The image shows an illustrated library with 4 labeled shelf sections. Choose the patch option that completes the library illustration.
Required answer format: set "answer" to the selected option letter as a string.
Example JSON:
{"answer":"C"}
```

### task_illustrations__library__rotated_tile_label / single / answer_and_annotation / sample 3015598818149380

- `instance_seed`: `3015598818149380`
- `word_count`: `61`
- `body_word_count`: `22`

```text
The scene shows a library room containing 6 labeled book sections. Select the letter of the tile whose library fragment is rotated.
Annotation format: set "annotation" to one [x0, y0, x1, y1] box around the rotated tile in image pixel coordinates.
Answer format: set "answer" to the letter of the rotated tile.
Example JSON:
{"annotation":[350,42,670,362],"answer":"B"}
```

### task_illustrations__library__rotated_tile_label / single / answer_only / sample 3015598818149380

- `instance_seed`: `3015598818149380`
- `word_count`: `40`
- `body_word_count`: `22`

```text
The scene shows a library room containing 6 labeled book sections. Select the letter of the tile whose library fragment is rotated.
Format for the "answer" field: set "answer" to the letter of the rotated tile.
Example JSON:
{"answer":"B"}
```

### task_illustrations__library__swapped_tile_pair_label / single / answer_and_annotation / sample 1937792956452180

- `instance_seed`: `1937792956452180`
- `word_count`: `76`
- `body_word_count`: `26`

```text
This library scene contains 6 labeled book sections. Two numbered cells in the library grid are out of place. Select the option naming those two cells.
Annotation format: set "annotation" to a JSON array containing exactly two [x0, y0, x1, y1] boxes around the swapped cells in image pixel coordinates.
Answer field: set "answer" to the option letter naming the two swapped cells.
Example JSON:
{"annotation":[[0,0,400,266],[800,532,1200,798]],"answer":"C"}
```

### task_illustrations__library__swapped_tile_pair_label / single / answer_only / sample 1937792956452180

- `instance_seed`: `1937792956452180`
- `word_count`: `43`
- `body_word_count`: `26`

```text
This library scene contains 6 labeled book sections. Two numbered cells in the library grid are out of place. Select the option naming those two cells.
Answer format: set "answer" to the option letter naming the two swapped cells.
Example JSON:
{"answer":"C"}
```

### task_illustrations__park_playground__jigsaw_arrangement_label / single / answer_and_annotation / sample 2342305227615701

- `instance_seed`: `2342305227615701`
- `word_count`: `58`
- `body_word_count`: `19`

```text
The canvas contains an illustrated playground park. Which option shows the park playground image with the tiles arranged correctly?
Required annotation format: set "annotation" to one [x0, y0, x1, y1] box around the selected option image in pixel coordinates.
Required answer format: set "answer" to the selected option letter.
Example JSON:
{"annotation":[594,478,1114,844],"answer":"C"}
```

### task_illustrations__park_playground__jigsaw_arrangement_label / single / answer_only / sample 2342305227615701

- `instance_seed`: `2342305227615701`
- `word_count`: `32`
- `body_word_count`: `19`

```text
The canvas contains an illustrated playground park. Which option shows the park playground image with the tiles arranged correctly?
Answer format: set "answer" to the selected option letter.
Example JSON:
{"answer":"C"}
```

### task_illustrations__park_playground__missing_patch_label / single / answer_and_annotation / sample 8431505657878322

- `instance_seed`: `8431505657878322`
- `word_count`: `66`
- `body_word_count`: `19`

```text
The canvas contains an illustrated playground park. Find the option that completes the missing part of the park scene.
Annotation format: set "annotation" to a JSON object with "missing_region" and "selected_option" keys, each mapped to a [x0, y0, x1, y1] pixel box.
Answer format: set "answer" to the selected option letter.
Example JSON:
{"annotation":{"missing_region":[152,188,356,330],"selected_option":[708,612,912,754]},"answer":"C"}
```

### task_illustrations__park_playground__missing_patch_label / single / answer_only / sample 8431505657878322

- `instance_seed`: `8431505657878322`
- `word_count`: `33`
- `body_word_count`: `19`

```text
The canvas contains an illustrated playground park. Find the option that completes the missing part of the park scene.
Final answer format: set "answer" to the selected option letter.
Example JSON:
{"answer":"C"}
```

### task_illustrations__park_playground__person_count / single / answer_and_annotation / sample 499498406947278

- `instance_seed`: `499498406947278`
- `word_count`: `71`
- `body_word_count`: `16`

```text
The image shows an illustrated park playground. How many people can be seen in the scene?
Required annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around each visible person.
Required answer format: set "answer" to the total count of visible people as an integer.
Example JSON:
{"annotation":[[176,511,236,611],[486,593,546,693],[824,455,884,555]],"answer":3}
```

### task_illustrations__park_playground__person_count / single / answer_only / sample 499498406947278

- `instance_seed`: `499498406947278`
- `word_count`: `35`
- `body_word_count`: `16`

```text
The image shows an illustrated park playground. How many people can be seen in the scene?
Final answer format: set "answer" to the total count of visible people as an integer.
Example JSON:
{"answer":3}
```

### task_illustrations__park_playground__playground_equipment_count / single / answer_and_annotation / sample 3693532076136765

- `instance_seed`: `3693532076136765`
- `word_count`: `66`
- `body_word_count`: `14`

```text
The canvas contains an illustrated playground park. Find every slides. What is the count?
Final answer format: set "answer" to the count of slides as an integer.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around each counted slides.
Example JSON:
{"annotation":[[162,315,282,435],[430,335,558,455],[700,309,836,429]],"answer":3}
```

### task_illustrations__park_playground__playground_equipment_count / single / answer_only / sample 3693532076136765

- `instance_seed`: `3693532076136765`
- `word_count`: `33`
- `body_word_count`: `14`

```text
The canvas contains an illustrated playground park. Find every slides. What is the count?
Format for the "answer" field: set "answer" to the count of slides as an integer.
Example JSON:
{"answer":3}
```

### task_illustrations__park_playground__rotated_tile_label / single / answer_and_annotation / sample 5554761700961027

- `instance_seed`: `5554761700961027`
- `word_count`: `51`
- `body_word_count`: `14`

```text
The canvas contains an illustrated playground park. Which tile is turned the wrong way?
Final answer format: set "answer" to the selected tile letter.
Annotation format: set "annotation" to one [x0, y0, x1, y1] box around the rotated tile in pixel coordinates.
Example JSON:
{"annotation":[438,168,756,436],"answer":"B"}
```

### task_illustrations__park_playground__rotated_tile_label / single / answer_only / sample 5554761700961027

- `instance_seed`: `5554761700961027`
- `word_count`: `27`
- `body_word_count`: `23`

```text
The canvas contains an illustrated playground park. Which tile is turned the wrong way?
Answer field: set "answer" to the selected tile letter.
Example JSON:
{"answer":"B"}
```

### task_illustrations__park_playground__swapped_tile_pair_label / single / answer_and_annotation / sample 8696216035388777

- `instance_seed`: `8696216035388777`
- `word_count`: `69`
- `body_word_count`: `20`

```text
The picture shows a synthetic park playground. Choose the option that names the two grid cells whose patches were exchanged.
Format for the "annotation" field: set "annotation" to a JSON array containing two [x0, y0, x1, y1] boxes around the two swapped numbered cells.
Format for the "answer" field: set "answer" to the selected option letter.
Example JSON:
{"annotation":[[0,0,400,266],[800,532,1200,798]],"answer":"C"}
```

### task_illustrations__park_playground__swapped_tile_pair_label / single / answer_only / sample 8696216035388777

- `instance_seed`: `8696216035388777`
- `word_count`: `33`
- `body_word_count`: `29`

```text
The picture shows a synthetic park playground. Choose the option that names the two grid cells whose patches were exchanged.
Answer field: set "answer" to the selected option letter.
Example JSON:
{"answer":"C"}
```

### task_illustrations__pixel_village__missing_patch_label / single / answer_and_annotation / sample 528450688560520

- `instance_seed`: `528450688560520`
- `word_count`: `64`
- `body_word_count`: `17`

```text
This illustration shows a pixel village from above. Select the option that fills the missing patch exactly.
Annotation format: set "annotation" to a JSON object with "missing_region" and "selected_option" keys, each mapped to a [x0, y0, x1, y1] pixel box.
Answer format: set "answer" to the selected option letter.
Example JSON:
{"annotation":{"missing_region":[152,188,356,330],"selected_option":[708,612,912,754]},"answer":"C"}
```

### task_illustrations__pixel_village__missing_patch_label / single / answer_only / sample 528450688560520

- `instance_seed`: `528450688560520`
- `word_count`: `33`
- `body_word_count`: `17`

```text
This illustration shows a pixel village from above. Select the option that fills the missing patch exactly.
Format for the "answer" field: set "answer" to the selected option letter.
Example JSON:
{"answer":"C"}
```

### task_illustrations__pixel_village__object_type_count / single / answer_and_annotation / sample 5325182079928941

- `instance_seed`: `5325182079928941`
- `word_count`: `65`
- `body_word_count`: `13`

```text
The picture shows a pixel village map. How many people can be seen?
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around each counted person.
Answer format: set "answer" to the count of visible people as an integer.
Example JSON:
{"annotation":[[160,240,224,304],[416,208,480,272],[672,368,736,432]],"answer":3}
```

### task_illustrations__pixel_village__object_type_count / single / answer_only / sample 5325182079928941

- `instance_seed`: `5325182079928941`
- `word_count`: `33`
- `body_word_count`: `13`

```text
The picture shows a pixel village map. How many people can be seen?
Format for the "answer" field: set "answer" to the count of visible people as an integer.
Example JSON:
{"answer":3}
```

### task_illustrations__pixel_village__person_path_count / single / answer_and_annotation / sample 3217041742434763

- `instance_seed`: `3217041742434763`
- `word_count`: `77`
- `body_word_count`: `18`

```text
This illustration shows a pixel village from above. Find every person on a path. What is the count?
Required annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around each counted person on a path.
Required answer format: set "answer" to the count of people on the paths as an integer.
Example JSON:
{"annotation":[[288,320,352,384],[448,256,512,320],[576,384,640,448]],"answer":3}
```

### task_illustrations__pixel_village__person_path_count / single / answer_only / sample 3217041742434763

- `instance_seed`: `3217041742434763`
- `word_count`: `40`
- `body_word_count`: `18`

```text
This illustration shows a pixel village from above. Find every person on a path. What is the count?
Format for the "answer" field: set "answer" to the count of people on the paths as an integer.
Example JSON:
{"answer":3}
```

### task_illustrations__pixel_village__river_side_object_count / single / answer_and_annotation / sample 1223931692419380

- `instance_seed`: `1223931692419380`
- `word_count`: `81`
- `body_word_count`: `15`

```text
The picture shows a pixel village map. Count the visible people right of the river.
Format for the "annotation" field: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around each counted person right of the river.
Format for the "answer" field: set "answer" to the count of visible people right of the river as an integer.
Example JSON:
{"annotation":[[160,240,224,304],[416,208,480,272],[672,368,736,432]],"answer":3}
```

### task_illustrations__pixel_village__river_side_object_count / single / answer_only / sample 1223931692419380

- `instance_seed`: `1223931692419380`
- `word_count`: `37`
- `body_word_count`: `15`

```text
The picture shows a pixel village map. Count the visible people right of the river.
Final answer format: set "answer" to the count of visible people right of the river as an integer.
Example JSON:
{"answer":3}
```

### task_illustrations__pixel_village__rotated_tile_label / single / answer_and_annotation / sample 7860187295571026

- `instance_seed`: `7860187295571026`
- `word_count`: `57`
- `body_word_count`: `15`

```text
The canvas contains a top-down pixel village scene. Which tile is turned the wrong way?
Format for the "annotation" field: set "annotation" to the [x0, y0, x1, y1] box around the rotated tile in pixel coordinates.
Format for the "answer" field: set "answer" to the selected tile letter.
Example JSON:
{"annotation":[438,168,758,488],"answer":"B"}
```

### task_illustrations__pixel_village__rotated_tile_label / single / answer_only / sample 7860187295571026

- `instance_seed`: `7860187295571026`
- `word_count`: `28`
- `body_word_count`: `24`

```text
The canvas contains a top-down pixel village scene. Which tile is turned the wrong way?
Answer field: set "answer" to the selected tile letter.
Example JSON:
{"answer":"B"}
```

### task_illustrations__pixel_village__swapped_tile_pair_label / single / answer_and_annotation / sample 3017789401657728

- `instance_seed`: `3017789401657728`
- `word_count`: `63`
- `body_word_count`: `20`

```text
The scene shows a top-down pixel village. Find the two numbered cells that were exchanged and choose the matching option.
Annotation format: set "annotation" to a JSON array containing two [x0, y0, x1, y1] boxes around the two swapped numbered cells.
Answer format: set "answer" to the selected option letter.
Example JSON:
{"annotation":[[0,0,400,280],[800,560,1200,840]],"answer":"C"}
```

### task_illustrations__pixel_village__swapped_tile_pair_label / single / answer_only / sample 3017789401657728

- `instance_seed`: `3017789401657728`
- `word_count`: `33`
- `body_word_count`: `29`

```text
The scene shows a top-down pixel village. Find the two numbered cells that were exchanged and choose the matching option.
Answer field: set "answer" to the selected option letter.
Example JSON:
{"answer":"C"}
```

### task_illustrations__pixel_village__territory_object_count / single / answer_and_annotation / sample 4190484308433794

- `instance_seed`: `4190484308433794`
- `word_count`: `77`
- `body_word_count`: `17`

```text
The scene shows a top-down pixel village. What is the number of grave markers in the cemetery?
Final answer format: set "answer" to the count of grave markers in the cemetery as an integer.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around each counted grave marker in the cemetery.
Example JSON:
{"annotation":[[112,208,176,272],[176,208,240,272],[240,208,304,272]],"answer":3}
```

### task_illustrations__pixel_village__territory_object_count / single / answer_only / sample 4190484308433794

- `instance_seed`: `4190484308433794`
- `word_count`: `37`
- `body_word_count`: `17`

```text
The scene shows a top-down pixel village. What is the number of grave markers in the cemetery?
Answer format: set "answer" to the count of grave markers in the cemetery as an integer.
Example JSON:
{"answer":3}
```

### task_illustrations__rpg_dungeon__missing_patch_label / single / answer_and_annotation / sample 3804151825947741

- `instance_seed`: `3804151825947741`
- `word_count`: `80`
- `body_word_count`: `31`

```text
This illustration shows a top-down dungeon layout with one missing patch and candidate replacements. Which option matches the removed part of the dungeon scene?
Return JSON with keys "annotation" and "answer".
Final answer format: set "answer" to the selected patch option letter.
Annotation format: set "annotation" to an object with keys "missing_region" and "selected_option"; each value is one [x0, y0, x1, y1] pixel bounding box.
Example JSON:
{"annotation":{"missing_region":[220,150,420,310],"selected_option":[580,760,780,920]},"answer":"C"}
```

### task_illustrations__rpg_dungeon__missing_patch_label / single / answer_only / sample 3804151825947741

- `instance_seed`: `3804151825947741`
- `word_count`: `43`
- `body_word_count`: `39`

```text
This illustration shows a top-down dungeon layout with one missing patch and candidate replacements. Which option matches the removed part of the dungeon scene?
Return JSON with key "answer".
Answer field: set "answer" to the selected patch option letter.
Example JSON:
{"answer":"C"}
```

### task_illustrations__rpg_dungeon__monster_chamber_count / single / answer_and_annotation / sample 937841643179344

- `instance_seed`: `937841643179344`
- `word_count`: `87`
- `body_word_count`: `40`

```text
The image shows a top-down pixel RPG dungeon with stone chambers, corridors, a player, treasure chests, and small monsters in some chambers. Looking across the treasure chambers, how many contain a visible monster?
Return JSON with keys "annotation" and "answer".
Final answer format: set "answer" to the number of treasure chambers that contain a monster.
Annotation format: set "annotation" to a list containing one [x0, y0, x1, y1] bounding box around each counted monster.
Example JSON:
{"annotation":[[236,156,284,204],[596,156,644,204]],"answer":2}
```

### task_illustrations__rpg_dungeon__monster_chamber_count / single / answer_only / sample 937841643179344

- `instance_seed`: `937841643179344`
- `word_count`: `57`
- `body_word_count`: `38`

```text
The image shows a top-down pixel RPG dungeon with stone chambers, corridors, a player, treasure chests, and small monsters in some chambers. Looking across the treasure chambers, how many contain a visible monster?
Return JSON with key "answer".
Required answer format: set "answer" to the number of treasure chambers that contain a monster.
Example JSON:
{"answer":2}
```

### task_illustrations__rpg_dungeon__reachable_chest_count / single / answer_and_annotation / sample 8356286202215882

- `instance_seed`: `8356286202215882`
- `word_count`: `91`
- `body_word_count`: `35`

```text
The picture shows a pixel-art dungeon from above, including corridors, chambers, blockers, and treasure chests. From the player's position, how many chests are connected by unblocked floor paths?
Return JSON with keys "annotation" and "answer".
Annotation format: set "annotation" to a list containing one [x0, y0, x1, y1] bounding box around each counted reachable chest; use an empty list when the answer is 0.
Answer field: set "answer" to the number of treasure chests reachable from the player.
Example JSON:
{"annotation":[[236,156,284,204],[596,156,644,204]],"answer":2}
```

### task_illustrations__rpg_dungeon__reachable_chest_count / single / answer_only / sample 8356286202215882

- `instance_seed`: `8356286202215882`
- `word_count`: `51`
- `body_word_count`: `33`

```text
The picture shows a pixel-art dungeon from above, including corridors, chambers, blockers, and treasure chests. From the player's position, how many chests are connected by unblocked floor paths?
Return JSON with key "answer".
Answer format: set "answer" to the number of treasure chests reachable from the player.
Example JSON:
{"answer":2}
```

### task_illustrations__rpg_dungeon__safe_reachable_chest_count / single / answer_and_annotation / sample 427078276929202

- `instance_seed`: `427078276929202`
- `word_count`: `106`
- `body_word_count`: `47`

```text
The scene shows a top-down RPG-style dungeon map with walkable floor, blocked passages, treasure chests, and monsters inside some chambers. How many treasure chests can the player reach without passing through boulder-blocked paths, after excluding chests in chambers with monsters?
Return JSON with keys "annotation" and "answer".
Final answer format: set "answer" to the number of reachable treasure chests after excluding chests in monster chambers.
Annotation format: set "annotation" to a list containing one [x0, y0, x1, y1] bounding box around each counted chest; use an empty list when the answer is 0.
Example JSON:
{"annotation":[[236,156,284,204],[596,156,644,204]],"answer":2}
```

### task_illustrations__rpg_dungeon__safe_reachable_chest_count / single / answer_only / sample 427078276929202

- `instance_seed`: `427078276929202`
- `word_count`: `67`
- `body_word_count`: `45`

```text
The scene shows a top-down RPG-style dungeon map with walkable floor, blocked passages, treasure chests, and monsters inside some chambers. How many treasure chests can the player reach without passing through boulder-blocked paths, after excluding chests in chambers with monsters?
Return JSON with key "answer".
Required answer format: set "answer" to the number of reachable treasure chests after excluding chests in monster chambers.
Example JSON:
{"answer":2}
```

### task_illustrations__rpg_house__door_state_count / closed_door_count / answer_and_annotation / sample 3860058099758893

- `instance_seed`: `3860058099758893`
- `word_count`: `70`
- `body_word_count`: `29`

```text
The scene shows a top-down RPG-style house layout with rooms connected by doorways. Count each closed door once. What is the total?
Return JSON with keys "annotation" and "answer".
Annotation format: set "annotation" to one [x, y] point on each counted door in image pixel coordinates.
Answer field: set "answer" to the number of doors in the requested state.
Example JSON:
{"annotation":[[320,246],[480,486],[640,246]],"answer":3}
```

### task_illustrations__rpg_house__door_state_count / closed_door_count / answer_only / sample 3860058099758893

- `instance_seed`: `3860058099758893`
- `word_count`: `44`
- `body_word_count`: `40`

```text
The scene shows a top-down RPG-style house layout with rooms connected by doorways. Count each closed door once. What is the total?
Return JSON with key "answer".
Answer field: set "answer" to the number of doors in the requested state.
Example JSON:
{"answer":3}
```

### task_illustrations__rpg_house__door_state_count / open_door_count / answer_and_annotation / sample 3931454571182550

- `instance_seed`: `3931454571182550`
- `word_count`: `75`
- `body_word_count`: `33`

```text
The picture shows a pixel-art house interior from above, including rooms, walls, and doors. How many doors are open enough for a player to pass through?
Return JSON with keys "annotation" and "answer".
Final answer format: set "answer" to the number of doors in the requested state.
Annotation format: set "annotation" to one [x, y] point on each counted door in image pixel coordinates.
Example JSON:
{"annotation":[[320,246],[480,486],[640,246]],"answer":3}
```

### task_illustrations__rpg_house__door_state_count / open_door_count / answer_only / sample 3931454571182550

- `instance_seed`: `3931454571182550`
- `word_count`: `48`
- `body_word_count`: `44`

```text
The picture shows a pixel-art house interior from above, including rooms, walls, and doors. How many doors are open enough for a player to pass through?
Return JSON with key "answer".
Answer field: set "answer" to the number of doors in the requested state.
Example JSON:
{"answer":3}
```

### task_illustrations__rpg_house__missing_patch_label / single / answer_and_annotation / sample 3365172470024007

- `instance_seed`: `3365172470024007`
- `word_count`: `86`
- `body_word_count`: `38`

```text
The picture shows a pixel-art house interior from above, including rooms, walls, and doors. One rectangular region is missing from the source house image. Which patch option restores that missing region?
Return JSON with keys "annotation" and "answer".
Final answer format: set "answer" to the selected patch option letter.
Annotation format: set "annotation" to an object with keys "missing_region" and "selected_option"; each value is a [x0, y0, x1, y1] pixel box.
Example JSON:
{"annotation":{"missing_region":[120,80,300,220],"selected_option":[430,720,610,860]},"answer":"C"}
```

### task_illustrations__rpg_house__missing_patch_label / single / answer_only / sample 3365172470024007

- `instance_seed`: `3365172470024007`
- `word_count`: `51`
- `body_word_count`: `36`

```text
The picture shows a pixel-art house interior from above, including rooms, walls, and doors. One rectangular region is missing from the source house image. Which patch option restores that missing region?
Return JSON with key "answer".
Final answer format: set "answer" to the selected patch option letter.
Example JSON:
{"answer":"C"}
```

### task_illustrations__rpg_house__reachable_room_count / single / answer_and_annotation / sample 1974223144035174

- `instance_seed`: `1974223144035174`
- `word_count`: `105`
- `body_word_count`: `42`

```text
The canvas contains a top-down RPG house map with enclosed rooms, walls, and doorways. Starting from the room with the player, how many other rooms can the player reach by passing only through open doors?
Return JSON with keys "annotation" and "answer".
Annotation format: set "annotation" to an object with keys "player" and "reachable_rooms"; "player" contains one [x, y] point on the player, and "reachable_rooms" contains one [x, y] point near the center of each counted room.
Answer field: set "answer" to the number of other rooms reachable from the player's room.
Example JSON:
{"annotation":{"player":[[420,360]],"reachable_rooms":[[260,180],[620,180]]},"answer":2}
```

### task_illustrations__rpg_house__reachable_room_count / single / answer_only / sample 1974223144035174

- `instance_seed`: `1974223144035174`
- `word_count`: `59`
- `body_word_count`: `55`

```text
The canvas contains a top-down RPG house map with enclosed rooms, walls, and doorways. Starting from the room with the player, how many other rooms can the player reach by passing only through open doors?
Return JSON with key "answer".
Answer field: set "answer" to the number of other rooms reachable from the player's room.
Example JSON:
{"answer":2}
```

### task_illustrations__rpg_house__room_count / single / answer_and_annotation / sample 403690134144072

- `instance_seed`: `403690134144072`
- `word_count`: `75`
- `body_word_count`: `27`

```text
This illustration shows an RPG-style indoor house layout from above. How many enclosed rooms are shown in the house layout?
Return JSON with keys "annotation" and "answer".
Required annotation format: set "annotation" to one [x, y] point near the center of each counted room in image pixel coordinates.
Required answer format: set "answer" to the total number of enclosed rooms.
Example JSON:
{"annotation":[[168,148],[456,148],[744,148],[312,492],[648,492]],"answer":5}
```

### task_illustrations__rpg_house__room_count / single / answer_only / sample 403690134144072

- `instance_seed`: `403690134144072`
- `word_count`: `40`
- `body_word_count`: `25`

```text
This illustration shows an RPG-style indoor house layout from above. How many enclosed rooms are shown in the house layout?
Return JSON with key "answer".
Answer format: set "answer" to the total number of enclosed rooms.
Example JSON:
{"answer":5}
```

### task_illustrations__rpg_house__swapped_tile_pair_label / single / answer_and_annotation / sample 7527616123174788

- `instance_seed`: `7527616123174788`
- `word_count`: `81`
- `body_word_count`: `36`

```text
The canvas contains a top-down RPG house map with enclosed rooms, walls, and doorways. Two numbered tiles are in each other's positions. Which lettered option gives the swapped pair?
Return JSON with keys "annotation" and "answer".
Final answer format: set "answer" to the option letter naming the two swapped numbered tiles.
Annotation format: set "annotation" to two [x0, y0, x1, y1] pixel boxes around the swapped numbered tiles.
Example JSON:
{"annotation":[[0,0,400,266],[800,532,1200,798]],"answer":"D"}
```

### task_illustrations__rpg_house__swapped_tile_pair_label / single / answer_only / sample 7527616123174788

- `instance_seed`: `7527616123174788`
- `word_count`: `53`
- `body_word_count`: `34`

```text
The canvas contains a top-down RPG house map with enclosed rooms, walls, and doorways. Two numbered tiles are in each other's positions. Which lettered option gives the swapped pair?
Return JSON with key "answer".
Final answer format: set "answer" to the option letter naming the two swapped numbered tiles.
Example JSON:
{"answer":"D"}
```

### task_illustrations__rpg_tactical_map__counterfactual_terrain_conversion_cost_value / single / answer_and_annotation / sample 6238966390302142

- `instance_seed`: `6238966390302142`
- `word_count`: `167`
- `body_word_count`: `96`

```text
The scene shows a grid-based tactical map from above, with a blue unit, varied terrain, and one marked destination tile. The blue unit starts on its current tile. Grass, roads, and bridges cost 1 movement point; forests cost 2; mountains cost 3; water cannot be entered. Moves are only up, down, left, or right. Before moving, exactly one water, mountain, or forest tile may be changed into a road tile. After that conversion, how many movement points are needed to reach the marked destination tile using the cheapest path?
Return JSON with keys "annotation" and "answer".
Format for the "annotation" field: set "annotation" to an object with keys "player_cell", "target_cell", and "changed_cell", each mapping to one [x0, y0, x1, y1] pixel bounding box around that tile.
Format for the "answer" field: set "answer" to the fewest number of movement points needed after the best single terrain-to-road conversion.
Example JSON:
{"annotation":{"player_cell":[160,320,240,400],"target_cell":[320,320,400,400],"changed_cell":[240,320,320,400]},"answer":5}
```

### task_illustrations__rpg_tactical_map__counterfactual_terrain_conversion_cost_value / single / answer_only / sample 6238966390302142

- `instance_seed`: `6238966390302142`
- `word_count`: `116`
- `body_word_count`: `94`

```text
The scene shows a grid-based tactical map from above, with a blue unit, varied terrain, and one marked destination tile. The blue unit starts on its current tile. Grass, roads, and bridges cost 1 movement point; forests cost 2; mountains cost 3; water cannot be entered. Moves are only up, down, left, or right. Before moving, exactly one water, mountain, or forest tile may be changed into a road tile. After that conversion, how many movement points are needed to reach the marked destination tile using the cheapest path?
Return JSON with key "answer".
Answer format: set "answer" to the fewest number of movement points needed after the best single terrain-to-road conversion.
Example JSON:
{"answer":5}
```

### task_illustrations__rpg_tactical_map__movement_cost_value / single / answer_and_annotation / sample 5297355580750692

- `instance_seed`: `5297355580750692`
- `word_count`: `143`
- `body_word_count`: `78`

```text
This illustration shows a tactical RPG grid map where a blue unit can move across terrain toward the marked target tile. The blue unit starts on its current tile. Grass, roads, and bridges cost 1 movement point; forests cost 2; mountains cost 3; water cannot be entered. Moves are only up, down, left, or right. How many movement points are needed to reach the marked destination tile using the cheapest path?
Return JSON with keys "annotation" and "answer".
Format for the "annotation" field: set "annotation" to an object with keys "player_cell" and "target_cell", each mapping to one [x0, y0, x1, y1] pixel bounding box around that tile.
Format for the "answer" field: set "answer" to the fewest number of movement points needed to reach the marked target tile.
Example JSON:
{"annotation":{"player_cell":[160,320,240,400],"target_cell":[320,320,400,400]},"answer":7}
```

### task_illustrations__rpg_tactical_map__movement_cost_value / single / answer_only / sample 5297355580750692

- `instance_seed`: `5297355580750692`
- `word_count`: `98`
- `body_word_count`: `94`

```text
This illustration shows a tactical RPG grid map where a blue unit can move across terrain toward the marked target tile. The blue unit starts on its current tile. Grass, roads, and bridges cost 1 movement point; forests cost 2; mountains cost 3; water cannot be entered. Moves are only up, down, left, or right. How many movement points are needed to reach the marked destination tile using the cheapest path?
Return JSON with key "answer".
Answer field: set "answer" to the fewest number of movement points needed to reach the marked target tile.
Example JSON:
{"answer":7}
```

### task_illustrations__rpg_tactical_map__movement_reachable_tile_count / single / answer_and_annotation / sample 4239604344828419

- `instance_seed`: `4239604344828419`
- `word_count`: `121`
- `body_word_count`: `67`

```text
This illustration shows a tactical RPG grid map where a blue unit can move across terrain. With up to 2 movement points, count the tiles the blue unit can reach, excluding its starting tile. Grass, roads, and bridges cost 1 movement point; forests cost 2; mountains cost 3; water cannot be entered. Moves are only up, down, left, or right.
Return JSON with keys "annotation" and "answer".
Final answer format: set "answer" to the number of reachable tiles, excluding the blue unit's starting tile.
Annotation format: set "annotation" to a list of [x0, y0, x1, y1] pixel bounding boxes around each counted reachable tile.
Example JSON:
{"annotation":[[240,160,320,240],[320,160,400,240],[240,240,320,320]],"answer":3}
```

### task_illustrations__rpg_tactical_map__movement_reachable_tile_count / single / answer_only / sample 4239604344828419

- `instance_seed`: `4239604344828419`
- `word_count`: `86`
- `body_word_count`: `65`

```text
This illustration shows a tactical RPG grid map where a blue unit can move across terrain. With up to 2 movement points, count the tiles the blue unit can reach, excluding its starting tile. Grass, roads, and bridges cost 1 movement point; forests cost 2; mountains cost 3; water cannot be entered. Moves are only up, down, left, or right.
Return JSON with key "answer".
Final answer format: set "answer" to the number of reachable tiles, excluding the blue unit's starting tile.
Example JSON:
{"answer":3}
```

### task_illustrations__rpg_tactical_map__movement_reachable_tile_label / single / answer_and_annotation / sample 3336864314380235

- `instance_seed`: `3336864314380235`
- `word_count`: `110`
- `body_word_count`: `72`

```text
The canvas contains a top-down RPG battle map with grass, roads, forests, water, bridges, mountains, one blue unit, and lettered tiles. The blue unit starts on its current tile. It has 6 movement points. Grass, roads, and bridges cost 1 movement point; forests cost 2; mountains cost 3; water cannot be entered. Moves are only up, down, left, or right. Which lettered tile is reachable?
Return JSON with keys "annotation" and "answer".
Final answer format: set "answer" to the letter of the reachable tile.
Annotation format: set "annotation" to one [x0, y0, x1, y1] pixel bounding box around the selected tile.
Example JSON:
{"annotation":[320,160,400,240],"answer":"C"}
```

### task_illustrations__rpg_tactical_map__movement_reachable_tile_label / single / answer_only / sample 3336864314380235

- `instance_seed`: `3336864314380235`
- `word_count`: `86`
- `body_word_count`: `70`

```text
The canvas contains a top-down RPG battle map with grass, roads, forests, water, bridges, mountains, one blue unit, and lettered tiles. The blue unit starts on its current tile. It has 6 movement points. Grass, roads, and bridges cost 1 movement point; forests cost 2; mountains cost 3; water cannot be entered. Moves are only up, down, left, or right. Which lettered tile is reachable?
Return JSON with key "answer".
Final answer format: set "answer" to the letter of the reachable tile.
Example JSON:
{"answer":"C"}
```

### task_illustrations__rpg_tactical_map__movement_sequence_endpoint_label / single / answer_and_annotation / sample 5676302829751498

- `instance_seed`: `5676302829751498`
- `word_count`: `91`
- `body_word_count`: `43`

```text
The picture shows a pixel-art tactical movement map containing terrain tiles, a blue unit, and lettered candidate tiles. Follow this ordered move list from the blue unit: left, up, up, up. Select the final lettered tile.
Return JSON with keys "annotation" and "answer".
Format for the "annotation" field: set "annotation" to one [x0, y0, x1, y1] pixel bounding box around the selected ending tile.
Format for the "answer" field: set "answer" to the letter of the tile where the blue unit ends.
Example JSON:
{"annotation":[320,160,400,240],"answer":"C"}
```

### task_illustrations__rpg_tactical_map__movement_sequence_endpoint_label / single / answer_only / sample 5676302829751498

- `instance_seed`: `5676302829751498`
- `word_count`: `60`
- `body_word_count`: `56`

```text
The picture shows a pixel-art tactical movement map containing terrain tiles, a blue unit, and lettered candidate tiles. Follow this ordered move list from the blue unit: left, up, up, up. Select the final lettered tile.
Return JSON with key "answer".
Answer field: set "answer" to the letter of the tile where the blue unit ends.
Example JSON:
{"answer":"C"}
```

### task_illustrations__rpg_tactical_map__terrain_type_tile_count / single / answer_and_annotation / sample 237409349525424

- `instance_seed`: `237409349525424`
- `word_count`: `80`
- `body_word_count`: `32`

```text
This illustration shows a tactical RPG grid map where a blue unit can move across terrain. How many visible mountain tiles are in the map?
Return JSON with keys "annotation" and "answer".
Annotation format: set "annotation" to a list of [x0, y0, x1, y1] pixel bounding boxes around each counted {terrain_label} tile.
Answer format: set "answer" to the number of visible {terrain_label} tiles.
Example JSON:
{"annotation":[[80,160,160,240],[160,160,240,240],[160,240,240,320]],"answer":3}
```

### task_illustrations__rpg_tactical_map__terrain_type_tile_count / single / answer_only / sample 237409349525424

- `instance_seed`: `237409349525424`
- `word_count`: `45`
- `body_word_count`: `41`

```text
This illustration shows a tactical RPG grid map where a blue unit can move across terrain. How many visible mountain tiles are in the map?
Return JSON with key "answer".
Answer field: set "answer" to the number of visible {terrain_label} tiles.
Example JSON:
{"answer":3}
```

### task_illustrations__rpg_tactical_map__water_barrier_unreachable_tile_label / single / answer_and_annotation / sample 4375500550605400

- `instance_seed`: `4375500550605400`
- `word_count`: `105`
- `body_word_count`: `66`

```text
The scene shows a grid-based tactical map from above, with a blue unit, one water barrier crossing the map, and lettered target tiles. Using only the water-blocking rule, choose the lettered tile that cannot be reached from the blue unit. Water tiles cannot be crossed; all non-water tiles can be crossed. Moves are only up, down, left, or right.
Return JSON with keys "annotation" and "answer".
Final answer format: set "answer" to the letter of the unreachable tile.
Annotation format: set "annotation" to one [x0, y0, x1, y1] pixel bounding box around the selected unreachable tile.
Example JSON:
{"annotation":[480,160,560,240],"answer":"D"}
```

### task_illustrations__rpg_tactical_map__water_barrier_unreachable_tile_label / single / answer_only / sample 4375500550605400

- `instance_seed`: `4375500550605400`
- `word_count`: `79`
- `body_word_count`: `64`

```text
The scene shows a grid-based tactical map from above, with a blue unit, one water barrier crossing the map, and lettered target tiles. Using only the water-blocking rule, choose the lettered tile that cannot be reached from the blue unit. Water tiles cannot be crossed; all non-water tiles can be crossed. Moves are only up, down, left, or right.
Return JSON with key "answer".
Answer format: set "answer" to the letter of the unreachable tile.
Example JSON:
{"answer":"D"}
```

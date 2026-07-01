# Prompt Concision Audit

- rendered prompts: `158`
- tasks covered: `60`
- observed query ids covered: `79`

## Variant Coverage

- tasks with incomplete query ids or generation errors: `0`

| task | expected_query_ids | collected_query_id_counts | generated | issues |
| --- | --- | --- | ---: | --- |
| task_three_d__carousel__belt_object_type_count_arithmetic_value | `difference_count, total_count` | `{'difference_count': 1, 'total_count': 1}` | 2 | `` |
| task_three_d__carousel__belt_total_object_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__carousel__between_object_type_anchors_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__carousel__color_ordered_adjacent_pair_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__carousel__color_transfer_total_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__carousel__object_type_ordered_adjacent_pair_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__carousel__object_type_transfer_total_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__carousel__scoped_belt_color_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__carousel__scoped_belt_object_type_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__carousel__scoped_color_type_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__conveyor__belt_total_object_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__conveyor__between_object_type_anchors_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__conveyor__color_ordered_adjacent_pair_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__conveyor__color_transfer_total_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__conveyor__lane_object_type_count_arithmetic_value | `difference_count, total_count` | `{'difference_count': 1, 'total_count': 1}` | 2 | `` |
| task_three_d__conveyor__object_type_ordered_adjacent_pair_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__conveyor__object_type_transfer_total_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__conveyor__scoped_belt_color_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__conveyor__scoped_belt_object_type_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__conveyor__scoped_color_type_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__object_cluster__color_count_arithmetic | `difference_count, total_count` | `{'difference_count': 1, 'total_count': 1}` | 2 | `` |
| task_three_d__object_cluster__color_membership_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__object_cluster__counterfactual_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__object_cluster__multi_attribute_and_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__object_cluster__multi_attribute_exclusion_count | `color_and_not_type_count, type_and_not_color_count` | `{'color_and_not_type_count': 1, 'type_and_not_color_count': 1}` | 2 | `` |
| task_three_d__object_cluster__multi_attribute_or_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__object_cluster__multi_attribute_xor_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__object_cluster__object_type_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__object_cluster__object_type_count_arithmetic | `difference_count, total_count` | `{'difference_count': 1, 'total_count': 1}` | 2 | `` |
| task_three_d__object_cluster__total_object_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__object_scene__between_references_label | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__object_scene__camera_depth_relation_count | `closer_to_camera_than_reference_count, farther_from_camera_than_reference_count` | `{'closer_to_camera_than_reference_count': 1, 'farther_from_camera_than_reference_count': 1}` | 2 | `` |
| task_three_d__object_scene__camera_distance_extremum_label | `closest_to_camera, farthest_from_camera` | `{'closest_to_camera': 1, 'farthest_from_camera': 1}` | 2 | `` |
| task_three_d__object_scene__height_extremum_label | `highest_above_floor, lowest_above_floor` | `{'highest_above_floor': 1, 'lowest_above_floor': 1}` | 2 | `` |
| task_three_d__object_scene__image_plane_lateral_relation_count | `left_of_reference_in_view_count, right_of_reference_in_view_count` | `{'left_of_reference_in_view_count': 1, 'right_of_reference_in_view_count': 1}` | 2 | `` |
| task_three_d__object_scene__line_side_label | `left_of_directed_line, right_of_directed_line` | `{'left_of_directed_line': 1, 'right_of_directed_line': 1}` | 2 | `` |
| task_three_d__object_scene__marked_point_depth_extremum_label | `closest_marked_point, farthest_marked_point` | `{'closest_marked_point': 1, 'farthest_marked_point': 1}` | 2 | `` |
| task_three_d__object_scene__marked_point_vertical_relation_label | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__object_scene__multiview_object_match_label | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__object_scene__object_relation_label | `inside_prop, on_top_of_prop, under_prop` | `{'inside_prop': 1, 'on_top_of_prop': 1, 'under_prop': 1}` | 3 | `` |
| task_three_d__object_scene__occlusion_order_label | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__object_scene__point_camera_distance_order_label | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__object_scene__point_on_object_line_label | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__object_scene__reference_nearest_label | `closest_to_reference, farthest_from_reference` | `{'closest_to_reference': 1, 'farthest_from_reference': 1}` | 2 | `` |
| task_three_d__object_scene__reference_triangle_inside_label | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__room__wall_object_camera_distance_label | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__room__wall_object_same_wall_reference_label | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__room__wall_object_side_relation_label | `left_of_reference_on_wall, right_of_reference_on_wall` | `{'left_of_reference_on_wall': 1, 'right_of_reference_on_wall': 1}` | 2 | `` |
| task_three_d__street__intersection_nearest_label | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__street__lane_ahead_object_label | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__street__same_road_arm_reference_label | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__surface_fixture__color_count_after_operations_value | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__surface_fixture__color_frequency_option_label | `absent_color, most_frequent_color` | `{'absent_color': 1, 'most_frequent_color': 1}` | 2 | `` |
| task_three_d__surface_fixture__colored_element_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__surface_fixture__element_count_extremum_label | `highest_element_count, lowest_element_count` | `{'highest_element_count': 1, 'lowest_element_count': 1}` | 2 | `` |
| task_three_d__surface_fixture__recolor_board_match_label | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__surface_fixture__repeated_element_count | `single` | `{'single': 1}` | 2 | `` |
| task_three_d__surface_fixture__scoped_colored_element_count | `column_scoped_color_count, row_scoped_color_count` | `{'column_scoped_color_count': 1, 'row_scoped_color_count': 1}` | 2 | `` |
| task_three_d__warehouse__nearest_candidate_to_reference_label | `closest_object_to_reference, closest_object_to_robot` | `{'closest_object_to_reference': 1, 'closest_object_to_robot': 1}` | 2 | `` |
| task_three_d__warehouse__robot_forward_path_label | `single` | `{'single': 1}` | 2 | `` |

## Longest Prompts

### task_three_d__carousel__color_ordered_adjacent_pair_count / answer_and_annotation / sample 5274351976002687

- `query_id`: `single`
- `instance_seed`: `5274351976002687`
- `word_count`: `113`
- `body_word_count`: `38`

```text
The picture shows a baggage-style conveyor carousel with small objects on two oval belts. Following the order of the INNER belt, count each green [#37B94B] object immediately followed by a red [#E63232] object. How many pairs are there?
Format for the "annotation" field: set "annotation" to an array containing one pixel-space segment [[x0, y0], [x1, y1]] per counted adjacent ordered pair, where each endpoint is an [x, y] pixel point at an object center; the segment starts at the first object and ends at the second object.
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[[120,450],[174,494]],[[390,320],[450,370]]],"answer":2}
```

### task_three_d__object_cluster__counterfactual_count / answer_and_annotation / sample 7084808865690874

- `query_id`: `single`
- `instance_seed`: `7084808865690874`
- `word_count`: `110`
- `body_word_count`: `50`

```text
The visible scene contains many small 3D objects arranged on a plain surface. Use the visible cluster as the starting set. Apply these edits:
1. Remove 1 purple [#963ACA] pencil.
2. Add 1 blue [#2D75E6] remote control.
3. Add 2 brown [#887044] pencils.
What is the final count of pencils?
Format for the "annotation" field: set "annotation" to an array containing one [x0, y0, x1, y1] pixel box around each starting visible object matching the queried property before the edits.
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[120,450,174,494],[390,320,450,370],[704,520,756,580]],"answer":5}
```

### task_three_d__conveyor__color_ordered_adjacent_pair_count / answer_and_annotation / sample 2855360547259200

- `query_id`: `single`
- `instance_seed`: `2855360547259200`
- `word_count`: `107`
- `body_word_count`: `37`

```text
The picture shows three separate straight conveyor belts with objects on the belts. Following the order of the BOTTOM belt, count each magenta [#D02C91] object immediately followed by a yellow [#D4C21E] object. How many pairs are there?
Final answer format: set "answer" to the count as an integer.
Annotation format: set "annotation" to an array containing one pixel-space segment [[x0, y0], [x1, y1]] per counted adjacent ordered pair, where each endpoint is an [x, y] pixel point at an object center; the segment starts at the first object and ends at the second object.
Example JSON:
{"annotation":[[[120,450],[174,494]],[[390,320],[450,370]]],"answer":2}
```

### task_three_d__conveyor__lane_object_type_count_arithmetic_value / answer_and_annotation / sample 4612491792315183

- `query_id`: `total_count`
- `instance_seed`: `4612491792315183`
- `word_count`: `107`
- `body_word_count`: `34`

```text
The picture shows three separate straight conveyor belts with objects on the belts. Count the balls on the LEFT belt and on the RIGHT belt, then add the two counts. What is the result?
Required annotation format: set "annotation" to an object with one key for each requested lane, named by lane position such as "top_objects" or "left_objects"; each value is an array of [x0, y0, x1, y1] boxes around the counted objects of the requested type for that lane.
Required answer format: set "answer" to the computed count as an integer.
Example JSON:
{"annotation":{"top_objects":[[120,450,174,494]],"middle_objects":[[390,320,450,370]]},"answer":2}
```

### task_three_d__surface_fixture__color_count_after_operations_value / answer_and_annotation / sample 5792516825434595

- `query_id`: `single`
- `instance_seed`: `5792516825434595`
- `word_count`: `107`
- `body_word_count`: `40`

```text
The scene shows a fixture surface with repeated colored surface elements. Suppose these changes happen: add 3 magenta [#D02C91] pavers; add 3 yellow [#D4C21E] pavers; remove 1 magenta [#D02C91] paver. How many yellow [#D4C21E] pavers are there after all changes?
Format for the "annotation" field: set "annotation" to an array containing one [x0, y0, x1, y1] pixel box around each original visible target-color element used as the starting count; do not mark hypothetical added elements.
Format for the "answer" field: set "answer" to the final count as an integer after applying the listed changes.
Example JSON:
{"annotation":[[120,450,174,494],[390,320,450,370]],"answer":5}
```

### task_three_d__conveyor__lane_object_type_count_arithmetic_value / answer_and_annotation / sample 4124190879239878

- `query_id`: `difference_count`
- `instance_seed`: `4124190879239878`
- `word_count`: `104`
- `body_word_count`: `33`

```text
The visual shows a three-lane conveyor with small objects on each lane. What is the difference between the number of chess pieces on the LEFT belt and the number on the RIGHT belt?
Annotation format: set "annotation" to an object with one key for each requested lane, named by lane position such as "top_objects" or "left_objects"; each value is an array of [x0, y0, x1, y1] boxes around the counted objects of the requested type for that lane.
Answer field: set "answer" to the computed count as an integer.
Example JSON:
{"annotation":{"top_objects":[[120,450,174,494]],"middle_objects":[[390,320,450,370]]},"answer":2}
```

### task_three_d__carousel__object_type_ordered_adjacent_pair_count / answer_and_annotation / sample 5284735579195479

- `query_id`: `single`
- `instance_seed`: `5284735579195479`
- `word_count`: `102`
- `body_word_count`: `27`

```text
The scene shows small 3D objects riding on two concentric elliptical conveyor belts. Count the neighboring pairs on the OUTER belt where umbrellas come immediately before cones.
Format for the "annotation" field: set "annotation" to an array containing one pixel-space segment [[x0, y0], [x1, y1]] per counted adjacent ordered pair, where each endpoint is an [x, y] pixel point at an object center; the segment starts at the first object and ends at the second object.
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[[120,450],[174,494]],[[390,320],[450,370]]],"answer":2}
```

### task_three_d__conveyor__object_type_transfer_total_count / answer_and_annotation / sample 7140846889444957

- `query_id`: `single`
- `instance_seed`: `7140846889444957`
- `word_count`: `101`
- `body_word_count`: `35`

```text
The image shows three straight parallel conveyor belts with small 3D objects on them. After transferring the puzzle pieces on the RIGHT belt to the LEFT belt, how many objects would the LEFT belt have?
Format for the "annotation" field: set "annotation" to an object with keys "source_moved_objects" and "destination_existing_objects"; each value is an array of [x0, y0, x1, y1] boxes around the corresponding objects before the move.
Format for the "answer" field: set "answer" to the resulting count as an integer.
Example JSON:
{"annotation":{"source_moved_objects":[[120,450,174,494]],"destination_existing_objects":[[390,320,450,370],[470,320,520,370]]},"answer":3}
```

### task_three_d__carousel__color_transfer_total_count / answer_and_annotation / sample 4261364338910370

- `query_id`: `single`
- `instance_seed`: `4261364338910370`
- `word_count`: `99`
- `body_word_count`: `38`

```text
A 3D conveyor carousel is shown with objects on the inner and outer belts. Suppose all brown [#887044] objects on the INNER belt are moved to the OUTER belt. How many objects would be on the OUTER belt?
Final answer format: set "answer" to the resulting count as an integer.
Annotation format: set "annotation" to an object with keys "source_moved_objects" and "destination_existing_objects"; each value is an array of [x0, y0, x1, y1] boxes around the corresponding objects before the move.
Example JSON:
{"annotation":{"source_moved_objects":[[120,450,174,494]],"destination_existing_objects":[[390,320,450,370],[470,320,520,370]]},"answer":3}
```

### task_three_d__conveyor__object_type_ordered_adjacent_pair_count / answer_and_annotation / sample 2460183435017049

- `query_id`: `single`
- `instance_seed`: `2460183435017049`
- `word_count`: `98`
- `body_word_count`: `28`

```text
The picture shows three separate straight conveyor belts with objects on the belts. How many adjacent ordered pairs on the TOP belt go from chess pieces to hats?
Final answer format: set "answer" to the count as an integer.
Annotation format: set "annotation" to an array containing one pixel-space segment [[x0, y0], [x1, y1]] per counted adjacent ordered pair, where each endpoint is an [x, y] pixel point at an object center; the segment starts at the first object and ends at the second object.
Example JSON:
{"annotation":[[[120,450],[174,494]],[[390,320],[450,370]]],"answer":2}
```

### task_three_d__carousel__belt_object_type_count_arithmetic_value / answer_and_annotation / sample 4967323396516367

- `query_id`: `difference_count`
- `instance_seed`: `4967323396516367`
- `word_count`: `96`
- `body_word_count`: `34`

```text
A 3D conveyor carousel is shown with objects on the inner and outer belts. What is the difference between the number of plates on the INNER belt and the number on the OUTER belt?
Required annotation format: set "annotation" to an object with keys "inner_objects" and "outer_objects"; each value is an array of [x0, y0, x1, y1] boxes around the counted objects of the requested type for that belt.
Required answer format: set "answer" to the computed count as an integer.
Example JSON:
{"annotation":{"inner_objects":[[120,450,174,494]],"outer_objects":[[390,320,450,370]]},"answer":2}
```

### task_three_d__carousel__belt_object_type_count_arithmetic_value / answer_and_annotation / sample 445697350293333

- `query_id`: `total_count`
- `instance_seed`: `445697350293333`
- `word_count`: `96`
- `body_word_count`: `36`

```text
The picture shows a baggage-style conveyor carousel with small objects on two oval belts. Add the count of apples on the INNER belt to the count of apples on the OUTER belt. What is the sum?
Annotation format: set "annotation" to an object with keys "inner_objects" and "outer_objects"; each value is an array of [x0, y0, x1, y1] boxes around the counted objects of the requested type for that belt.
Answer field: set "answer" to the computed count as an integer.
Example JSON:
{"annotation":{"inner_objects":[[120,450,174,494]],"outer_objects":[[390,320,450,370]]},"answer":2}
```

### task_three_d__carousel__object_type_transfer_total_count / answer_and_annotation / sample 7263895744506266

- `query_id`: `single`
- `instance_seed`: `7263895744506266`
- `word_count`: `95`
- `body_word_count`: `33`

```text
A 3D conveyor carousel is shown with objects on the inner and outer belts. What is the new total on the OUTER belt if all stars from the INNER belt are moved there?
Required annotation format: set "annotation" to an object with keys "source_moved_objects" and "destination_existing_objects"; each value is an array of [x0, y0, x1, y1] boxes around the corresponding objects before the move.
Required answer format: set "answer" to the resulting count as an integer.
Example JSON:
{"annotation":{"source_moved_objects":[[120,450,174,494]],"destination_existing_objects":[[390,320,450,370],[470,320,520,370]]},"answer":3}
```

### task_three_d__conveyor__color_transfer_total_count / answer_and_annotation / sample 7274900670379643

- `query_id`: `single`
- `instance_seed`: `7274900670379643`
- `word_count`: `95`
- `body_word_count`: `34`

```text
The scene shows small 3D objects arranged on three straight conveyor lanes. After transferring the blue [#2D75E6] objects on the MIDDLE belt to the RIGHT belt, how many objects would the RIGHT belt have?
Final answer format: set "answer" to the resulting count as an integer.
Annotation format: set "annotation" to an object with keys "source_moved_objects" and "destination_existing_objects"; each value is an array of [x0, y0, x1, y1] boxes around the corresponding objects before the move.
Example JSON:
{"annotation":{"source_moved_objects":[[120,450,174,494]],"destination_existing_objects":[[390,320,450,370],[470,320,520,370]]},"answer":3}
```

### task_three_d__street__lane_ahead_object_label / answer_and_annotation / sample 5906709959417880

- `query_id`: `single`
- `instance_seed`: `5906709959417880`
- `word_count`: `95`
- `body_word_count`: `57`

```text
The scene shows a perspective street intersection or T intersection with roads, sidewalks, crosswalk markings, street context, one red-boxed reference street object with a red travel-direction arrow, candidate street objects, and a text option panel below the scene. Which option describes the object directly ahead of the red-boxed object along the lane indicated by the red arrow?
Annotation format: set "annotation" to the bounding box [x0, y0, x1, y1] around the selected street object in the scene.
Answer format: set "answer" to the selected option letter.
Example JSON:
{"annotation":[142,118,238,178],"answer":"C"}
```

### task_three_d__object_cluster__color_count_arithmetic / answer_and_annotation / sample 4768817333180211

- `query_id`: `difference_count`
- `instance_seed`: `4768817333180211`
- `word_count`: `93`
- `body_word_count`: `33`

```text
The image contains many small 3D objects arranged on a plain surface. After subtracting the smaller count from the larger count for brown [#887044] objects and maroon [#963644] objects, what is the difference?
Annotation format: set "annotation" to an object with keys "left_operand" and "right_operand"; each value is an array of [x0, y0, x1, y1] pixel boxes around the objects in that operand group.
Answer field: set "answer" to the count as an integer.
Example JSON:
{"annotation":{"left_operand":[[120,450,174,494],[390,320,450,370]],"right_operand":[[704,520,756,580]]},"answer":1}
```

### task_three_d__object_cluster__color_count_arithmetic / answer_and_annotation / sample 3938293536365319

- `query_id`: `total_count`
- `instance_seed`: `3938293536365319`
- `word_count`: `89`
- `body_word_count`: `27`

```text
The image shows many small 3D objects arranged on a plain surface. Add the number of blue [#2D75E6] objects and magenta [#D02C91] objects. What is the total?
Required annotation format: set "annotation" to an object with keys "left_operand" and "right_operand"; each value is an array of [x0, y0, x1, y1] pixel boxes around the objects in that operand group.
Required answer format: set "answer" to the count as an integer.
Example JSON:
{"annotation":{"left_operand":[[120,450,174,494],[390,320,450,370]],"right_operand":[[704,520,756,580]]},"answer":1}
```

### task_three_d__carousel__between_object_type_anchors_count / answer_and_annotation / sample 6432946269138446

- `query_id`: `single`
- `instance_seed`: `6432946269138446`
- `word_count`: `88`
- `body_word_count`: `35`

```text
The scene shows small 3D objects riding on two concentric elliptical conveyor belts. On the OUTER belt, following the belt arrows from marked object A to marked object B, how many objects are between them?
Annotation format: set "annotation" to an array containing one [x0, y0, x1, y1] pixel box around each counted object between the marked anchors; do not include the marked anchor objects.
Answer format: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[120,450,174,494],[390,320,450,370]],"answer":2}
```

### task_three_d__conveyor__between_object_type_anchors_count / answer_and_annotation / sample 5165424042754202

- `query_id`: `single`
- `instance_seed`: `5165424042754202`
- `word_count`: `87`
- `body_word_count`: `33`

```text
The visual shows a three-lane conveyor with small objects on each lane. Looking only at the TOP belt, how many objects lie between the marked flower A and the marked puzzle piece B?
Final answer format: set "answer" to the count as an integer.
Annotation format: set "annotation" to an array containing one [x0, y0, x1, y1] pixel box around each counted object between the marked anchors; do not include the marked anchor objects.
Example JSON:
{"annotation":[[120,450,174,494],[390,320,450,370]],"answer":2}
```

### task_three_d__conveyor__scoped_color_type_count / answer_and_annotation / sample 2503222502801942

- `query_id`: `single`
- `instance_seed`: `2503222502801942`
- `word_count`: `87`
- `body_word_count`: `27`

```text
The image shows three straight parallel conveyor belts with small 3D objects on them. Looking only at the TOP belt, how many cyan [#34C4E0] stars are visible?
Format for the "annotation" field: set "annotation" to an array containing one [x0, y0, x1, y1] pixel box around each counted object matching both the requested color and object type on the requested belt.
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[120,450,174,494],[390,320,450,370]],"answer":2}
```

### task_three_d__object_scene__image_plane_lateral_relation_count / answer_and_annotation / sample 7501840574571443

- `query_id`: `right_of_reference_in_view_count`
- `instance_seed`: `7501840574571443`
- `word_count`: `87`
- `body_word_count`: `39`

```text
The view shows a perspective 3D platform scene with many small objects and one red-boxed reference object. In the image, count the other small objects that appear to the right of the red-boxed reference object. How many are there?
Annotation format: set "annotation" to an array containing one bounding box [x0, y0, x1, y1] around each counted small object.
Answer format: set "answer" to the number of counted small objects.
Example JSON:
{"annotation":[[118,442,176,503],[391,316,448,374],[702,521,758,579]],"answer":3}
```

### task_three_d__street__same_road_arm_reference_label / answer_and_annotation / sample 4415929907906753

- `query_id`: `single`
- `instance_seed`: `4415929907906753`
- `word_count`: `86`
- `body_word_count`: `48`

```text
The image shows a perspective street intersection or T intersection with roads, sidewalks, crosswalk markings, street context, one red-boxed reference street object, candidate street objects, and a text option panel below the scene. Which option describes the object placed along the same road arm as the red-boxed object?
Annotation format: set "annotation" to the bounding box [x0, y0, x1, y1] around the selected street object in the scene.
Answer field: set "answer" to the selected option letter.
Example JSON:
{"annotation":[142,118,238,178],"answer":"C"}
```

### task_three_d__object_cluster__object_type_count_arithmetic / answer_and_annotation / sample 6247149652253919

- `query_id`: `difference_count`
- `instance_seed`: `6247149652253919`
- `word_count`: `85`
- `body_word_count`: `23`

```text
The image contains many small 3D objects arranged on a plain surface. What is the difference between the counts of diamonds and bottles?
Required annotation format: set "annotation" to an object with keys "left_operand" and "right_operand"; each value is an array of [x0, y0, x1, y1] pixel boxes around the objects in that operand group.
Required answer format: set "answer" to the count as an integer.
Example JSON:
{"annotation":{"left_operand":[[120,450,174,494],[390,320,450,370]],"right_operand":[[704,520,756,580]]},"answer":1}
```

### task_three_d__surface_fixture__scoped_colored_element_count / answer_and_annotation / sample 5113290182982696

- `query_id`: `row_scoped_color_count`
- `instance_seed`: `5113290182982696`
- `word_count`: `85`
- `body_word_count`: `29`

```text
The scene shows a fixture surface arranged in rows and columns with repeated colored surface elements. Count the orange [#EE881A] drawer pulls in row 1. How many are there?
Format for the "annotation" field: set "annotation" to an array containing one [x0, y0, x1, y1] pixel box around each counted colored surface element in the requested row or column.
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[120,450,174,494],[390,320,450,370]],"answer":2}
```

### task_three_d__carousel__scoped_color_type_count / answer_and_annotation / sample 4221448444823518

- `query_id`: `single`
- `instance_seed`: `4221448444823518`
- `word_count`: `83`
- `body_word_count`: `23`

```text
The visual shows small objects arranged on concentric inner and outer conveyor belts. How many cyan [#34C4E0] flowers are on the INNER belt?
Format for the "annotation" field: set "annotation" to an array containing one [x0, y0, x1, y1] pixel box around each counted object matching both the requested color and object type on the requested belt.
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[120,450,174,494],[390,320,450,370]],"answer":2}
```

## Repeated Scaffolding Terms

### task_three_d__surface_fixture__recolor_board_match_label / answer_and_annotation / sample 70590172597877

- `query_id`: `single`
- `instance_seed`: `70590172597877`
- `word_count`: `76`
- `body_word_count`: `35`
- `repeated_terms`: `{'board': 3}`

```text
Visible in the image is one original fixture board and four labeled candidate boards with visible lights. If every cyan [#34C4E0] light becomes maroon [#963644] on the original board, which labeled board shows the result?
Annotation format: set "annotation" to the [x0, y0, x1, y1] pixel box around the selected candidate board.
Answer field: set "answer" to the selected candidate board label as a single capital letter.
Example JSON:
{"annotation":[640,470,1050,720],"answer":"C"}
```

### task_three_d__surface_fixture__recolor_board_match_label / answer_only / sample 70590172597877

- `query_id`: `single`
- `instance_seed`: `70590172597877`
- `word_count`: `54`
- `body_word_count`: `35`
- `repeated_terms`: `{'board': 3}`

```text
Visible in the image is one original fixture board and four labeled candidate boards with visible lights. If every cyan [#34C4E0] light becomes maroon [#963644] on the original board, which labeled board shows the result?
Answer format: set "answer" to the selected candidate board label as a single capital letter.
Example JSON:
{"answer":"C"}
```

## All Prompt Samples

### task_three_d__carousel__belt_object_type_count_arithmetic_value / difference_count / answer_and_annotation / sample 4967323396516367

- `instance_seed`: `4967323396516367`
- `word_count`: `96`
- `body_word_count`: `34`

```text
A 3D conveyor carousel is shown with objects on the inner and outer belts. What is the difference between the number of plates on the INNER belt and the number on the OUTER belt?
Required annotation format: set "annotation" to an object with keys "inner_objects" and "outer_objects"; each value is an array of [x0, y0, x1, y1] boxes around the counted objects of the requested type for that belt.
Required answer format: set "answer" to the computed count as an integer.
Example JSON:
{"annotation":{"inner_objects":[[120,450,174,494]],"outer_objects":[[390,320,450,370]]},"answer":2}
```

### task_three_d__carousel__belt_object_type_count_arithmetic_value / difference_count / answer_only / sample 4967323396516367

- `instance_seed`: `4967323396516367`
- `word_count`: `50`
- `body_word_count`: `34`

```text
A 3D conveyor carousel is shown with objects on the inner and outer belts. What is the difference between the number of plates on the INNER belt and the number on the OUTER belt?
Required answer format: set "answer" to the computed count as an integer.
Example JSON:
{"answer":2}
```

### task_three_d__carousel__belt_object_type_count_arithmetic_value / total_count / answer_and_annotation / sample 445697350293333

- `instance_seed`: `445697350293333`
- `word_count`: `96`
- `body_word_count`: `36`

```text
The picture shows a baggage-style conveyor carousel with small objects on two oval belts. Add the count of apples on the INNER belt to the count of apples on the OUTER belt. What is the sum?
Annotation format: set "annotation" to an object with keys "inner_objects" and "outer_objects"; each value is an array of [x0, y0, x1, y1] boxes around the counted objects of the requested type for that belt.
Answer field: set "answer" to the computed count as an integer.
Example JSON:
{"annotation":{"inner_objects":[[120,450,174,494]],"outer_objects":[[390,320,450,370]]},"answer":2}
```

### task_three_d__carousel__belt_object_type_count_arithmetic_value / total_count / answer_only / sample 445697350293333

- `instance_seed`: `445697350293333`
- `word_count`: `51`
- `body_word_count`: `47`

```text
The picture shows a baggage-style conveyor carousel with small objects on two oval belts. Add the count of apples on the INNER belt to the count of apples on the OUTER belt. What is the sum?
Answer field: set "answer" to the computed count as an integer.
Example JSON:
{"answer":2}
```

### task_three_d__carousel__belt_total_object_count / single / answer_and_annotation / sample 158304622052658

- `instance_seed`: `158304622052658`
- `word_count`: `73`
- `body_word_count`: `27`

```text
The image shows a 3D airport-style conveyor carousel with an inner and an outer elliptical belt. Looking only at the OUTER belt, how many objects are visible?
Annotation format: set "annotation" to an array containing one [x0, y0, x1, y1] pixel box around each counted object on the requested belt.
Answer format: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[120,450,174,494],[390,320,450,370]],"answer":2}
```

### task_three_d__carousel__belt_total_object_count / single / answer_only / sample 158304622052658

- `instance_seed`: `158304622052658`
- `word_count`: `41`
- `body_word_count`: `27`

```text
The image shows a 3D airport-style conveyor carousel with an inner and an outer elliptical belt. Looking only at the OUTER belt, how many objects are visible?
Answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_three_d__carousel__between_object_type_anchors_count / single / answer_and_annotation / sample 6432946269138446

- `instance_seed`: `6432946269138446`
- `word_count`: `88`
- `body_word_count`: `35`

```text
The scene shows small 3D objects riding on two concentric elliptical conveyor belts. On the OUTER belt, following the belt arrows from marked object A to marked object B, how many objects are between them?
Annotation format: set "annotation" to an array containing one [x0, y0, x1, y1] pixel box around each counted object between the marked anchors; do not include the marked anchor objects.
Answer format: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[120,450,174,494],[390,320,450,370]],"answer":2}
```

### task_three_d__carousel__between_object_type_anchors_count / single / answer_only / sample 6432946269138446

- `instance_seed`: `6432946269138446`
- `word_count`: `50`
- `body_word_count`: `35`

```text
The scene shows small 3D objects riding on two concentric elliptical conveyor belts. On the OUTER belt, following the belt arrows from marked object A to marked object B, how many objects are between them?
Required answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_three_d__carousel__color_ordered_adjacent_pair_count / single / answer_and_annotation / sample 5274351976002687

- `instance_seed`: `5274351976002687`
- `word_count`: `113`
- `body_word_count`: `38`

```text
The picture shows a baggage-style conveyor carousel with small objects on two oval belts. Following the order of the INNER belt, count each green [#37B94B] object immediately followed by a red [#E63232] object. How many pairs are there?
Format for the "annotation" field: set "annotation" to an array containing one pixel-space segment [[x0, y0], [x1, y1]] per counted adjacent ordered pair, where each endpoint is an [x, y] pixel point at an object center; the segment starts at the first object and ends at the second object.
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[[120,450],[174,494]],[[390,320],[450,370]]],"answer":2}
```

### task_three_d__carousel__color_ordered_adjacent_pair_count / single / answer_only / sample 5274351976002687

- `instance_seed`: `5274351976002687`
- `word_count`: `52`
- `body_word_count`: `48`

```text
The picture shows a baggage-style conveyor carousel with small objects on two oval belts. Following the order of the INNER belt, count each green [#37B94B] object immediately followed by a red [#E63232] object. How many pairs are there?
Answer field: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_three_d__carousel__color_transfer_total_count / single / answer_and_annotation / sample 4261364338910370

- `instance_seed`: `4261364338910370`
- `word_count`: `99`
- `body_word_count`: `38`

```text
A 3D conveyor carousel is shown with objects on the inner and outer belts. Suppose all brown [#887044] objects on the INNER belt are moved to the OUTER belt. How many objects would be on the OUTER belt?
Final answer format: set "answer" to the resulting count as an integer.
Annotation format: set "annotation" to an object with keys "source_moved_objects" and "destination_existing_objects"; each value is an array of [x0, y0, x1, y1] boxes around the corresponding objects before the move.
Example JSON:
{"annotation":{"source_moved_objects":[[120,450,174,494]],"destination_existing_objects":[[390,320,450,370],[470,320,520,370]]},"answer":3}
```

### task_three_d__carousel__color_transfer_total_count / single / answer_only / sample 4261364338910370

- `instance_seed`: `4261364338910370`
- `word_count`: `53`
- `body_word_count`: `49`

```text
A 3D conveyor carousel is shown with objects on the inner and outer belts. Suppose all brown [#887044] objects on the INNER belt are moved to the OUTER belt. How many objects would be on the OUTER belt?
Answer field: set "answer" to the resulting count as an integer.
Example JSON:
{"answer":3}
```

### task_three_d__carousel__object_type_ordered_adjacent_pair_count / single / answer_and_annotation / sample 5284735579195479

- `instance_seed`: `5284735579195479`
- `word_count`: `102`
- `body_word_count`: `27`

```text
The scene shows small 3D objects riding on two concentric elliptical conveyor belts. Count the neighboring pairs on the OUTER belt where umbrellas come immediately before cones.
Format for the "annotation" field: set "annotation" to an array containing one pixel-space segment [[x0, y0], [x1, y1]] per counted adjacent ordered pair, where each endpoint is an [x, y] pixel point at an object center; the segment starts at the first object and ends at the second object.
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[[120,450],[174,494]],[[390,320],[450,370]]],"answer":2}
```

### task_three_d__carousel__object_type_ordered_adjacent_pair_count / single / answer_only / sample 5284735579195479

- `instance_seed`: `5284735579195479`
- `word_count`: `42`
- `body_word_count`: `27`

```text
The scene shows small 3D objects riding on two concentric elliptical conveyor belts. Count the neighboring pairs on the OUTER belt where umbrellas come immediately before cones.
Final answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_three_d__carousel__object_type_transfer_total_count / single / answer_and_annotation / sample 7263895744506266

- `instance_seed`: `7263895744506266`
- `word_count`: `95`
- `body_word_count`: `33`

```text
A 3D conveyor carousel is shown with objects on the inner and outer belts. What is the new total on the OUTER belt if all stars from the INNER belt are moved there?
Required annotation format: set "annotation" to an object with keys "source_moved_objects" and "destination_existing_objects"; each value is an array of [x0, y0, x1, y1] boxes around the corresponding objects before the move.
Required answer format: set "answer" to the resulting count as an integer.
Example JSON:
{"annotation":{"source_moved_objects":[[120,450,174,494]],"destination_existing_objects":[[390,320,450,370],[470,320,520,370]]},"answer":3}
```

### task_three_d__carousel__object_type_transfer_total_count / single / answer_only / sample 7263895744506266

- `instance_seed`: `7263895744506266`
- `word_count`: `49`
- `body_word_count`: `33`

```text
A 3D conveyor carousel is shown with objects on the inner and outer belts. What is the new total on the OUTER belt if all stars from the INNER belt are moved there?
Final answer format: set "answer" to the resulting count as an integer.
Example JSON:
{"answer":3}
```

### task_three_d__carousel__scoped_belt_color_count / single / answer_and_annotation / sample 2993329952392021

- `instance_seed`: `2993329952392021`
- `word_count`: `72`
- `body_word_count`: `25`

```text
The visual shows small objects arranged on concentric inner and outer conveyor belts. What is the number of red [#E63232] objects on the INNER belt?
Annotation format: set "annotation" to an array containing one [x0, y0, x1, y1] pixel box around each counted colored object on the requested belt.
Answer field: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[120,450,174,494],[390,320,450,370]],"answer":2}
```

### task_three_d__carousel__scoped_belt_color_count / single / answer_only / sample 2993329952392021

- `instance_seed`: `2993329952392021`
- `word_count`: `42`
- `body_word_count`: `25`

```text
The visual shows small objects arranged on concentric inner and outer conveyor belts. What is the number of red [#E63232] objects on the INNER belt?
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_three_d__carousel__scoped_belt_object_type_count / single / answer_and_annotation / sample 7890460848795095

- `instance_seed`: `7890460848795095`
- `word_count`: `74`
- `body_word_count`: `22`

```text
The picture shows a baggage-style conveyor carousel with small objects on two oval belts. How many lanterns are on the INNER belt?
Format for the "annotation" field: set "annotation" to an array containing one [x0, y0, x1, y1] pixel box around each counted object on the requested belt.
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[120,450,174,494],[390,320,450,370]],"answer":2}
```

### task_three_d__carousel__scoped_belt_object_type_count / single / answer_only / sample 7890460848795095

- `instance_seed`: `7890460848795095`
- `word_count`: `36`
- `body_word_count`: `22`

```text
The picture shows a baggage-style conveyor carousel with small objects on two oval belts. How many lanterns are on the INNER belt?
Answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_three_d__carousel__scoped_color_type_count / single / answer_and_annotation / sample 4221448444823518

- `instance_seed`: `4221448444823518`
- `word_count`: `83`
- `body_word_count`: `23`

```text
The visual shows small objects arranged on concentric inner and outer conveyor belts. How many cyan [#34C4E0] flowers are on the INNER belt?
Format for the "annotation" field: set "annotation" to an array containing one [x0, y0, x1, y1] pixel box around each counted object matching both the requested color and object type on the requested belt.
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[120,450,174,494],[390,320,450,370]],"answer":2}
```

### task_three_d__carousel__scoped_color_type_count / single / answer_only / sample 4221448444823518

- `instance_seed`: `4221448444823518`
- `word_count`: `37`
- `body_word_count`: `23`

```text
The visual shows small objects arranged on concentric inner and outer conveyor belts. How many cyan [#34C4E0] flowers are on the INNER belt?
Answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_three_d__conveyor__belt_total_object_count / single / answer_and_annotation / sample 2738912503051374

- `instance_seed`: `2738912503051374`
- `word_count`: `72`
- `body_word_count`: `25`

```text
The image shows three straight parallel conveyor belts with small 3D objects on them. What is the total number of objects on the MIDDLE belt?
Final answer format: set "answer" to the count as an integer.
Annotation format: set "annotation" to an array containing one [x0, y0, x1, y1] pixel box around each counted object on the requested belt.
Example JSON:
{"annotation":[[120,450,174,494],[390,320,450,370]],"answer":2}
```

### task_three_d__conveyor__belt_total_object_count / single / answer_only / sample 2738912503051374

- `instance_seed`: `2738912503051374`
- `word_count`: `40`
- `body_word_count`: `25`

```text
The image shows three straight parallel conveyor belts with small 3D objects on them. What is the total number of objects on the MIDDLE belt?
Final answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_three_d__conveyor__between_object_type_anchors_count / single / answer_and_annotation / sample 5165424042754202

- `instance_seed`: `5165424042754202`
- `word_count`: `87`
- `body_word_count`: `33`

```text
The visual shows a three-lane conveyor with small objects on each lane. Looking only at the TOP belt, how many objects lie between the marked flower A and the marked puzzle piece B?
Final answer format: set "answer" to the count as an integer.
Annotation format: set "annotation" to an array containing one [x0, y0, x1, y1] pixel box around each counted object between the marked anchors; do not include the marked anchor objects.
Example JSON:
{"annotation":[[120,450,174,494],[390,320,450,370]],"answer":2}
```

### task_three_d__conveyor__between_object_type_anchors_count / single / answer_only / sample 5165424042754202

- `instance_seed`: `5165424042754202`
- `word_count`: `50`
- `body_word_count`: `33`

```text
The visual shows a three-lane conveyor with small objects on each lane. Looking only at the TOP belt, how many objects lie between the marked flower A and the marked puzzle piece B?
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_three_d__conveyor__color_ordered_adjacent_pair_count / single / answer_and_annotation / sample 2855360547259200

- `instance_seed`: `2855360547259200`
- `word_count`: `107`
- `body_word_count`: `37`

```text
The picture shows three separate straight conveyor belts with objects on the belts. Following the order of the BOTTOM belt, count each magenta [#D02C91] object immediately followed by a yellow [#D4C21E] object. How many pairs are there?
Final answer format: set "answer" to the count as an integer.
Annotation format: set "annotation" to an array containing one pixel-space segment [[x0, y0], [x1, y1]] per counted adjacent ordered pair, where each endpoint is an [x, y] pixel point at an object center; the segment starts at the first object and ends at the second object.
Example JSON:
{"annotation":[[[120,450],[174,494]],[[390,320],[450,370]]],"answer":2}
```

### task_three_d__conveyor__color_ordered_adjacent_pair_count / single / answer_only / sample 2855360547259200

- `instance_seed`: `2855360547259200`
- `word_count`: `52`
- `body_word_count`: `37`

```text
The picture shows three separate straight conveyor belts with objects on the belts. Following the order of the BOTTOM belt, count each magenta [#D02C91] object immediately followed by a yellow [#D4C21E] object. How many pairs are there?
Required answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_three_d__conveyor__color_transfer_total_count / single / answer_and_annotation / sample 7274900670379643

- `instance_seed`: `7274900670379643`
- `word_count`: `95`
- `body_word_count`: `34`

```text
The scene shows small 3D objects arranged on three straight conveyor lanes. After transferring the blue [#2D75E6] objects on the MIDDLE belt to the RIGHT belt, how many objects would the RIGHT belt have?
Final answer format: set "answer" to the resulting count as an integer.
Annotation format: set "annotation" to an object with keys "source_moved_objects" and "destination_existing_objects"; each value is an array of [x0, y0, x1, y1] boxes around the corresponding objects before the move.
Example JSON:
{"annotation":{"source_moved_objects":[[120,450,174,494]],"destination_existing_objects":[[390,320,450,370],[470,320,520,370]]},"answer":3}
```

### task_three_d__conveyor__color_transfer_total_count / single / answer_only / sample 7274900670379643

- `instance_seed`: `7274900670379643`
- `word_count`: `50`
- `body_word_count`: `34`

```text
The scene shows small 3D objects arranged on three straight conveyor lanes. After transferring the blue [#2D75E6] objects on the MIDDLE belt to the RIGHT belt, how many objects would the RIGHT belt have?
Required answer format: set "answer" to the resulting count as an integer.
Example JSON:
{"answer":3}
```

### task_three_d__conveyor__lane_object_type_count_arithmetic_value / difference_count / answer_and_annotation / sample 4124190879239878

- `instance_seed`: `4124190879239878`
- `word_count`: `104`
- `body_word_count`: `33`

```text
The visual shows a three-lane conveyor with small objects on each lane. What is the difference between the number of chess pieces on the LEFT belt and the number on the RIGHT belt?
Annotation format: set "annotation" to an object with one key for each requested lane, named by lane position such as "top_objects" or "left_objects"; each value is an array of [x0, y0, x1, y1] boxes around the counted objects of the requested type for that lane.
Answer field: set "answer" to the computed count as an integer.
Example JSON:
{"annotation":{"top_objects":[[120,450,174,494]],"middle_objects":[[390,320,450,370]]},"answer":2}
```

### task_three_d__conveyor__lane_object_type_count_arithmetic_value / difference_count / answer_only / sample 4124190879239878

- `instance_seed`: `4124190879239878`
- `word_count`: `49`
- `body_word_count`: `33`

```text
The visual shows a three-lane conveyor with small objects on each lane. What is the difference between the number of chess pieces on the LEFT belt and the number on the RIGHT belt?
Required answer format: set "answer" to the computed count as an integer.
Example JSON:
{"answer":2}
```

### task_three_d__conveyor__lane_object_type_count_arithmetic_value / total_count / answer_and_annotation / sample 4612491792315183

- `instance_seed`: `4612491792315183`
- `word_count`: `107`
- `body_word_count`: `34`

```text
The picture shows three separate straight conveyor belts with objects on the belts. Count the balls on the LEFT belt and on the RIGHT belt, then add the two counts. What is the result?
Required annotation format: set "annotation" to an object with one key for each requested lane, named by lane position such as "top_objects" or "left_objects"; each value is an array of [x0, y0, x1, y1] boxes around the counted objects of the requested type for that lane.
Required answer format: set "answer" to the computed count as an integer.
Example JSON:
{"annotation":{"top_objects":[[120,450,174,494]],"middle_objects":[[390,320,450,370]]},"answer":2}
```

### task_three_d__conveyor__lane_object_type_count_arithmetic_value / total_count / answer_only / sample 4612491792315183

- `instance_seed`: `4612491792315183`
- `word_count`: `49`
- `body_word_count`: `45`

```text
The picture shows three separate straight conveyor belts with objects on the belts. Count the balls on the LEFT belt and on the RIGHT belt, then add the two counts. What is the result?
Answer field: set "answer" to the computed count as an integer.
Example JSON:
{"answer":2}
```

### task_three_d__conveyor__object_type_ordered_adjacent_pair_count / single / answer_and_annotation / sample 2460183435017049

- `instance_seed`: `2460183435017049`
- `word_count`: `98`
- `body_word_count`: `28`

```text
The picture shows three separate straight conveyor belts with objects on the belts. How many adjacent ordered pairs on the TOP belt go from chess pieces to hats?
Final answer format: set "answer" to the count as an integer.
Annotation format: set "annotation" to an array containing one pixel-space segment [[x0, y0], [x1, y1]] per counted adjacent ordered pair, where each endpoint is an [x, y] pixel point at an object center; the segment starts at the first object and ends at the second object.
Example JSON:
{"annotation":[[[120,450],[174,494]],[[390,320],[450,370]]],"answer":2}
```

### task_three_d__conveyor__object_type_ordered_adjacent_pair_count / single / answer_only / sample 2460183435017049

- `instance_seed`: `2460183435017049`
- `word_count`: `43`
- `body_word_count`: `28`

```text
The picture shows three separate straight conveyor belts with objects on the belts. How many adjacent ordered pairs on the TOP belt go from chess pieces to hats?
Required answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_three_d__conveyor__object_type_transfer_total_count / single / answer_and_annotation / sample 7140846889444957

- `instance_seed`: `7140846889444957`
- `word_count`: `101`
- `body_word_count`: `35`

```text
The image shows three straight parallel conveyor belts with small 3D objects on them. After transferring the puzzle pieces on the RIGHT belt to the LEFT belt, how many objects would the LEFT belt have?
Format for the "annotation" field: set "annotation" to an object with keys "source_moved_objects" and "destination_existing_objects"; each value is an array of [x0, y0, x1, y1] boxes around the corresponding objects before the move.
Format for the "answer" field: set "answer" to the resulting count as an integer.
Example JSON:
{"annotation":{"source_moved_objects":[[120,450,174,494]],"destination_existing_objects":[[390,320,450,370],[470,320,520,370]]},"answer":3}
```

### task_three_d__conveyor__object_type_transfer_total_count / single / answer_only / sample 7140846889444957

- `instance_seed`: `7140846889444957`
- `word_count`: `53`
- `body_word_count`: `35`

```text
The image shows three straight parallel conveyor belts with small 3D objects on them. After transferring the puzzle pieces on the RIGHT belt to the LEFT belt, how many objects would the LEFT belt have?
Format for the "answer" field: set "answer" to the resulting count as an integer.
Example JSON:
{"answer":3}
```

### task_three_d__conveyor__scoped_belt_color_count / single / answer_and_annotation / sample 4810802966114128

- `instance_seed`: `4810802966114128`
- `word_count`: `72`
- `body_word_count`: `24`

```text
The visual shows a three-lane conveyor with small objects on each lane. What is the number of green [#37B94B] objects on the LEFT belt?
Final answer format: set "answer" to the count as an integer.
Annotation format: set "annotation" to an array containing one [x0, y0, x1, y1] pixel box around each counted colored object on the requested belt.
Example JSON:
{"annotation":[[120,450,174,494],[390,320,450,370]],"answer":2}
```

### task_three_d__conveyor__scoped_belt_color_count / single / answer_only / sample 4810802966114128

- `instance_seed`: `4810802966114128`
- `word_count`: `39`
- `body_word_count`: `24`

```text
The visual shows a three-lane conveyor with small objects on each lane. What is the number of green [#37B94B] objects on the LEFT belt?
Final answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_three_d__conveyor__scoped_belt_object_type_count / single / answer_and_annotation / sample 7048325324857038

- `instance_seed`: `7048325324857038`
- `word_count`: `74`
- `body_word_count`: `22`

```text
The visual shows a three-lane conveyor with small objects on each lane. What is the number of flowers on the TOP belt?
Format for the "annotation" field: set "annotation" to an array containing one [x0, y0, x1, y1] pixel box around each counted object on the requested belt.
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[120,450,174,494],[390,320,450,370]],"answer":2}
```

### task_three_d__conveyor__scoped_belt_object_type_count / single / answer_only / sample 7048325324857038

- `instance_seed`: `7048325324857038`
- `word_count`: `36`
- `body_word_count`: `32`

```text
The visual shows a three-lane conveyor with small objects on each lane. What is the number of flowers on the TOP belt?
Answer field: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_three_d__conveyor__scoped_color_type_count / single / answer_and_annotation / sample 2503222502801942

- `instance_seed`: `2503222502801942`
- `word_count`: `87`
- `body_word_count`: `27`

```text
The image shows three straight parallel conveyor belts with small 3D objects on them. Looking only at the TOP belt, how many cyan [#34C4E0] stars are visible?
Format for the "annotation" field: set "annotation" to an array containing one [x0, y0, x1, y1] pixel box around each counted object matching both the requested color and object type on the requested belt.
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[120,450,174,494],[390,320,450,370]],"answer":2}
```

### task_three_d__conveyor__scoped_color_type_count / single / answer_only / sample 2503222502801942

- `instance_seed`: `2503222502801942`
- `word_count`: `42`
- `body_word_count`: `27`

```text
The image shows three straight parallel conveyor belts with small 3D objects on them. Looking only at the TOP belt, how many cyan [#34C4E0] stars are visible?
Final answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_three_d__object_cluster__color_count_arithmetic / difference_count / answer_and_annotation / sample 4768817333180211

- `instance_seed`: `4768817333180211`
- `word_count`: `93`
- `body_word_count`: `33`

```text
The image contains many small 3D objects arranged on a plain surface. After subtracting the smaller count from the larger count for brown [#887044] objects and maroon [#963644] objects, what is the difference?
Annotation format: set "annotation" to an object with keys "left_operand" and "right_operand"; each value is an array of [x0, y0, x1, y1] pixel boxes around the objects in that operand group.
Answer field: set "answer" to the count as an integer.
Example JSON:
{"annotation":{"left_operand":[[120,450,174,494],[390,320,450,370]],"right_operand":[[704,520,756,580]]},"answer":1}
```

### task_three_d__object_cluster__color_count_arithmetic / difference_count / answer_only / sample 4768817333180211

- `instance_seed`: `4768817333180211`
- `word_count`: `48`
- `body_word_count`: `33`

```text
The image contains many small 3D objects arranged on a plain surface. After subtracting the smaller count from the larger count for brown [#887044] objects and maroon [#963644] objects, what is the difference?
Final answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":3}
```

### task_three_d__object_cluster__color_count_arithmetic / total_count / answer_and_annotation / sample 3938293536365319

- `instance_seed`: `3938293536365319`
- `word_count`: `89`
- `body_word_count`: `27`

```text
The image shows many small 3D objects arranged on a plain surface. Add the number of blue [#2D75E6] objects and magenta [#D02C91] objects. What is the total?
Required annotation format: set "annotation" to an object with keys "left_operand" and "right_operand"; each value is an array of [x0, y0, x1, y1] pixel boxes around the objects in that operand group.
Required answer format: set "answer" to the count as an integer.
Example JSON:
{"annotation":{"left_operand":[[120,450,174,494],[390,320,450,370]],"right_operand":[[704,520,756,580]]},"answer":1}
```

### task_three_d__object_cluster__color_count_arithmetic / total_count / answer_only / sample 3938293536365319

- `instance_seed`: `3938293536365319`
- `word_count`: `42`
- `body_word_count`: `27`

```text
The image shows many small 3D objects arranged on a plain surface. Add the number of blue [#2D75E6] objects and magenta [#D02C91] objects. What is the total?
Final answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":3}
```

### task_three_d__object_cluster__color_membership_count / single / answer_and_annotation / sample 6514519733050705

- `instance_seed`: `6514519733050705`
- `word_count`: `70`
- `body_word_count`: `22`

```text
The visible scene contains many small 3D objects arranged on a plain surface. How many brown [#887044] objects are in the cluster?
Required annotation format: set "annotation" to an array containing one [x0, y0, x1, y1] pixel box around each counted object.
Required answer format: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[120,450,174,494],[390,320,450,370],[704,520,756,580]],"answer":3}
```

### task_three_d__object_cluster__color_membership_count / single / answer_only / sample 6514519733050705

- `instance_seed`: `6514519733050705`
- `word_count`: `37`
- `body_word_count`: `22`

```text
The visible scene contains many small 3D objects arranged on a plain surface. How many brown [#887044] objects are in the cluster?
Required answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":3}
```

### task_three_d__object_cluster__counterfactual_count / single / answer_and_annotation / sample 7084808865690874

- `instance_seed`: `7084808865690874`
- `word_count`: `110`
- `body_word_count`: `50`

```text
The visible scene contains many small 3D objects arranged on a plain surface. Use the visible cluster as the starting set. Apply these edits:
1. Remove 1 purple [#963ACA] pencil.
2. Add 1 blue [#2D75E6] remote control.
3. Add 2 brown [#887044] pencils.
What is the final count of pencils?
Format for the "annotation" field: set "annotation" to an array containing one [x0, y0, x1, y1] pixel box around each starting visible object matching the queried property before the edits.
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[120,450,174,494],[390,320,450,370],[704,520,756,580]],"answer":5}
```

### task_three_d__object_cluster__counterfactual_count / single / answer_only / sample 7084808865690874

- `instance_seed`: `7084808865690874`
- `word_count`: `64`
- `body_word_count`: `60`

```text
The visible scene contains many small 3D objects arranged on a plain surface. Use the visible cluster as the starting set. Apply these edits:
1. Remove 1 purple [#963ACA] pencil.
2. Add 1 blue [#2D75E6] remote control.
3. Add 2 brown [#887044] pencils.
What is the final count of pencils?
Answer field: set "answer" to the count as an integer.
Example JSON:
{"answer":3}
```

### task_three_d__object_cluster__multi_attribute_and_count / single / answer_and_annotation / sample 3662188308203776

- `instance_seed`: `3662188308203776`
- `word_count`: `73`
- `body_word_count`: `25`

```text
The image contains many small 3D objects arranged on a plain surface. What is the total number of visible purple [#963ACA] plates in the cluster?
Required annotation format: set "annotation" to an array containing one [x0, y0, x1, y1] pixel box around each counted object.
Required answer format: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[120,450,174,494],[390,320,450,370],[704,520,756,580]],"answer":3}
```

### task_three_d__object_cluster__multi_attribute_and_count / single / answer_only / sample 3662188308203776

- `instance_seed`: `3662188308203776`
- `word_count`: `39`
- `body_word_count`: `25`

```text
The image contains many small 3D objects arranged on a plain surface. What is the total number of visible purple [#963ACA] plates in the cluster?
Answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":3}
```

### task_three_d__object_cluster__multi_attribute_exclusion_count / color_and_not_type_count / answer_and_annotation / sample 413488224596160

- `instance_seed`: `413488224596160`
- `word_count`: `69`
- `body_word_count`: `21`

```text
The visible scene contains many small 3D objects arranged on a plain surface. How many cyan [#34C4E0] objects are not hearts?
Required annotation format: set "annotation" to an array containing one [x0, y0, x1, y1] pixel box around each counted object.
Required answer format: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[120,450,174,494],[390,320,450,370],[704,520,756,580]],"answer":3}
```

### task_three_d__object_cluster__multi_attribute_exclusion_count / color_and_not_type_count / answer_only / sample 413488224596160

- `instance_seed`: `413488224596160`
- `word_count`: `36`
- `body_word_count`: `21`

```text
The visible scene contains many small 3D objects arranged on a plain surface. How many cyan [#34C4E0] objects are not hearts?
Required answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":3}
```

### task_three_d__object_cluster__multi_attribute_exclusion_count / type_and_not_color_count / answer_and_annotation / sample 5702719170382

- `instance_seed`: `5702719170382`
- `word_count`: `73`
- `body_word_count`: `27`

```text
The scene shows many small 3D objects arranged on a plain surface. What is the number of visible trays in the cluster that are not cyan [#34C4E0]?
Annotation format: set "annotation" to an array containing one [x0, y0, x1, y1] pixel box around each counted object.
Answer format: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[120,450,174,494],[390,320,450,370],[704,520,756,580]],"answer":3}
```

### task_three_d__object_cluster__multi_attribute_exclusion_count / type_and_not_color_count / answer_only / sample 5702719170382

- `instance_seed`: `5702719170382`
- `word_count`: `42`
- `body_word_count`: `27`

```text
The scene shows many small 3D objects arranged on a plain surface. What is the number of visible trays in the cluster that are not cyan [#34C4E0]?
Final answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":3}
```

### task_three_d__object_cluster__multi_attribute_or_count / single / answer_and_annotation / sample 7287759503855126

- `instance_seed`: `7287759503855126`
- `word_count`: `80`
- `body_word_count`: `28`

```text
The image shows many small 3D objects arranged on a plain surface. Count every clustered object that is a chair or is maroon [#963644]. How many are there?
Format for the "annotation" field: set "annotation" to an array containing one [x0, y0, x1, y1] pixel box around each counted object.
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[120,450,174,494],[390,320,450,370],[704,520,756,580]],"answer":3}
```

### task_three_d__object_cluster__multi_attribute_or_count / single / answer_only / sample 7287759503855126

- `instance_seed`: `7287759503855126`
- `word_count`: `42`
- `body_word_count`: `38`

```text
The image shows many small 3D objects arranged on a plain surface. Count every clustered object that is a chair or is maroon [#963644]. How many are there?
Answer field: set "answer" to the count as an integer.
Example JSON:
{"answer":3}
```

### task_three_d__object_cluster__multi_attribute_xor_count / single / answer_and_annotation / sample 4375300847520121

- `instance_seed`: `4375300847520121`
- `word_count`: `79`
- `body_word_count`: `31`

```text
The image shows many small 3D objects arranged on a plain surface. Count every clustered object that is a star or is blue [#2D75E6], but not both. How many are there?
Required annotation format: set "annotation" to an array containing one [x0, y0, x1, y1] pixel box around each counted object.
Required answer format: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[120,450,174,494],[390,320,450,370],[704,520,756,580]],"answer":3}
```

### task_three_d__object_cluster__multi_attribute_xor_count / single / answer_only / sample 4375300847520121

- `instance_seed`: `4375300847520121`
- `word_count`: `48`
- `body_word_count`: `31`

```text
The image shows many small 3D objects arranged on a plain surface. Count every clustered object that is a star or is blue [#2D75E6], but not both. How many are there?
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"answer":3}
```

### task_three_d__object_cluster__object_type_count / single / answer_and_annotation / sample 87996489199656

- `instance_seed`: `87996489199656`
- `word_count`: `71`
- `body_word_count`: `19`

```text
The image contains many small 3D objects arranged on a plain surface. How many bowls are in the cluster?
Format for the "annotation" field: set "annotation" to an array containing one [x0, y0, x1, y1] pixel box around each counted object.
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[120,450,174,494],[390,320,450,370],[704,520,756,580]],"answer":3}
```

### task_three_d__object_cluster__object_type_count / single / answer_only / sample 87996489199656

- `instance_seed`: `87996489199656`
- `word_count`: `34`
- `body_word_count`: `19`

```text
The image contains many small 3D objects arranged on a plain surface. How many bowls are in the cluster?
Required answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":3}
```

### task_three_d__object_cluster__object_type_count_arithmetic / difference_count / answer_and_annotation / sample 6247149652253919

- `instance_seed`: `6247149652253919`
- `word_count`: `85`
- `body_word_count`: `23`

```text
The image contains many small 3D objects arranged on a plain surface. What is the difference between the counts of diamonds and bottles?
Required annotation format: set "annotation" to an object with keys "left_operand" and "right_operand"; each value is an array of [x0, y0, x1, y1] pixel boxes around the objects in that operand group.
Required answer format: set "answer" to the count as an integer.
Example JSON:
{"annotation":{"left_operand":[[120,450,174,494],[390,320,450,370]],"right_operand":[[704,520,756,580]]},"answer":1}
```

### task_three_d__object_cluster__object_type_count_arithmetic / difference_count / answer_only / sample 6247149652253919

- `instance_seed`: `6247149652253919`
- `word_count`: `38`
- `body_word_count`: `23`

```text
The image contains many small 3D objects arranged on a plain surface. What is the difference between the counts of diamonds and bottles?
Required answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":3}
```

### task_three_d__object_cluster__object_type_count_arithmetic / total_count / answer_and_annotation / sample 3052723167074896

- `instance_seed`: `3052723167074896`
- `word_count`: `82`
- `body_word_count`: `21`

```text
The image contains many small 3D objects arranged on a plain surface. How many gloves and plates are there in total?
Final answer format: set "answer" to the count as an integer.
Annotation format: set "annotation" to an object with keys "left_operand" and "right_operand"; each value is an array of [x0, y0, x1, y1] pixel boxes around the objects in that operand group.
Example JSON:
{"annotation":{"left_operand":[[120,450,174,494],[390,320,450,370]],"right_operand":[[704,520,756,580]]},"answer":1}
```

### task_three_d__object_cluster__object_type_count_arithmetic / total_count / answer_only / sample 3052723167074896

- `instance_seed`: `3052723167074896`
- `word_count`: `38`
- `body_word_count`: `21`

```text
The image contains many small 3D objects arranged on a plain surface. How many gloves and plates are there in total?
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"answer":3}
```

### task_three_d__object_cluster__total_object_count / single / answer_and_annotation / sample 3393393507993222

- `instance_seed`: `3393393507993222`
- `word_count`: `72`
- `body_word_count`: `20`

```text
The image contains many small 3D objects arranged on a plain surface. What is the total number of visible objects?
Format for the "annotation" field: set "annotation" to an array containing one [x0, y0, x1, y1] pixel box around each counted object.
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[120,450,174,494],[390,320,450,370],[704,520,756,580]],"answer":3}
```

### task_three_d__object_cluster__total_object_count / single / answer_only / sample 3393393507993222

- `instance_seed`: `3393393507993222`
- `word_count`: `35`
- `body_word_count`: `20`

```text
The image contains many small 3D objects arranged on a plain surface. What is the total number of visible objects?
Final answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":3}
```

### task_three_d__object_scene__between_references_label / single / answer_and_annotation / sample 3213403754065541

- `instance_seed`: `3213403754065541`
- `word_count`: `65`
- `body_word_count`: `28`

```text
The image presents a perspective 3D platform scene with several objects and two reference objects. Which option describes the object positioned between the vending machine and the arch?
Annotation format: set "annotation" to the bounding box [x0, y0, x1, y1] around the selected object in the scene.
Answer format: set "answer" to the selected option letter.
Example JSON:
{"annotation":[318,260,366,308],"answer":"C"}
```

### task_three_d__object_scene__between_references_label / single / answer_only / sample 3213403754065541

- `instance_seed`: `3213403754065541`
- `word_count`: `44`
- `body_word_count`: `28`

```text
The image presents a perspective 3D platform scene with several objects and two reference objects. Which option describes the object positioned between the vending machine and the arch?
Format for the "answer" field: set "answer" to the selected option letter.
Example JSON:
{"answer":"C"}
```

### task_three_d__object_scene__camera_depth_relation_count / closer_to_camera_than_reference_count / answer_and_annotation / sample 6035339122497743

- `instance_seed`: `6035339122497743`
- `word_count`: `80`
- `body_word_count`: `32`

```text
The view shows a perspective 3D platform scene with many small objects and one red-boxed reference object. How many other small objects are closer to the camera than the red-boxed reference object?
Annotation format: set "annotation" to an array containing one bounding box [x0, y0, x1, y1] around each counted small object.
Answer field: set "answer" to the number of counted small objects.
Example JSON:
{"annotation":[[118,442,176,503],[391,316,448,374],[702,521,758,579]],"answer":3}
```

### task_three_d__object_scene__camera_depth_relation_count / closer_to_camera_than_reference_count / answer_only / sample 6035339122497743

- `instance_seed`: `6035339122497743`
- `word_count`: `47`
- `body_word_count`: `43`

```text
The view shows a perspective 3D platform scene with many small objects and one red-boxed reference object. How many other small objects are closer to the camera than the red-boxed reference object?
Answer field: set "answer" to the number of counted small objects.
Example JSON:
{"answer":3}
```

### task_three_d__object_scene__camera_depth_relation_count / farther_from_camera_than_reference_count / answer_and_annotation / sample 6788733993498159

- `instance_seed`: `6788733993498159`
- `word_count`: `82`
- `body_word_count`: `34`

```text
The image presents a perspective 3D platform scene with many small objects and one red-boxed reference object. From this camera view, how many other small objects are farther away than the red-boxed reference object?
Annotation format: set "annotation" to an array containing one bounding box [x0, y0, x1, y1] around each counted small object.
Answer format: set "answer" to the number of counted small objects.
Example JSON:
{"annotation":[[118,442,176,503],[391,316,448,374],[702,521,758,579]],"answer":3}
```

### task_three_d__object_scene__camera_depth_relation_count / farther_from_camera_than_reference_count / answer_only / sample 6788733993498159

- `instance_seed`: `6788733993498159`
- `word_count`: `50`
- `body_word_count`: `34`

```text
The image presents a perspective 3D platform scene with many small objects and one red-boxed reference object. From this camera view, how many other small objects are farther away than the red-boxed reference object?
Final answer format: set "answer" to the number of counted small objects.
Example JSON:
{"answer":3}
```

### task_three_d__object_scene__camera_distance_extremum_label / closest_to_camera / answer_and_annotation / sample 1568189727750431

- `instance_seed`: `1568189727750431`
- `word_count`: `64`
- `body_word_count`: `26`

```text
The view shows a perspective 3D platform scene with several small objects and larger props. From the camera view, which option describes the nearest small object?
Annotation format: set "annotation" to the [x0, y0, x1, y1] bounding box around the selected small object in the scene.
Answer format: set "answer" to the selected option letter.
Example JSON:
{"annotation":[318,260,366,308],"answer":"C"}
```

### task_three_d__object_scene__camera_distance_extremum_label / closest_to_camera / answer_only / sample 1568189727750431

- `instance_seed`: `1568189727750431`
- `word_count`: `42`
- `body_word_count`: `26`

```text
The view shows a perspective 3D platform scene with several small objects and larger props. From the camera view, which option describes the nearest small object?
Format for the "answer" field: set "answer" to the selected option letter.
Example JSON:
{"answer":"C"}
```

### task_three_d__object_scene__camera_distance_extremum_label / farthest_from_camera / answer_and_annotation / sample 1304771374425269

- `instance_seed`: `1304771374425269`
- `word_count`: `64`
- `body_word_count`: `26`

```text
The image shows a perspective 3D platform scene with several small objects and larger props. Which option describes the small 3D object farthest from the camera?
Annotation format: set "annotation" to the [x0, y0, x1, y1] bounding box around the selected small object in the scene.
Answer format: set "answer" to the selected option letter.
Example JSON:
{"annotation":[318,260,366,308],"answer":"C"}
```

### task_three_d__object_scene__camera_distance_extremum_label / farthest_from_camera / answer_only / sample 1304771374425269

- `instance_seed`: `1304771374425269`
- `word_count`: `39`
- `body_word_count`: `35`

```text
The image shows a perspective 3D platform scene with several small objects and larger props. Which option describes the small 3D object farthest from the camera?
Answer field: set "answer" to the selected option letter.
Example JSON:
{"answer":"C"}
```

### task_three_d__object_scene__height_extremum_label / highest_above_floor / answer_and_annotation / sample 6608238580100368

- `instance_seed`: `6608238580100368`
- `word_count`: `67`
- `body_word_count`: `30`

```text
The image shows a perspective 3D platform scene with objects placed at different heights. Using the 3D height cues, choose the listed option for the object highest above the floor.
Annotation format: set "annotation" to the bounding box [x0, y0, x1, y1] around the selected object in the scene.
Answer format: set "answer" to the selected option letter.
Example JSON:
{"annotation":[318,260,366,308],"answer":"C"}
```

### task_three_d__object_scene__height_extremum_label / highest_above_floor / answer_only / sample 6608238580100368

- `instance_seed`: `6608238580100368`
- `word_count`: `46`
- `body_word_count`: `30`

```text
The image shows a perspective 3D platform scene with objects placed at different heights. Using the 3D height cues, choose the listed option for the object highest above the floor.
Format for the "answer" field: set "answer" to the selected option letter.
Example JSON:
{"answer":"C"}
```

### task_three_d__object_scene__height_extremum_label / lowest_above_floor / answer_and_annotation / sample 6679870540415497

- `instance_seed`: `6679870540415497`
- `word_count`: `64`
- `body_word_count`: `26`

```text
The scene shows a perspective 3D platform scene with objects placed at different heights. Among the listed options, which object is sitting lowest above the floor?
Final answer format: set "answer" to the selected option letter.
Annotation format: set "annotation" to the bounding box [x0, y0, x1, y1] around the selected object in the scene.
Example JSON:
{"annotation":[318,260,366,308],"answer":"C"}
```

### task_three_d__object_scene__height_extremum_label / lowest_above_floor / answer_only / sample 6679870540415497

- `instance_seed`: `6679870540415497`
- `word_count`: `40`
- `body_word_count`: `26`

```text
The scene shows a perspective 3D platform scene with objects placed at different heights. Among the listed options, which object is sitting lowest above the floor?
Final answer format: set "answer" to the selected option letter.
Example JSON:
{"answer":"C"}
```

### task_three_d__object_scene__image_plane_lateral_relation_count / left_of_reference_in_view_count / answer_and_annotation / sample 1225252623419645

- `instance_seed`: `1225252623419645`
- `word_count`: `81`
- `body_word_count`: `33`

```text
The picture shows a perspective 3D platform scene with many small objects and one red-boxed reference object. How many small objects, excluding the red-boxed reference object, appear to its left in the image?
Annotation format: set "annotation" to an array containing one bounding box [x0, y0, x1, y1] around each counted small object.
Answer format: set "answer" to the number of counted small objects.
Example JSON:
{"annotation":[[118,442,176,503],[391,316,448,374],[702,521,758,579]],"answer":3}
```

### task_three_d__object_scene__image_plane_lateral_relation_count / left_of_reference_in_view_count / answer_only / sample 1225252623419645

- `instance_seed`: `1225252623419645`
- `word_count`: `49`
- `body_word_count`: `33`

```text
The picture shows a perspective 3D platform scene with many small objects and one red-boxed reference object. How many small objects, excluding the red-boxed reference object, appear to its left in the image?
Required answer format: set "answer" to the number of counted small objects.
Example JSON:
{"answer":3}
```

### task_three_d__object_scene__image_plane_lateral_relation_count / right_of_reference_in_view_count / answer_and_annotation / sample 7501840574571443

- `instance_seed`: `7501840574571443`
- `word_count`: `87`
- `body_word_count`: `39`

```text
The view shows a perspective 3D platform scene with many small objects and one red-boxed reference object. In the image, count the other small objects that appear to the right of the red-boxed reference object. How many are there?
Annotation format: set "annotation" to an array containing one bounding box [x0, y0, x1, y1] around each counted small object.
Answer format: set "answer" to the number of counted small objects.
Example JSON:
{"annotation":[[118,442,176,503],[391,316,448,374],[702,521,758,579]],"answer":3}
```

### task_three_d__object_scene__image_plane_lateral_relation_count / right_of_reference_in_view_count / answer_only / sample 7501840574571443

- `instance_seed`: `7501840574571443`
- `word_count`: `54`
- `body_word_count`: `39`

```text
The view shows a perspective 3D platform scene with many small objects and one red-boxed reference object. In the image, count the other small objects that appear to the right of the red-boxed reference object. How many are there?
Answer format: set "answer" to the number of counted small objects.
Example JSON:
{"answer":3}
```

### task_three_d__object_scene__line_side_label / left_of_directed_line / answer_and_annotation / sample 6191580946146410

- `instance_seed`: `6191580946146410`
- `word_count`: `67`
- `body_word_count`: `33`

```text
The image presents a perspective 3D platform scene with named objects and lettered point markers. Which marked point is on the left side of the line from the half cylinder to the pyramid?
Final answer format: set "answer" to the selected marked-point letter.
Annotation format: set "annotation" to the point [x, y] at the center of the selected point marker.
Example JSON:
{"annotation":[318,260],"answer":"C"}
```

### task_three_d__object_scene__line_side_label / left_of_directed_line / answer_only / sample 6191580946146410

- `instance_seed`: `6191580946146410`
- `word_count`: `46`
- `body_word_count`: `33`

```text
The image presents a perspective 3D platform scene with named objects and lettered point markers. Which marked point is on the left side of the line from the half cylinder to the pyramid?
Answer format: set "answer" to the selected marked-point letter.
Example JSON:
{"answer":"C"}
```

### task_three_d__object_scene__line_side_label / right_of_directed_line / answer_and_annotation / sample 1638774133820697

- `instance_seed`: `1638774133820697`
- `word_count`: `63`
- `body_word_count`: `30`

```text
The image presents a perspective 3D platform scene with named objects and lettered point markers. Choose the marked point right of the directed line from the bell to the diamond.
Annotation format: set "annotation" to the point [x, y] at the center of the selected point marker.
Answer format: set "answer" to the selected marked-point letter.
Example JSON:
{"annotation":[318,260],"answer":"C"}
```

### task_three_d__object_scene__line_side_label / right_of_directed_line / answer_only / sample 1638774133820697

- `instance_seed`: `1638774133820697`
- `word_count`: `44`
- `body_word_count`: `30`

```text
The image presents a perspective 3D platform scene with named objects and lettered point markers. Choose the marked point right of the directed line from the bell to the diamond.
Final answer format: set "answer" to the selected marked-point letter.
Example JSON:
{"answer":"C"}
```

### task_three_d__object_scene__marked_point_depth_extremum_label / closest_marked_point / answer_and_annotation / sample 6428240158615430

- `instance_seed`: `6428240158615430`
- `word_count`: `62`
- `body_word_count`: `28`

```text
The image presents a perspective 3D platform scene with objects and lettered floor point markers. Among the lettered floor point markers, which one is closest to the viewer?
Final answer format: set "answer" to the selected marked-point letter.
Annotation format: set "annotation" to the point [x, y] at the center of the selected point marker.
Example JSON:
{"annotation":[318,260],"answer":"C"}
```

### task_three_d__object_scene__marked_point_depth_extremum_label / closest_marked_point / answer_only / sample 6428240158615430

- `instance_seed`: `6428240158615430`
- `word_count`: `41`
- `body_word_count`: `37`

```text
The image presents a perspective 3D platform scene with objects and lettered floor point markers. Among the lettered floor point markers, which one is closest to the viewer?
Answer field: set "answer" to the selected marked-point letter.
Example JSON:
{"answer":"C"}
```

### task_three_d__object_scene__marked_point_depth_extremum_label / farthest_marked_point / answer_and_annotation / sample 5581217135570102

- `instance_seed`: `5581217135570102`
- `word_count`: `61`
- `body_word_count`: `28`

```text
The scene shows a perspective 3D platform scene with objects and lettered floor point markers. Among the lettered floor point markers, which one is farthest from the viewer?
Annotation format: set "annotation" to the point [x, y] at the center of the selected point marker.
Answer field: set "answer" to the selected marked-point letter.
Example JSON:
{"annotation":[318,260],"answer":"C"}
```

### task_three_d__object_scene__marked_point_depth_extremum_label / farthest_marked_point / answer_only / sample 5581217135570102

- `instance_seed`: `5581217135570102`
- `word_count`: `42`
- `body_word_count`: `28`

```text
The scene shows a perspective 3D platform scene with objects and lettered floor point markers. Among the lettered floor point markers, which one is farthest from the viewer?
Final answer format: set "answer" to the selected marked-point letter.
Example JSON:
{"answer":"C"}
```

### task_three_d__object_scene__marked_point_vertical_relation_label / single / answer_and_annotation / sample 4582175812976214

- `instance_seed`: `4582175812976214`
- `word_count`: `59`
- `body_word_count`: `26`

```text
The image shows a perspective 3D platform scene with small objects and lettered point markers. Which lettered point is directly above the cup in 3D space?
Annotation format: set "annotation" to the point [x, y] at the center of the selected point marker.
Answer format: set "answer" to the selected marked-point letter.
Example JSON:
{"annotation":[318,260],"answer":"C"}
```

### task_three_d__object_scene__marked_point_vertical_relation_label / single / answer_only / sample 4582175812976214

- `instance_seed`: `4582175812976214`
- `word_count`: `39`
- `body_word_count`: `26`

```text
The image shows a perspective 3D platform scene with small objects and lettered point markers. Which lettered point is directly above the cup in 3D space?
Answer format: set "answer" to the selected marked-point letter.
Example JSON:
{"answer":"C"}
```

### task_three_d__object_scene__multiview_object_match_label / single / answer_and_annotation / sample 196989311538457

- `instance_seed`: `196989311538457`
- `word_count`: `74`
- `body_word_count`: `31`

```text
The picture shows two side-by-side views of the same 3D setup. Which lettered object in the right view is the same physical object as the red-boxed object in the left view?
Annotation format: set "annotation" to the bounding box [x0, y0, x1, y1] around the matching lettered object in the right view.
Answer field: set "answer" to the selected object letter from the right view.
Example JSON:
{"annotation":[842,228,902,296],"answer":"C"}
```

### task_three_d__object_scene__multiview_object_match_label / single / answer_only / sample 196989311538457

- `instance_seed`: `196989311538457`
- `word_count`: `49`
- `body_word_count`: `31`

```text
The picture shows two side-by-side views of the same 3D setup. Which lettered object in the right view is the same physical object as the red-boxed object in the left view?
Required answer format: set "answer" to the selected object letter from the right view.
Example JSON:
{"answer":"C"}
```

### task_three_d__object_scene__object_relation_label / inside_prop / answer_and_annotation / sample 1370656678262104

- `instance_seed`: `1370656678262104`
- `word_count`: `62`
- `body_word_count`: `24`

```text
The image shows a perspective 3D platform scene with small objects and larger props. Which option describes the small object in the open box?
Annotation format: set "annotation" to the bounding box [x0, y0, x1, y1] around the selected small object in the scene.
Answer field: set "answer" to the selected option letter.
Example JSON:
{"annotation":[318,260,366,308],"answer":"C"}
```

### task_three_d__object_scene__object_relation_label / inside_prop / answer_only / sample 1370656678262104

- `instance_seed`: `1370656678262104`
- `word_count`: `38`
- `body_word_count`: `24`

```text
The image shows a perspective 3D platform scene with small objects and larger props. Which option describes the small object in the open box?
Required answer format: set "answer" to the selected option letter.
Example JSON:
{"answer":"C"}
```

### task_three_d__object_scene__object_relation_label / on_top_of_prop / answer_and_annotation / sample 6538848579113513

- `instance_seed`: `6538848579113513`
- `word_count`: `64`
- `body_word_count`: `26`

```text
The view shows a perspective 3D platform scene with small objects and larger props. Which option describes the small 3D object on top of the shelf?
Annotation format: set "annotation" to the bounding box [x0, y0, x1, y1] around the selected small object in the scene.
Answer format: set "answer" to the selected option letter.
Example JSON:
{"annotation":[318,260,366,308],"answer":"C"}
```

### task_three_d__object_scene__object_relation_label / on_top_of_prop / answer_only / sample 6538848579113513

- `instance_seed`: `6538848579113513`
- `word_count`: `39`
- `body_word_count`: `26`

```text
The view shows a perspective 3D platform scene with small objects and larger props. Which option describes the small 3D object on top of the shelf?
Answer format: set "answer" to the selected option letter.
Example JSON:
{"answer":"C"}
```

### task_three_d__object_scene__object_relation_label / under_prop / answer_and_annotation / sample 5653024963690914

- `instance_seed`: `5653024963690914`
- `word_count`: `63`
- `body_word_count`: `25`

```text
The picture shows a perspective 3D platform scene with small objects and larger props. Find the small object below the table and choose its option.
Annotation format: set "annotation" to the bounding box [x0, y0, x1, y1] around the selected small object in the scene.
Answer format: set "answer" to the selected option letter.
Example JSON:
{"annotation":[318,260,366,308],"answer":"C"}
```

### task_three_d__object_scene__object_relation_label / under_prop / answer_only / sample 5653024963690914

- `instance_seed`: `5653024963690914`
- `word_count`: `41`
- `body_word_count`: `25`

```text
The picture shows a perspective 3D platform scene with small objects and larger props. Find the small object below the table and choose its option.
Format for the "answer" field: set "answer" to the selected option letter.
Example JSON:
{"answer":"C"}
```

### task_three_d__object_scene__occlusion_order_label / single / answer_and_annotation / sample 6715748115180174

- `instance_seed`: `6715748115180174`
- `word_count`: `60`
- `body_word_count`: `23`

```text
The image presents a perspective 3D scene with a rectangular platform and several small objects. Which object covers part of the rectangular platform?
Annotation format: set "annotation" to the bounding box [x0, y0, x1, y1] around the selected object in the scene.
Answer format: set "answer" to the selected option letter.
Example JSON:
{"annotation":[318,260,366,308],"answer":"C"}
```

### task_three_d__object_scene__occlusion_order_label / single / answer_only / sample 6715748115180174

- `instance_seed`: `6715748115180174`
- `word_count`: `39`
- `body_word_count`: `23`

```text
The image presents a perspective 3D scene with a rectangular platform and several small objects. Which object covers part of the rectangular platform?
Format for the "answer" field: set "answer" to the selected option letter.
Example JSON:
{"answer":"C"}
```

### task_three_d__object_scene__point_camera_distance_order_label / single / answer_and_annotation / sample 7055569441082500

- `instance_seed`: `7055569441082500`
- `word_count`: `68`
- `body_word_count`: `27`

```text
The image shows a perspective 3D platform scene with three marked floor points and an option panel. Which option gives the marked-point order from nearest to farthest?
Annotation format: set "annotation" to an object mapping P, Q, and R to their marked-point centers [x, y].
Answer format: set "answer" to the selected option letter.
Example JSON:
{"annotation":{"P":[318,260],"Q":[486,370],"R":[650,310]},"answer":"C"}
```

### task_three_d__object_scene__point_camera_distance_order_label / single / answer_only / sample 7055569441082500

- `instance_seed`: `7055569441082500`
- `word_count`: `41`
- `body_word_count`: `27`

```text
The image shows a perspective 3D platform scene with three marked floor points and an option panel. Which option gives the marked-point order from nearest to farthest?
Required answer format: set "answer" to the selected option letter.
Example JSON:
{"answer":"C"}
```

### task_three_d__object_scene__point_on_object_line_label / single / answer_and_annotation / sample 6503144850398437

- `instance_seed`: `6503144850398437`
- `word_count`: `62`
- `body_word_count`: `28`

```text
The scene shows a perspective 3D platform scene with named objects and lettered point markers. Find the marked point that lines up with the carrot and the clock.
Final answer format: set "answer" to the selected marked-point letter.
Annotation format: set "annotation" to the point [x, y] at the center of the selected point marker.
Example JSON:
{"annotation":[318,260],"answer":"C"}
```

### task_three_d__object_scene__point_on_object_line_label / single / answer_only / sample 6503144850398437

- `instance_seed`: `6503144850398437`
- `word_count`: `41`
- `body_word_count`: `37`

```text
The scene shows a perspective 3D platform scene with named objects and lettered point markers. Find the marked point that lines up with the carrot and the clock.
Answer field: set "answer" to the selected marked-point letter.
Example JSON:
{"answer":"C"}
```

### task_three_d__object_scene__reference_nearest_label / closest_to_reference / answer_and_annotation / sample 280026815556772

- `instance_seed`: `280026815556772`
- `word_count`: `58`
- `body_word_count`: `21`

```text
The image presents a large reference object and six smaller candidate objects. Which option describes the object closest to the piano?
Annotation format: set "annotation" to the bounding box [x0, y0, x1, y1] around the selected object in the scene.
Answer format: set "answer" to the selected option letter.
Example JSON:
{"annotation":[318,260,366,308],"answer":"C"}
```

### task_three_d__object_scene__reference_nearest_label / closest_to_reference / answer_only / sample 280026815556772

- `instance_seed`: `280026815556772`
- `word_count`: `34`
- `body_word_count`: `30`

```text
The image presents a large reference object and six smaller candidate objects. Which option describes the object closest to the piano?
Answer field: set "answer" to the selected option letter.
Example JSON:
{"answer":"C"}
```

### task_three_d__object_scene__reference_nearest_label / farthest_from_reference / answer_and_annotation / sample 7181181308672446

- `instance_seed`: `7181181308672446`
- `word_count`: `60`
- `body_word_count`: `23`

```text
The scene shows a large reference object and six smaller candidate objects. Looking at the bench, choose the option for the farthest object.
Annotation format: set "annotation" to the bounding box [x0, y0, x1, y1] around the selected object in the scene.
Answer format: set "answer" to the selected option letter.
Example JSON:
{"annotation":[318,260,366,308],"answer":"C"}
```

### task_three_d__object_scene__reference_nearest_label / farthest_from_reference / answer_only / sample 7181181308672446

- `instance_seed`: `7181181308672446`
- `word_count`: `37`
- `body_word_count`: `23`

```text
The scene shows a large reference object and six smaller candidate objects. Looking at the bench, choose the option for the farthest object.
Final answer format: set "answer" to the selected option letter.
Example JSON:
{"answer":"C"}
```

### task_three_d__object_scene__reference_triangle_inside_label / single / answer_and_annotation / sample 1997666066705806

- `instance_seed`: `1997666066705806`
- `word_count`: `65`
- `body_word_count`: `32`

```text
The view shows a perspective 3D platform scene with named objects and lettered point markers. Which marked point is inside the triangle formed by the envelope, the trophy, and the remote control?
Annotation format: set "annotation" to the point [x, y] at the center of the selected point marker.
Answer field: set "answer" to the selected marked-point letter.
Example JSON:
{"annotation":[318,260],"answer":"C"}
```

### task_three_d__object_scene__reference_triangle_inside_label / single / answer_only / sample 1997666066705806

- `instance_seed`: `1997666066705806`
- `word_count`: `45`
- `body_word_count`: `41`

```text
The view shows a perspective 3D platform scene with named objects and lettered point markers. Which marked point is inside the triangle formed by the envelope, the trophy, and the remote control?
Answer field: set "answer" to the selected marked-point letter.
Example JSON:
{"answer":"C"}
```

### task_three_d__room__wall_object_camera_distance_label / single / answer_and_annotation / sample 1832742170643889

- `instance_seed`: `1832742170643889`
- `word_count`: `64`
- `body_word_count`: `26`

```text
The image shows a perspective indoor room with floor, walls, furniture, room objects, and wall-mounted objects. Which option describes the wall object nearest to the camera?
Annotation format: set "annotation" to the bounding box [x0, y0, x1, y1] around the selected wall-mounted object in the scene.
Answer format: set "answer" to the selected option letter.
Example JSON:
{"annotation":[142,118,238,178],"answer":"C"}
```

### task_three_d__room__wall_object_camera_distance_label / single / answer_only / sample 1832742170643889

- `instance_seed`: `1832742170643889`
- `word_count`: `42`
- `body_word_count`: `26`

```text
The image shows a perspective indoor room with floor, walls, furniture, room objects, and wall-mounted objects. Which option describes the wall object nearest to the camera?
Format for the "answer" field: set "answer" to the selected option letter.
Example JSON:
{"answer":"C"}
```

### task_three_d__room__wall_object_same_wall_reference_label / single / answer_and_annotation / sample 5251884493719410

- `instance_seed`: `5251884493719410`
- `word_count`: `68`
- `body_word_count`: `30`

```text
The view shows a perspective indoor room with floor, walls, furniture, room objects, and wall-mounted objects. Choose the option for the wall-mounted object on the same wall as the mirror.
Annotation format: set "annotation" to the bounding box [x0, y0, x1, y1] around the selected wall-mounted object in the scene.
Answer format: set "answer" to the selected option letter.
Example JSON:
{"annotation":[142,118,238,178],"answer":"C"}
```

### task_three_d__room__wall_object_same_wall_reference_label / single / answer_only / sample 5251884493719410

- `instance_seed`: `5251884493719410`
- `word_count`: `43`
- `body_word_count`: `30`

```text
The view shows a perspective indoor room with floor, walls, furniture, room objects, and wall-mounted objects. Choose the option for the wall-mounted object on the same wall as the mirror.
Answer format: set "answer" to the selected option letter.
Example JSON:
{"answer":"C"}
```

### task_three_d__room__wall_object_side_relation_label / left_of_reference_on_wall / answer_and_annotation / sample 1464890657216942

- `instance_seed`: `1464890657216942`
- `word_count`: `74`
- `body_word_count`: `30`

```text
The scene shows a perspective indoor room with floor, walls, furniture, room objects, and wall-mounted objects. On the wall with the TV, which option describes the object to its left?
Format for the "annotation" field: set "annotation" to the bounding box [x0, y0, x1, y1] around the selected wall-mounted object in the scene.
Format for the "answer" field: set "answer" to the selected option letter.
Example JSON:
{"annotation":[142,118,238,178],"answer":"C"}
```

### task_three_d__room__wall_object_side_relation_label / left_of_reference_on_wall / answer_only / sample 1464890657216942

- `instance_seed`: `1464890657216942`
- `word_count`: `43`
- `body_word_count`: `39`

```text
The scene shows a perspective indoor room with floor, walls, furniture, room objects, and wall-mounted objects. On the wall with the TV, which option describes the object to its left?
Answer field: set "answer" to the selected option letter.
Example JSON:
{"answer":"C"}
```

### task_three_d__room__wall_object_side_relation_label / right_of_reference_on_wall / answer_and_annotation / sample 7701025298025215

- `instance_seed`: `7701025298025215`
- `word_count`: `69`
- `body_word_count`: `31`

```text
The image shows a perspective indoor room with floor, walls, furniture, room objects, and wall-mounted objects. Choose the option for the object to the right of the TV on that wall.
Annotation format: set "annotation" to the bounding box [x0, y0, x1, y1] around the selected wall-mounted object in the scene.
Answer format: set "answer" to the selected option letter.
Example JSON:
{"annotation":[142,118,238,178],"answer":"C"}
```

### task_three_d__room__wall_object_side_relation_label / right_of_reference_on_wall / answer_only / sample 7701025298025215

- `instance_seed`: `7701025298025215`
- `word_count`: `47`
- `body_word_count`: `31`

```text
The image shows a perspective indoor room with floor, walls, furniture, room objects, and wall-mounted objects. Choose the option for the object to the right of the TV on that wall.
Format for the "answer" field: set "answer" to the selected option letter.
Example JSON:
{"answer":"C"}
```

### task_three_d__street__intersection_nearest_label / single / answer_and_annotation / sample 2864450641959256

- `instance_seed`: `2864450641959256`
- `word_count`: `79`
- `body_word_count`: `39`

```text
The image presents a perspective street intersection or T intersection with roads, sidewalks, crosswalk markings, street context, candidate street objects, and a text option panel below the scene. Which option describes the object closest to where the roads meet?
Required annotation format: set "annotation" to the bounding box [x0, y0, x1, y1] around the selected street object in the scene.
Required answer format: set "answer" to the selected option letter.
Example JSON:
{"annotation":[142,118,238,178],"answer":"C"}
```

### task_three_d__street__intersection_nearest_label / single / answer_only / sample 2864450641959256

- `instance_seed`: `2864450641959256`
- `word_count`: `53`
- `body_word_count`: `39`

```text
The image presents a perspective street intersection or T intersection with roads, sidewalks, crosswalk markings, street context, candidate street objects, and a text option panel below the scene. Which option describes the object closest to where the roads meet?
Required answer format: set "answer" to the selected option letter.
Example JSON:
{"answer":"C"}
```

### task_three_d__street__lane_ahead_object_label / single / answer_and_annotation / sample 5906709959417880

- `instance_seed`: `5906709959417880`
- `word_count`: `95`
- `body_word_count`: `57`

```text
The scene shows a perspective street intersection or T intersection with roads, sidewalks, crosswalk markings, street context, one red-boxed reference street object with a red travel-direction arrow, candidate street objects, and a text option panel below the scene. Which option describes the object directly ahead of the red-boxed object along the lane indicated by the red arrow?
Annotation format: set "annotation" to the bounding box [x0, y0, x1, y1] around the selected street object in the scene.
Answer format: set "answer" to the selected option letter.
Example JSON:
{"annotation":[142,118,238,178],"answer":"C"}
```

### task_three_d__street__lane_ahead_object_label / single / answer_only / sample 5906709959417880

- `instance_seed`: `5906709959417880`
- `word_count`: `70`
- `body_word_count`: `66`

```text
The scene shows a perspective street intersection or T intersection with roads, sidewalks, crosswalk markings, street context, one red-boxed reference street object with a red travel-direction arrow, candidate street objects, and a text option panel below the scene. Which option describes the object directly ahead of the red-boxed object along the lane indicated by the red arrow?
Answer field: set "answer" to the selected option letter.
Example JSON:
{"answer":"C"}
```

### task_three_d__street__same_road_arm_reference_label / single / answer_and_annotation / sample 4415929907906753

- `instance_seed`: `4415929907906753`
- `word_count`: `86`
- `body_word_count`: `48`

```text
The image shows a perspective street intersection or T intersection with roads, sidewalks, crosswalk markings, street context, one red-boxed reference street object, candidate street objects, and a text option panel below the scene. Which option describes the object placed along the same road arm as the red-boxed object?
Annotation format: set "annotation" to the bounding box [x0, y0, x1, y1] around the selected street object in the scene.
Answer field: set "answer" to the selected option letter.
Example JSON:
{"annotation":[142,118,238,178],"answer":"C"}
```

### task_three_d__street__same_road_arm_reference_label / single / answer_only / sample 4415929907906753

- `instance_seed`: `4415929907906753`
- `word_count`: `62`
- `body_word_count`: `48`

```text
The image shows a perspective street intersection or T intersection with roads, sidewalks, crosswalk markings, street context, one red-boxed reference street object, candidate street objects, and a text option panel below the scene. Which option describes the object placed along the same road arm as the red-boxed object?
Required answer format: set "answer" to the selected option letter.
Example JSON:
{"answer":"C"}
```

### task_three_d__surface_fixture__color_count_after_operations_value / single / answer_and_annotation / sample 5792516825434595

- `instance_seed`: `5792516825434595`
- `word_count`: `107`
- `body_word_count`: `40`

```text
The scene shows a fixture surface with repeated colored surface elements. Suppose these changes happen: add 3 magenta [#D02C91] pavers; add 3 yellow [#D4C21E] pavers; remove 1 magenta [#D02C91] paver. How many yellow [#D4C21E] pavers are there after all changes?
Format for the "annotation" field: set "annotation" to an array containing one [x0, y0, x1, y1] pixel box around each original visible target-color element used as the starting count; do not mark hypothetical added elements.
Format for the "answer" field: set "answer" to the final count as an integer after applying the listed changes.
Example JSON:
{"annotation":[[120,450,174,494],[390,320,450,370]],"answer":5}
```

### task_three_d__surface_fixture__color_count_after_operations_value / single / answer_only / sample 5792516825434595

- `instance_seed`: `5792516825434595`
- `word_count`: `61`
- `body_word_count`: `40`

```text
The scene shows a fixture surface with repeated colored surface elements. Suppose these changes happen: add 3 magenta [#D02C91] pavers; add 3 yellow [#D4C21E] pavers; remove 1 magenta [#D02C91] paver. How many yellow [#D4C21E] pavers are there after all changes?
Required answer format: set "answer" to the final count as an integer after applying the listed changes.
Example JSON:
{"answer":5}
```

### task_three_d__surface_fixture__color_frequency_option_label / absent_color / answer_and_annotation / sample 2676132417303973

- `instance_seed`: `2676132417303973`
- `word_count`: `73`
- `body_word_count`: `31`

```text
Visible in the image is a fixture surface with colored sockets and six labeled text options naming colors. Which text option names a color with zero visible sockets on the fixture?
Final answer format: set "answer" to the selected option label as a single capital letter.
Annotation format: set "annotation" to the [x0, y0, x1, y1] pixel box around the selected text option card.
Example JSON:
{"annotation":[620,710,890,790],"answer":"D"}
```

### task_three_d__surface_fixture__color_frequency_option_label / absent_color / answer_only / sample 2676132417303973

- `instance_seed`: `2676132417303973`
- `word_count`: `49`
- `body_word_count`: `31`

```text
Visible in the image is a fixture surface with colored sockets and six labeled text options naming colors. Which text option names a color with zero visible sockets on the fixture?
Answer format: set "answer" to the selected option label as a single capital letter.
Example JSON:
{"answer":"D"}
```

### task_three_d__surface_fixture__color_frequency_option_label / most_frequent_color / answer_and_annotation / sample 4183176837608257

- `instance_seed`: `4183176837608257`
- `word_count`: `75`
- `body_word_count`: `32`

```text
The picture shows a fixture surface with colored solar panels and six labeled text options naming colors. What letter labels the option naming the color that appears most often on the fixture?
Required annotation format: set "annotation" to the [x0, y0, x1, y1] pixel box around the selected text option card.
Required answer format: set "answer" to the selected option label as a single capital letter.
Example JSON:
{"annotation":[620,710,890,790],"answer":"D"}
```

### task_three_d__surface_fixture__color_frequency_option_label / most_frequent_color / answer_only / sample 4183176837608257

- `instance_seed`: `4183176837608257`
- `word_count`: `50`
- `body_word_count`: `46`

```text
The picture shows a fixture surface with colored solar panels and six labeled text options naming colors. What letter labels the option naming the color that appears most often on the fixture?
Answer field: set "answer" to the selected option label as a single capital letter.
Example JSON:
{"answer":"D"}
```

### task_three_d__surface_fixture__colored_element_count / single / answer_and_annotation / sample 4454566623525421

- `instance_seed`: `4454566623525421`
- `word_count`: `65`
- `body_word_count`: `21`

```text
This perspective view shows a fixture surface with repeated colored surface elements. Count the yellow [#D4C21E] lockers. How many are there?
Annotation format: set "annotation" to an array containing one [x0, y0, x1, y1] pixel box around each counted colored surface element.
Answer format: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[120,450,174,494],[390,320,450,370]],"answer":2}
```

### task_three_d__surface_fixture__colored_element_count / single / answer_only / sample 4454566623525421

- `instance_seed`: `4454566623525421`
- `word_count`: `36`
- `body_word_count`: `21`

```text
This perspective view shows a fixture surface with repeated colored surface elements. Count the yellow [#D4C21E] lockers. How many are there?
Final answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_three_d__surface_fixture__element_count_extremum_label / highest_element_count / answer_and_annotation / sample 8500579916262187

- `instance_seed`: `8500579916262187`
- `word_count`: `67`
- `body_word_count`: `22`

```text
The picture shows four labeled fixture panels with visible slots. What letter labels the panel with the highest count of visible slots?
Format for the "annotation" field: set "annotation" to the [x0, y0, x1, y1] pixel box around the selected panel.
Format for the "answer" field: set "answer" to the selected panel label as a single capital letter.
Example JSON:
{"annotation":[80,90,520,410],"answer":"B"}
```

### task_three_d__surface_fixture__element_count_extremum_label / highest_element_count / answer_only / sample 8500579916262187

- `instance_seed`: `8500579916262187`
- `word_count`: `40`
- `body_word_count`: `36`

```text
The picture shows four labeled fixture panels with visible slots. What letter labels the panel with the highest count of visible slots?
Answer field: set "answer" to the selected panel label as a single capital letter.
Example JSON:
{"answer":"B"}
```

### task_three_d__surface_fixture__element_count_extremum_label / lowest_element_count / answer_and_annotation / sample 681025183630151

- `instance_seed`: `681025183630151`
- `word_count`: `64`
- `body_word_count`: `25`

```text
Visible in the image is four labeled fixture panels with visible screws. Among the four labeled panels, which one contains the smallest number of screws?
Annotation format: set "annotation" to the [x0, y0, x1, y1] pixel box around the selected panel.
Answer format: set "answer" to the selected panel label as a single capital letter.
Example JSON:
{"annotation":[80,90,520,410],"answer":"B"}
```

### task_three_d__surface_fixture__element_count_extremum_label / lowest_element_count / answer_only / sample 681025183630151

- `instance_seed`: `681025183630151`
- `word_count`: `46`
- `body_word_count`: `25`

```text
Visible in the image is four labeled fixture panels with visible screws. Among the four labeled panels, which one contains the smallest number of screws?
Format for the "answer" field: set "answer" to the selected panel label as a single capital letter.
Example JSON:
{"answer":"B"}
```

### task_three_d__surface_fixture__recolor_board_match_label / single / answer_and_annotation / sample 70590172597877

- `instance_seed`: `70590172597877`
- `word_count`: `76`
- `body_word_count`: `35`

```text
Visible in the image is one original fixture board and four labeled candidate boards with visible lights. If every cyan [#34C4E0] light becomes maroon [#963644] on the original board, which labeled board shows the result?
Annotation format: set "annotation" to the [x0, y0, x1, y1] pixel box around the selected candidate board.
Answer field: set "answer" to the selected candidate board label as a single capital letter.
Example JSON:
{"annotation":[640,470,1050,720],"answer":"C"}
```

### task_three_d__surface_fixture__recolor_board_match_label / single / answer_only / sample 70590172597877

- `instance_seed`: `70590172597877`
- `word_count`: `54`
- `body_word_count`: `35`

```text
Visible in the image is one original fixture board and four labeled candidate boards with visible lights. If every cyan [#34C4E0] light becomes maroon [#963644] on the original board, which labeled board shows the result?
Answer format: set "answer" to the selected candidate board label as a single capital letter.
Example JSON:
{"answer":"C"}
```

### task_three_d__surface_fixture__repeated_element_count / single / answer_and_annotation / sample 5365456359631350

- `instance_seed`: `5365456359631350`
- `word_count`: `69`
- `body_word_count`: `19`

```text
Visible in the image is a screw plate with visible screws. Count the visible screws. How many are there?
Required annotation format: set "annotation" to an array containing one [x0, y0, x1, y1] pixel box around each counted surface element.
Required answer format: set "answer" to the number of counted surface elements.
Example JSON:
{"annotation":[[120,450,174,494],[390,320,450,370],[704,520,756,580]],"answer":3}
```

### task_three_d__surface_fixture__repeated_element_count / single / answer_only / sample 5365456359631350

- `instance_seed`: `5365456359631350`
- `word_count`: `34`
- `body_word_count`: `30`

```text
Visible in the image is a screw plate with visible screws. Count the visible screws. How many are there?
Answer field: set "answer" to the number of counted surface elements.
Example JSON:
{"answer":3}
```

### task_three_d__surface_fixture__scoped_colored_element_count / column_scoped_color_count / answer_and_annotation / sample 1218155921514533

- `instance_seed`: `1218155921514533`
- `word_count`: `79`
- `body_word_count`: `27`

```text
The scene shows a fixture surface arranged in rows and columns with repeated colored surface elements. In column 5, what is the number of yellow [#D4C21E] lockers?
Required annotation format: set "annotation" to an array containing one [x0, y0, x1, y1] pixel box around each counted colored surface element in the requested row or column.
Required answer format: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[120,450,174,494],[390,320,450,370]],"answer":2}
```

### task_three_d__surface_fixture__scoped_colored_element_count / column_scoped_color_count / answer_only / sample 1218155921514533

- `instance_seed`: `1218155921514533`
- `word_count`: `42`
- `body_word_count`: `27`

```text
The scene shows a fixture surface arranged in rows and columns with repeated colored surface elements. In column 5, what is the number of yellow [#D4C21E] lockers?
Final answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_three_d__surface_fixture__scoped_colored_element_count / row_scoped_color_count / answer_and_annotation / sample 5113290182982696

- `instance_seed`: `5113290182982696`
- `word_count`: `85`
- `body_word_count`: `29`

```text
The scene shows a fixture surface arranged in rows and columns with repeated colored surface elements. Count the orange [#EE881A] drawer pulls in row 1. How many are there?
Format for the "annotation" field: set "annotation" to an array containing one [x0, y0, x1, y1] pixel box around each counted colored surface element in the requested row or column.
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[120,450,174,494],[390,320,450,370]],"answer":2}
```

### task_three_d__surface_fixture__scoped_colored_element_count / row_scoped_color_count / answer_only / sample 5113290182982696

- `instance_seed`: `5113290182982696`
- `word_count`: `44`
- `body_word_count`: `29`

```text
The scene shows a fixture surface arranged in rows and columns with repeated colored surface elements. Count the orange [#EE881A] drawer pulls in row 1. How many are there?
Required answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_three_d__warehouse__nearest_candidate_to_reference_label / closest_object_to_reference / answer_and_annotation / sample 6316089241083789

- `instance_seed`: `6316089241083789`
- `word_count`: `79`
- `body_word_count`: `41`

```text
The image presents a perspective warehouse aisle with shelf racks, warehouse equipment, one red sphere reference object, candidate warehouse objects, and a text option panel below the scene. Which option describes the object with the smallest distance to the red sphere?
Annotation format: set "annotation" to the bounding box [x0, y0, x1, y1] around the selected warehouse object in the scene.
Answer field: set "answer" to the selected option letter.
Example JSON:
{"annotation":[142,118,238,178],"answer":"C"}
```

### task_three_d__warehouse__nearest_candidate_to_reference_label / closest_object_to_reference / answer_only / sample 6316089241083789

- `instance_seed`: `6316089241083789`
- `word_count`: `55`
- `body_word_count`: `41`

```text
The image presents a perspective warehouse aisle with shelf racks, warehouse equipment, one red sphere reference object, candidate warehouse objects, and a text option panel below the scene. Which option describes the object with the smallest distance to the red sphere?
Required answer format: set "answer" to the selected option letter.
Example JSON:
{"answer":"C"}
```

### task_three_d__warehouse__nearest_candidate_to_reference_label / closest_object_to_robot / answer_and_annotation / sample 51941419892514

- `instance_seed`: `51941419892514`
- `word_count`: `77`
- `body_word_count`: `37`

```text
The picture shows a perspective warehouse aisle with shelf racks, warehouse equipment, one robot, candidate warehouse objects, and a text option panel below the scene. Among the candidate warehouse objects, which option is nearest to the robot?
Required annotation format: set "annotation" to the bounding box [x0, y0, x1, y1] around the selected warehouse object in the scene.
Required answer format: set "answer" to the selected option letter.
Example JSON:
{"annotation":[142,118,238,178],"answer":"C"}
```

### task_three_d__warehouse__nearest_candidate_to_reference_label / closest_object_to_robot / answer_only / sample 51941419892514

- `instance_seed`: `51941419892514`
- `word_count`: `51`
- `body_word_count`: `37`

```text
The picture shows a perspective warehouse aisle with shelf racks, warehouse equipment, one robot, candidate warehouse objects, and a text option panel below the scene. Among the candidate warehouse objects, which option is nearest to the robot?
Final answer format: set "answer" to the selected option letter.
Example JSON:
{"answer":"C"}
```

### task_three_d__warehouse__robot_forward_path_label / single / answer_and_annotation / sample 1165623228610942

- `instance_seed`: `1165623228610942`
- `word_count`: `82`
- `body_word_count`: `44`

```text
The picture shows a perspective warehouse aisle with shelf racks, warehouse equipment, one red-boxed robot with a red travel-direction arrow, candidate warehouse objects, and a text option panel below the scene. Choose the option for the first object in the red-boxed robot's forward path.
Annotation format: set "annotation" to the bounding box [x0, y0, x1, y1] around the selected warehouse object in the scene.
Answer field: set "answer" to the selected option letter.
Example JSON:
{"annotation":[142,118,238,178],"answer":"C"}
```

### task_three_d__warehouse__robot_forward_path_label / single / answer_only / sample 1165623228610942

- `instance_seed`: `1165623228610942`
- `word_count`: `58`
- `body_word_count`: `44`

```text
The picture shows a perspective warehouse aisle with shelf racks, warehouse equipment, one red-boxed robot with a red travel-direction arrow, candidate warehouse objects, and a text option panel below the scene. Choose the option for the first object in the red-boxed robot's forward path.
Final answer format: set "answer" to the selected option letter.
Example JSON:
{"answer":"C"}
```

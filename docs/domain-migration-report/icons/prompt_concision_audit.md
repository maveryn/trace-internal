# Prompt Concision Audit

- rendered prompts: `152`
- tasks covered: `40`
- observed query ids covered: `76`

## Variant Coverage

- tasks with incomplete query ids or generation errors: `0`

| task | expected_query_ids | collected_query_id_counts | generated | issues |
| --- | --- | --- | ---: | --- |
| task_icons__icon_cutout__partial_match_label | `single` | `{'single': 1}` | 2 | `` |
| task_icons__icon_field__most_frequent_type_count | `single` | `{'single': 1}` | 2 | `` |
| task_icons__icon_field__singleton_type_count | `single` | `{'single': 1}` | 2 | `` |
| task_icons__mirror_grid__mirror_symmetry_match_label | `single` | `{'single': 1}` | 2 | `` |
| task_icons__named_field__closer_to_reference_count | `single` | `{'single': 1}` | 2 | `` |
| task_icons__named_field__counterfactual_attribute_count | `single` | `{'single': 1}` | 2 | `` |
| task_icons__named_field__counterfactual_total_count | `single` | `{'single': 1}` | 2 | `` |
| task_icons__named_field__multi_attribute_and_count | `single` | `{'single': 1}` | 2 | `` |
| task_icons__named_field__multi_attribute_complement_count | `single` | `{'single': 1}` | 2 | `` |
| task_icons__named_field__multi_attribute_exclusion_count | `color_and_not_shape_count, shape_and_not_color_count` | `{'color_and_not_shape_count': 1, 'shape_and_not_color_count': 1}` | 2 | `` |
| task_icons__named_field__multi_attribute_or_count | `single` | `{'single': 1}` | 2 | `` |
| task_icons__named_field__multi_attribute_xor_count | `single` | `{'single': 1}` | 2 | `` |
| task_icons__named_field__reference_distance_rank_label | `closest_to_named_reference_label, farthest_from_named_reference_label, second_closest_to_named_reference_label` | `{'closest_to_named_reference_label': 1, 'farthest_from_named_reference_label': 1, 'second_closest_to_named_reference_label': 1}` | 3 | `` |
| task_icons__named_field__scoped_attribute_count | `inside_band_count, inside_quadrant_count, inside_shape_count, inside_shelf_count, outside_band_count, outside_shape_count` | `{'inside_band_count': 1, 'inside_quadrant_count': 1, 'inside_shape_count': 1, 'inside_shelf_count': 1, 'outside_band_count': 1, 'outside_shape_count': 1}` | 6 | `` |
| task_icons__named_field__single_attribute_membership_count | `single` | `{'single': 1}` | 2 | `` |
| task_icons__named_grid__group_predicate_count | `column_at_least_shape_count, column_exactly_shape_count, column_no_shape_count, row_at_least_shape_count, row_exactly_shape_count, row_no_shape_count` | `{'column_at_least_shape_count': 1, 'column_exactly_shape_count': 1, 'column_no_shape_count': 1, 'row_at_least_shape_count': 1, 'row_exactly_shape_count': 1, 'row_no_shape_count': 1}` | 6 | `` |
| task_icons__named_grid__row_column_shape_extreme_number | `column_fewest_shape_number, column_most_shape_number, row_fewest_shape_number, row_most_shape_number` | `{'column_fewest_shape_number': 1, 'column_most_shape_number': 1, 'row_fewest_shape_number': 1, 'row_most_shape_number': 1}` | 4 | `` |
| task_icons__named_grid__scoped_attribute_count | `column_shape_count, row_shape_count` | `{'column_shape_count': 1, 'row_shape_count': 1}` | 2 | `` |
| task_icons__named_path__path_neighbor_label | `after_first_shape_label, after_last_shape_label, after_second_shape_label, before_first_shape_label, before_last_shape_label, before_second_shape_label` | `{'after_first_shape_label': 1, 'after_last_shape_label': 1, 'after_second_shape_label': 1, 'before_first_shape_label': 1, 'before_last_shape_label': 1, 'before_second_shape_label': 1}` | 6 | `` |
| task_icons__named_ring__scoped_attribute_count | `clockwise_arc_shape_count, counterclockwise_arc_shape_count` | `{'clockwise_arc_shape_count': 1, 'counterclockwise_arc_shape_count': 1}` | 2 | `` |
| task_icons__named_strip__shape_run_length | `longest_shape_run_length, shortest_shape_run_length` | `{'longest_shape_run_length': 1, 'shortest_shape_run_length': 1}` | 2 | `` |
| task_icons__overlap_grid__occlusion_order_count | `single` | `{'single': 1}` | 2 | `` |
| task_icons__pair_grid__reference_color_pair_match_label | `single` | `{'single': 1}` | 2 | `` |
| task_icons__pair_grid__reference_transform_match_label | `single` | `{'single': 1}` | 2 | `` |
| task_icons__paired_canvas__color_change_count | `single` | `{'single': 1}` | 2 | `` |
| task_icons__paired_canvas__panel_set_relation_count | `added_in_right_count, missing_from_right_count` | `{'added_in_right_count': 1, 'missing_from_right_count': 1}` | 2 | `` |
| task_icons__paired_canvas__rotation_change_count | `single` | `{'single': 1}` | 2 | `` |
| task_icons__reference_canvas__anchor_position_count | `above_anchor, below_anchor, left_of_anchor, right_of_anchor` | `{'above_anchor': 1, 'below_anchor': 1, 'left_of_anchor': 1, 'right_of_anchor': 1}` | 4 | `` |
| task_icons__reference_canvas__reference_color_match_count | `single` | `{'single': 1}` | 2 | `` |
| task_icons__reference_canvas__reference_metric_relation_count | `size_larger, size_smaller` | `{'size_larger': 1, 'size_smaller': 1}` | 2 | `` |
| task_icons__reference_canvas__reference_rotation_match_count | `single` | `{'single': 1}` | 2 | `` |
| task_icons__reference_canvas__reference_type_color_rotation_match_count | `single` | `{'single': 1}` | 2 | `` |
| task_icons__reference_canvas__reference_type_match_count | `single` | `{'single': 1}` | 2 | `` |
| task_icons__sequence_strip__count_progression_completion_label | `single` | `{'single': 1}` | 2 | `` |
| task_icons__sequence_strip__rotation_progression_completion_label | `single` | `{'single': 1}` | 2 | `` |
| task_icons__sequence_strip__size_progression_completion_label | `single` | `{'single': 1}` | 2 | `` |
| task_icons__single_transform_options__geometric_transform_result_label | `flip_horizontal_result_label, flip_vertical_result_label, rotate_180_result_label, rotate_90_clockwise_result_label, rotate_90_counterclockwise_result_label` | `{'flip_horizontal_result_label': 1, 'flip_vertical_result_label': 1, 'rotate_180_result_label': 1, 'rotate_90_clockwise_result_label': 1, 'rotate_90_counterclockwise_result_label': 1}` | 5 | `` |
| task_icons__venn_field__scoped_attribute_count | `inside_both_circles_count, inside_either_circle_count, inside_exactly_one_circle_count, outside_both_circles_count` | `{'inside_both_circles_count': 1, 'inside_either_circle_count': 1, 'inside_exactly_one_circle_count': 1, 'outside_both_circles_count': 1}` | 4 | `` |
| task_icons__wallpaper_panels__motif_violation_label | `single` | `{'single': 1}` | 2 | `` |
| task_icons__wallpaper_panels__same_pattern_as_reference_label | `single` | `{'single': 1}` | 2 | `` |

## Longest Prompts

### task_icons__named_ring__scoped_attribute_count / answer_and_annotation / sample 4525877990387976

- `query_id`: `clockwise_arc_shape_count`
- `instance_seed`: `4525877990387976`
- `word_count`: `90`
- `body_word_count`: `33`

```text
The picture shows a ring of icons with endpoint markers A and B. Starting at marker A and moving clockwise to marker B, how many "triangle" icons are strictly between A and B?
Final answer format: set "answer" to the count as an integer.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every counted "triangle" icon strictly between A and B along the clockwise arc.
Example JSON:
{"annotation":[[176,168,236,228],[384,298,444,358]],"answer":2}
```

### task_icons__named_ring__scoped_attribute_count / answer_and_annotation / sample 6869640320475465

- `query_id`: `counterclockwise_arc_shape_count`
- `instance_seed`: `6869640320475465`
- `word_count`: `89`
- `body_word_count`: `33`

```text
The picture shows a ring of icons with endpoint markers A and B. Starting at marker A and moving counterclockwise to marker B, how many "car" icons are strictly between A and B?
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every counted "car" icon strictly between A and B along the counterclockwise arc.
Answer field: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[176,168,236,228],[384,298,444,358]],"answer":2}
```

### task_icons__named_field__reference_distance_rank_label / answer_and_annotation / sample 3530764205146963

- `query_id`: `farthest_from_named_reference_label`
- `instance_seed`: `3530764205146963`
- `word_count`: `85`
- `body_word_count`: `28`

```text
The figure shows a panel with one reference icon, six option icons labeled A-F, and other icons. Which labeled icon is farthest from the green [#37B94B] "lightbulb" icon?
Annotation format: set "annotation" to a JSON object with keys "reference_icon" and "selected_candidate", each mapped to an [x0, y0, x1, y1] bounding box in image pixel coordinates.
Format for the "answer" field: set "answer" to the selected option letter as a string.
Example JSON:
{"annotation":{"reference_icon":[178,244,238,304],"selected_candidate":[614,186,674,246]},"answer":"D"}
```

### task_icons__sequence_strip__count_progression_completion_label / answer_and_annotation / sample 2377184592106086

- `query_id`: `single`
- `instance_seed`: `2377184592106086`
- `word_count`: `84`
- `body_word_count`: `34`

```text
The picture shows a top row of four boxed sequence cells with one question-mark box and a bottom row of four labeled option boxes. Which option completes the icon-count sequence in the question-mark box?
Required annotation format: set "annotation" to one [x0, y0, x1, y1] box in image pixel coordinates for the correct option box.
Required answer format: set "answer" to the correct option label as a string, one of "A", "B", "C", or "D".
Example JSON:
{"annotation":[412,250,540,398],"answer":"C"}
```

### task_icons__sequence_strip__rotation_progression_completion_label / answer_and_annotation / sample 7153695796642113

- `query_id`: `single`
- `instance_seed`: `7153695796642113`
- `word_count`: `84`
- `body_word_count`: `34`

```text
This image shows a top row of four boxed sequence cells with one question-mark box and a bottom row of four labeled option boxes. Which option completes the rotation sequence in the question-mark box?
Required annotation format: set "annotation" to one [x0, y0, x1, y1] box in image pixel coordinates for the correct option box.
Required answer format: set "answer" to the correct option label as a string, one of "A", "B", "C", or "D".
Example JSON:
{"annotation":[412,250,540,398],"answer":"C"}
```

### task_icons__named_field__reference_distance_rank_label / answer_and_annotation / sample 8139067715692166

- `query_id`: `second_closest_to_named_reference_label`
- `instance_seed`: `8139067715692166`
- `word_count`: `83`
- `body_word_count`: `29`

```text
The scene shows a panel with one reference icon, six option icons labeled A-F, and other icons. Which labeled icon is second closest to the green [#37B94B] "ladder" icon?
Answer format: set "answer" to the selected option letter as a string.
Annotation format: set "annotation" to a JSON object with keys "reference_icon" and "selected_candidate", each mapped to an [x0, y0, x1, y1] bounding box in image pixel coordinates.
Example JSON:
{"annotation":{"reference_icon":[178,244,238,304],"selected_candidate":[614,186,674,246]},"answer":"D"}
```

### task_icons__paired_canvas__color_change_count / answer_and_annotation / sample 7478583881841186

- `query_id`: `single`
- `instance_seed`: `7478583881841186`
- `word_count`: `83`
- `body_word_count`: `31`

```text
The picture shows two icon panels labeled Left and Right with corresponding icons at matching positions. How many Right-panel icons changed color compared with the corresponding icon in the Left panel?
Format for the "annotation" field: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates for every counted Right-panel icon.
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[620,156,684,220],[834,338,902,406]],"answer":2}
```

### task_icons__sequence_strip__size_progression_completion_label / answer_and_annotation / sample 5247823446222219

- `query_id`: `single`
- `instance_seed`: `5247823446222219`
- `word_count`: `83`
- `body_word_count`: `35`

```text
This image shows a top row of four boxed sequence cells with one question-mark box and a bottom row of four labeled option boxes. Which option has the icon size needed to complete the sequence?
Annotation format: set "annotation" to one [x0, y0, x1, y1] box in image pixel coordinates for the correct option box.
Answer format: set "answer" to the correct option label as a string, one of "A", "B", "C", or "D".
Example JSON:
{"annotation":[412,250,540,398],"answer":"C"}
```

### task_icons__single_transform_options__geometric_transform_result_label / answer_and_annotation / sample 4387994724023287

- `query_id`: `rotate_180_result_label`
- `instance_seed`: `4387994724023287`
- `word_count`: `83`
- `body_word_count`: `29`

```text
The scene shows a Reference icon with a transform cue and six labeled option icons. Find the labeled option that shows the Reference icon after rotating it 180 degrees.
Format for the "annotation" field: set "annotation" to a JSON object with keys "reference_icon" and "selected_option", each a [x0, y0, x1, y1] box in image pixel coordinates.
Format for the "answer" field: set "answer" to the selected option letter.
Example JSON:
{"annotation":{"reference_icon":[82,144,250,312],"selected_option":[532,104,702,274]},"answer":"C"}
```

### task_icons__named_field__reference_distance_rank_label / answer_and_annotation / sample 1473610398890102

- `query_id`: `closest_to_named_reference_label`
- `instance_seed`: `1473610398890102`
- `word_count`: `82`
- `body_word_count`: `28`

```text
The picture shows a panel with one reference icon, six option icons labeled A-F, and other icons. Which labeled icon is closest to the blue [#2D75E6] "bell" icon?
Answer format: set "answer" to the selected option letter as a string.
Annotation format: set "annotation" to a JSON object with keys "reference_icon" and "selected_candidate", each mapped to an [x0, y0, x1, y1] bounding box in image pixel coordinates.
Example JSON:
{"annotation":{"reference_icon":[178,244,238,304],"selected_candidate":[614,186,674,246]},"answer":"D"}
```

### task_icons__single_transform_options__geometric_transform_result_label / answer_and_annotation / sample 5476346005978608

- `query_id`: `rotate_90_clockwise_result_label`
- `instance_seed`: `5476346005978608`
- `word_count`: `82`
- `body_word_count`: `28`

```text
The scene shows a Reference icon with a transform cue and six labeled option icons. Which labeled option shows the Reference icon after a 90 degree clockwise rotation?
Format for the "annotation" field: set "annotation" to a JSON object with keys "reference_icon" and "selected_option", each a [x0, y0, x1, y1] box in image pixel coordinates.
Format for the "answer" field: set "answer" to the selected option letter.
Example JSON:
{"annotation":{"reference_icon":[82,144,250,312],"selected_option":[532,104,702,274]},"answer":"C"}
```

### task_icons__named_field__multi_attribute_xor_count / answer_and_annotation / sample 3309554842508908

- `query_id`: `single`
- `instance_seed`: `3309554842508908`
- `word_count`: `81`
- `body_word_count`: `27`

```text
The image shows a panel of colored icons. How many icons have exactly one of these properties: being a "heart" icon or having the color orange [#EE881A]?
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every icon satisfying the stated shape/attribute condition.
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[112,124,172,184],[630,298,690,358]],"answer":2}
```

### task_icons__named_path__path_neighbor_label / answer_and_annotation / sample 323946661420442

- `query_id`: `before_first_shape_label`
- `instance_seed`: `323946661420442`
- `word_count`: `81`
- `body_word_count`: `33`

```text
This image shows a START-to-END icon path with six option icons labeled A-F and other icons. Which labeled icon comes immediately before the first "bell" icon along the path from START to END?
Format for the "annotation" field: set "annotation" to the [x0, y0, x1, y1] bounding box in image pixel coordinates for the selected answer icon.
Format for the "answer" field: set "answer" to the selected option letter as a string.
Example JSON:
{"annotation":[546,246,606,306],"answer":"E"}
```

### task_icons__overlap_grid__occlusion_order_count / answer_and_annotation / sample 553596173110781

- `query_id`: `single`
- `instance_seed`: `553596173110781`
- `word_count`: `81`
- `body_word_count`: `29`

```text
The image shows a Reference cell beside a labeled Scene grid. How many labeled Scene cells match the Reference front-to-back order? Front-to-back order means which icon is on top.
Required annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around all matching Scene cells.
Required answer format: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[336,104,506,274],[532,104,702,274],[728,104,898,274]],"answer":3}
```

### task_icons__reference_canvas__anchor_position_count / answer_and_annotation / sample 5726129846258863

- `query_id`: `below_anchor`
- `instance_seed`: `5726129846258863`
- `word_count`: `81`
- `body_word_count`: `28`

```text
The figure shows a Reference icon beside a Scene panel with one icon marked Anchor. How many Scene icons match the Reference type and are below the Anchor?
Format for the "annotation" field: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every counted Scene icon.
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[322,152,377,207],[756,318,820,382]],"answer":2}
```

### task_icons__single_transform_options__geometric_transform_result_label / answer_and_annotation / sample 474308002447364

- `query_id`: `flip_horizontal_result_label`
- `instance_seed`: `474308002447364`
- `word_count`: `80`
- `body_word_count`: `26`

```text
The figure shows a Reference icon with a transform cue and six labeled option icons. Which labeled option shows the Reference icon after a horizontal flip?
Format for the "annotation" field: set "annotation" to a JSON object with keys "reference_icon" and "selected_option", each a [x0, y0, x1, y1] box in image pixel coordinates.
Format for the "answer" field: set "answer" to the selected option letter.
Example JSON:
{"annotation":{"reference_icon":[82,144,250,312],"selected_option":[532,104,702,274]},"answer":"C"}
```

### task_icons__named_field__counterfactual_attribute_count / answer_and_annotation / sample 7327870548895393

- `query_id`: `single`
- `instance_seed`: `7327870548895393`
- `word_count`: `79`
- `body_word_count`: `24`

```text
The picture shows a panel of icons. Suppose all "octagon" icons changed into "television" icons. How many "television" icons would be in the Scene?
Answer format: set "answer" to the resulting count as an integer.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every visible icon that would be counted after the hypothetical edit.
Example JSON:
{"annotation":[[112,124,172,184],[630,298,690,358]],"answer":2}
```

### task_icons__paired_canvas__rotation_change_count / answer_and_annotation / sample 3251322991150751

- `query_id`: `single`
- `instance_seed`: `3251322991150751`
- `word_count`: `79`
- `body_word_count`: `31`

```text
This image shows two icon panels labeled Left and Right with corresponding icons at matching positions. How many Right-panel icons changed rotation compared with the corresponding icon in the Left panel?
Required annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates for every counted Right-panel icon.
Required answer format: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[620,156,684,220],[834,338,902,406]],"answer":2}
```

### task_icons__reference_canvas__anchor_position_count / answer_and_annotation / sample 1975253822837643

- `query_id`: `right_of_anchor`
- `instance_seed`: `1975253822837643`
- `word_count`: `79`
- `body_word_count`: `31`

```text
The picture shows a Reference icon beside a Scene panel with one icon marked Anchor. How many Scene icons match the Reference type and are to the right of the Anchor?
Final answer format: set "answer" to the count as an integer.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every counted Scene icon.
Example JSON:
{"annotation":[[322,152,377,207],[756,318,820,382]],"answer":2}
```

### task_icons__named_strip__shape_run_length / answer_and_annotation / sample 7033601339105322

- `query_id`: `longest_shape_run_length`
- `instance_seed`: `7033601339105322`
- `word_count`: `78`
- `body_word_count`: `20`

```text
This image shows a horizontal row of boxed icons. What is the maximum length of a consecutive "acorn" icon run?
Required annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates for the icons in the run that determines the answer.
Required answer format: set "answer" to the run length as an integer.
Example JSON:
{"annotation":[[220,132,270,182],[292,132,342,182],[364,132,414,182]],"answer":3}
```

### task_icons__paired_canvas__panel_set_relation_count / answer_and_annotation / sample 7708997564796638

- `query_id`: `added_in_right_count`
- `instance_seed`: `7708997564796638`
- `word_count`: `78`
- `body_word_count`: `28`

```text
This image shows two icon panels labeled Left and Right. How many Right-panel icons are new, meaning they do not exactly match any icon in the Left panel?
Final answer format: set "answer" to the count as an integer.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates for every counted icon in the relevant panel.
Example JSON:
{"annotation":[[620,156,684,220],[834,338,902,406]],"answer":2}
```

### task_icons__single_transform_options__geometric_transform_result_label / answer_and_annotation / sample 5114016568751050

- `query_id`: `rotate_90_counterclockwise_result_label`
- `instance_seed`: `5114016568751050`
- `word_count`: `78`
- `body_word_count`: `30`

```text
The picture shows a Reference icon with a transform cue and six labeled option icons. Find the labeled option that shows the Reference icon after rotating it 90 degrees counterclockwise.
Annotation format: set "annotation" to a JSON object with keys "reference_icon" and "selected_option", each a [x0, y0, x1, y1] box in image pixel coordinates.
Answer field: set "answer" to the selected option letter.
Example JSON:
{"annotation":{"reference_icon":[82,144,250,312],"selected_option":[532,104,702,274]},"answer":"C"}
```

### task_icons__wallpaper_panels__same_pattern_as_reference_label / answer_and_annotation / sample 4792880301869547

- `query_id`: `single`
- `instance_seed`: `4792880301869547`
- `word_count`: `78`
- `body_word_count`: `28`

```text
The scene shows one Reference wallpaper panel above four labeled wallpaper panels filled with repeated icon motifs. Find the labeled wallpaper panel that matches the Reference panel's pattern.
Annotation format: set "annotation" to a JSON object with keys "reference_panel" and "selected_panel", each mapped to one [x0, y0, x1, y1] box in image pixel coordinates.
Answer field: set "answer" to the selected panel letter.
Example JSON:
{"annotation":{"reference_panel":[36,36,320,604],"selected_panel":[420,220,620,400]},"answer":"C"}
```

### task_icons__icon_field__most_frequent_type_count / answer_and_annotation / sample 5525981113045451

- `query_id`: `single`
- `instance_seed`: `5525981113045451`
- `word_count`: `77`
- `body_word_count`: `19`

```text
The image shows one panel of assorted icons. How many Scene icons share the type that appears most often?
Format for the "annotation" field: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every counted icon of the unique most frequent type.
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[116,128,176,188],[639,307,699,367]],"answer":2}
```

### task_icons__named_field__counterfactual_total_count / answer_and_annotation / sample 923877976192543

- `query_id`: `single`
- `instance_seed`: `923877976192543`
- `word_count`: `77`
- `body_word_count`: `21`

```text
The image shows a panel of icons. Suppose all "fish" icons were removed from the Scene. How many icons would remain?
Final answer format: set "answer" to the resulting count as an integer.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every visible icon that would be counted after the hypothetical edit.
Example JSON:
{"annotation":[[112,124,172,184],[630,298,690,358]],"answer":2}
```

## Repeated Scaffolding Terms

## All Prompt Samples

### task_icons__icon_cutout__partial_match_label / single / answer_and_annotation / sample 6773916202758274

- `instance_seed`: `6773916202758274`
- `word_count`: `76`
- `body_word_count`: `22`

```text
The picture shows a partial icon fragment beside six labeled full-icon options. Which labeled full icon does the partial fragment come from?
Final answer format: set "answer" to the selected option letter as a string.
Annotation format: set "annotation" to a JSON object with keys "source_fragment" and "selected_option", each mapped to a [x0, y0, x1, y1] box in image pixel coordinates.
Example JSON:
{"annotation":{"source_fragment":[84,168,248,332],"selected_option":[492,112,662,282]},"answer":"C"}
```

### task_icons__icon_cutout__partial_match_label / single / answer_only / sample 6773916202758274

- `instance_seed`: `6773916202758274`
- `word_count`: `41`
- `body_word_count`: `22`

```text
The picture shows a partial icon fragment beside six labeled full-icon options. Which labeled full icon does the partial fragment come from?
Format for the "answer" field: set "answer" to the selected option letter as a string.
Example JSON:
{"answer":"C"}
```

### task_icons__icon_field__most_frequent_type_count / single / answer_and_annotation / sample 5525981113045451

- `instance_seed`: `5525981113045451`
- `word_count`: `77`
- `body_word_count`: `19`

```text
The image shows one panel of assorted icons. How many Scene icons share the type that appears most often?
Format for the "annotation" field: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every counted icon of the unique most frequent type.
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[116,128,176,188],[639,307,699,367]],"answer":2}
```

### task_icons__icon_field__most_frequent_type_count / single / answer_only / sample 5525981113045451

- `instance_seed`: `5525981113045451`
- `word_count`: `36`
- `body_word_count`: `19`

```text
The image shows one panel of assorted icons. How many Scene icons share the type that appears most often?
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_icons__icon_field__singleton_type_count / single / answer_and_annotation / sample 5906592065124997

- `instance_seed`: `5906592065124997`
- `word_count`: `65`
- `body_word_count`: `19`

```text
The image shows one panel of assorted icons. How many Scene icons have a type that appears exactly once?
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every counted icon.
Answer format: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[116,128,176,188],[639,307,699,367]],"answer":2}
```

### task_icons__icon_field__singleton_type_count / single / answer_only / sample 5906592065124997

- `instance_seed`: `5906592065124997`
- `word_count`: `33`
- `body_word_count`: `29`

```text
The image shows one panel of assorted icons. How many Scene icons have a type that appears exactly once?
Answer field: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_icons__mirror_grid__mirror_symmetry_match_label / single / answer_and_annotation / sample 4081773044150787

- `instance_seed`: `4081773044150787`
- `word_count`: `76`
- `body_word_count`: `25`

```text
The scene shows a Reference cell beside labeled option cells containing icons. Which labeled option cell has the same mirror symmetry as the Reference cell?
Final answer format: set "answer" to the matching option letter.
Annotation format: set "annotation" to a JSON object with keys "reference_cell" and "matching_option_cell", each mapped to a [x0, y0, x1, y1] box in image pixel coordinates.
Example JSON:
{"annotation":{"reference_cell":[44,190,268,414],"matching_option_cell":[590,120,790,320]},"answer":"C"}
```

### task_icons__mirror_grid__mirror_symmetry_match_label / single / answer_only / sample 4081773044150787

- `instance_seed`: `4081773044150787`
- `word_count`: `38`
- `body_word_count`: `25`

```text
The scene shows a Reference cell beside labeled option cells containing icons. Which labeled option cell has the same mirror symmetry as the Reference cell?
Answer format: set "answer" to the matching option letter.
Example JSON:
{"answer":"C"}
```

### task_icons__named_field__closer_to_reference_count / single / answer_and_annotation / sample 1323598023808579

- `instance_seed`: `1323598023808579`
- `word_count`: `76`
- `body_word_count`: `28`

```text
The figure shows a panel with two larger reference icons and several icons. How many "ladder" icons are closer to the "cactus" icon than to the "leaf" icon?
Required answer format: set "answer" to the count as an integer.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every counted "ladder" icon.
Example JSON:
{"annotation":[[112,124,172,184],[234,124,294,184]],"answer":2}
```

### task_icons__named_field__closer_to_reference_count / single / answer_only / sample 1323598023808579

- `instance_seed`: `1323598023808579`
- `word_count`: `42`
- `body_word_count`: `28`

```text
The figure shows a panel with two larger reference icons and several icons. How many "ladder" icons are closer to the "cactus" icon than to the "leaf" icon?
Answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_icons__named_field__counterfactual_attribute_count / single / answer_and_annotation / sample 7327870548895393

- `instance_seed`: `7327870548895393`
- `word_count`: `79`
- `body_word_count`: `24`

```text
The picture shows a panel of icons. Suppose all "octagon" icons changed into "television" icons. How many "television" icons would be in the Scene?
Answer format: set "answer" to the resulting count as an integer.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every visible icon that would be counted after the hypothetical edit.
Example JSON:
{"annotation":[[112,124,172,184],[630,298,690,358]],"answer":2}
```

### task_icons__named_field__counterfactual_attribute_count / single / answer_only / sample 7327870548895393

- `instance_seed`: `7327870548895393`
- `word_count`: `42`
- `body_word_count`: `24`

```text
The picture shows a panel of icons. Suppose all "octagon" icons changed into "television" icons. How many "television" icons would be in the Scene?
Format for the "answer" field: set "answer" to the resulting count as an integer.
Example JSON:
{"answer":2}
```

### task_icons__named_field__counterfactual_total_count / single / answer_and_annotation / sample 923877976192543

- `instance_seed`: `923877976192543`
- `word_count`: `77`
- `body_word_count`: `21`

```text
The image shows a panel of icons. Suppose all "fish" icons were removed from the Scene. How many icons would remain?
Final answer format: set "answer" to the resulting count as an integer.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every visible icon that would be counted after the hypothetical edit.
Example JSON:
{"annotation":[[112,124,172,184],[630,298,690,358]],"answer":2}
```

### task_icons__named_field__counterfactual_total_count / single / answer_only / sample 923877976192543

- `instance_seed`: `923877976192543`
- `word_count`: `39`
- `body_word_count`: `21`

```text
The image shows a panel of icons. Suppose all "fish" icons were removed from the Scene. How many icons would remain?
Format for the "answer" field: set "answer" to the resulting count as an integer.
Example JSON:
{"answer":2}
```

### task_icons__named_field__multi_attribute_and_count / single / answer_and_annotation / sample 3199398450219603

- `instance_seed`: `3199398450219603`
- `word_count`: `74`
- `body_word_count`: `20`

```text
The scene shows a panel of colored icons. How many icons are "candle" icons and have the color maroon [#963644]?
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every icon satisfying the stated shape/attribute condition.
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[112,124,172,184],[630,298,690,358]],"answer":2}
```

### task_icons__named_field__multi_attribute_and_count / single / answer_only / sample 3199398450219603

- `instance_seed`: `3199398450219603`
- `word_count`: `34`
- `body_word_count`: `20`

```text
The scene shows a panel of colored icons. How many icons are "candle" icons and have the color maroon [#963644]?
Answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_icons__named_field__multi_attribute_complement_count / single / answer_and_annotation / sample 2807149780265058

- `instance_seed`: `2807149780265058`
- `word_count`: `74`
- `body_word_count`: `22`

```text
The scene shows a panel of colored icons. How many icons are neither "star" icons nor icons with the color maroon [#963644]?
Required answer format: set "answer" to the count as an integer.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every icon satisfying the stated shape/attribute condition.
Example JSON:
{"annotation":[[112,124,172,184],[630,298,690,358]],"answer":2}
```

### task_icons__named_field__multi_attribute_complement_count / single / answer_only / sample 2807149780265058

- `instance_seed`: `2807149780265058`
- `word_count`: `39`
- `body_word_count`: `22`

```text
The scene shows a panel of colored icons. How many icons are neither "star" icons nor icons with the color maroon [#963644]?
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_icons__named_field__multi_attribute_exclusion_count / color_and_not_shape_count / answer_and_annotation / sample 3041161223449461

- `instance_seed`: `3041161223449461`
- `word_count`: `72`
- `body_word_count`: `21`

```text
The image shows a panel of colored icons. How many icons have the color green [#37B94B] but are not "sun" icons?
Answer format: set "answer" to the count as an integer.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every icon satisfying the stated shape/attribute condition.
Example JSON:
{"annotation":[[112,124,172,184],[630,298,690,358]],"answer":2}
```

### task_icons__named_field__multi_attribute_exclusion_count / color_and_not_shape_count / answer_only / sample 3041161223449461

- `instance_seed`: `3041161223449461`
- `word_count`: `35`
- `body_word_count`: `21`

```text
The image shows a panel of colored icons. How many icons have the color green [#37B94B] but are not "sun" icons?
Answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_icons__named_field__multi_attribute_exclusion_count / shape_and_not_color_count / answer_and_annotation / sample 3532760237808208

- `instance_seed`: `3532760237808208`
- `word_count`: `74`
- `body_word_count`: `22`

```text
The picture shows a panel of colored icons. How many icons are "cloud" icons but do not have the color red [#E63232]?
Required answer format: set "answer" to the count as an integer.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every icon satisfying the stated shape/attribute condition.
Example JSON:
{"annotation":[[112,124,172,184],[630,298,690,358]],"answer":2}
```

### task_icons__named_field__multi_attribute_exclusion_count / shape_and_not_color_count / answer_only / sample 3532760237808208

- `instance_seed`: `3532760237808208`
- `word_count`: `37`
- `body_word_count`: `22`

```text
The picture shows a panel of colored icons. How many icons are "cloud" icons but do not have the color red [#E63232]?
Required answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_icons__named_field__multi_attribute_or_count / single / answer_and_annotation / sample 641175837573619

- `instance_seed`: `641175837573619`
- `word_count`: `72`
- `body_word_count`: `21`

```text
The image shows a panel of colored icons. How many icons are "house" icons, have the color yellow [#D4C21E], or both?
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every icon satisfying the stated shape/attribute condition.
Answer format: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[112,124,172,184],[630,298,690,358]],"answer":2}
```

### task_icons__named_field__multi_attribute_or_count / single / answer_only / sample 641175837573619

- `instance_seed`: `641175837573619`
- `word_count`: `36`
- `body_word_count`: `21`

```text
The image shows a panel of colored icons. How many icons are "house" icons, have the color yellow [#D4C21E], or both?
Final answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_icons__named_field__multi_attribute_xor_count / single / answer_and_annotation / sample 3309554842508908

- `instance_seed`: `3309554842508908`
- `word_count`: `81`
- `body_word_count`: `27`

```text
The image shows a panel of colored icons. How many icons have exactly one of these properties: being a "heart" icon or having the color orange [#EE881A]?
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every icon satisfying the stated shape/attribute condition.
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[112,124,172,184],[630,298,690,358]],"answer":2}
```

### task_icons__named_field__multi_attribute_xor_count / single / answer_only / sample 3309554842508908

- `instance_seed`: `3309554842508908`
- `word_count`: `44`
- `body_word_count`: `27`

```text
The image shows a panel of colored icons. How many icons have exactly one of these properties: being a "heart" icon or having the color orange [#EE881A]?
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_icons__named_field__reference_distance_rank_label / closest_to_named_reference_label / answer_and_annotation / sample 1473610398890102

- `instance_seed`: `1473610398890102`
- `word_count`: `82`
- `body_word_count`: `28`

```text
The picture shows a panel with one reference icon, six option icons labeled A-F, and other icons. Which labeled icon is closest to the blue [#2D75E6] "bell" icon?
Answer format: set "answer" to the selected option letter as a string.
Annotation format: set "annotation" to a JSON object with keys "reference_icon" and "selected_candidate", each mapped to an [x0, y0, x1, y1] bounding box in image pixel coordinates.
Example JSON:
{"annotation":{"reference_icon":[178,244,238,304],"selected_candidate":[614,186,674,246]},"answer":"D"}
```

### task_icons__named_field__reference_distance_rank_label / closest_to_named_reference_label / answer_only / sample 1473610398890102

- `instance_seed`: `1473610398890102`
- `word_count`: `47`
- `body_word_count`: `28`

```text
The picture shows a panel with one reference icon, six option icons labeled A-F, and other icons. Which labeled icon is closest to the blue [#2D75E6] "bell" icon?
Format for the "answer" field: set "answer" to the selected option letter as a string.
Example JSON:
{"answer":"D"}
```

### task_icons__named_field__reference_distance_rank_label / farthest_from_named_reference_label / answer_and_annotation / sample 3530764205146963

- `instance_seed`: `3530764205146963`
- `word_count`: `85`
- `body_word_count`: `28`

```text
The figure shows a panel with one reference icon, six option icons labeled A-F, and other icons. Which labeled icon is farthest from the green [#37B94B] "lightbulb" icon?
Annotation format: set "annotation" to a JSON object with keys "reference_icon" and "selected_candidate", each mapped to an [x0, y0, x1, y1] bounding box in image pixel coordinates.
Format for the "answer" field: set "answer" to the selected option letter as a string.
Example JSON:
{"annotation":{"reference_icon":[178,244,238,304],"selected_candidate":[614,186,674,246]},"answer":"D"}
```

### task_icons__named_field__reference_distance_rank_label / farthest_from_named_reference_label / answer_only / sample 3530764205146963

- `instance_seed`: `3530764205146963`
- `word_count`: `47`
- `body_word_count`: `28`

```text
The figure shows a panel with one reference icon, six option icons labeled A-F, and other icons. Which labeled icon is farthest from the green [#37B94B] "lightbulb" icon?
Format for the "answer" field: set "answer" to the selected option letter as a string.
Example JSON:
{"answer":"D"}
```

### task_icons__named_field__reference_distance_rank_label / second_closest_to_named_reference_label / answer_and_annotation / sample 8139067715692166

- `instance_seed`: `8139067715692166`
- `word_count`: `83`
- `body_word_count`: `29`

```text
The scene shows a panel with one reference icon, six option icons labeled A-F, and other icons. Which labeled icon is second closest to the green [#37B94B] "ladder" icon?
Answer format: set "answer" to the selected option letter as a string.
Annotation format: set "annotation" to a JSON object with keys "reference_icon" and "selected_candidate", each mapped to an [x0, y0, x1, y1] bounding box in image pixel coordinates.
Example JSON:
{"annotation":{"reference_icon":[178,244,238,304],"selected_candidate":[614,186,674,246]},"answer":"D"}
```

### task_icons__named_field__reference_distance_rank_label / second_closest_to_named_reference_label / answer_only / sample 8139067715692166

- `instance_seed`: `8139067715692166`
- `word_count`: `46`
- `body_word_count`: `29`

```text
The scene shows a panel with one reference icon, six option icons labeled A-F, and other icons. Which labeled icon is second closest to the green [#37B94B] "ladder" icon?
Final answer format: set "answer" to the selected option letter as a string.
Example JSON:
{"answer":"D"}
```

### task_icons__named_field__scoped_attribute_count / inside_band_count / answer_and_annotation / sample 5662424099408909

- `instance_seed`: `5662424099408909`
- `word_count`: `72`
- `body_word_count`: `25`

```text
This image shows a panel of icons and a marked region. How many "flag" icons have centers inside the band between the two parallel lines?
Answer format: set "answer" to the count as an integer.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every counted "flag" icon.
Example JSON:
{"annotation":[[112,124,172,184],[630,298,690,358]],"answer":2}
```

### task_icons__named_field__scoped_attribute_count / inside_band_count / answer_only / sample 5662424099408909

- `instance_seed`: `5662424099408909`
- `word_count`: `39`
- `body_word_count`: `25`

```text
This image shows a panel of icons and a marked region. How many "flag" icons have centers inside the band between the two parallel lines?
Answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_icons__named_field__scoped_attribute_count / inside_quadrant_count / answer_and_annotation / sample 6463941879431529

- `instance_seed`: `6463941879431529`
- `word_count`: `68`
- `body_word_count`: `21`

```text
This image shows a panel of icons and a marked region. How many "knife" icons have centers inside the highlighted quadrant?
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every counted "knife" icon.
Answer format: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[112,124,172,184],[630,298,690,358]],"answer":2}
```

### task_icons__named_field__scoped_attribute_count / inside_quadrant_count / answer_only / sample 6463941879431529

- `instance_seed`: `6463941879431529`
- `word_count`: `38`
- `body_word_count`: `21`

```text
This image shows a panel of icons and a marked region. How many "knife" icons have centers inside the highlighted quadrant?
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_icons__named_field__scoped_attribute_count / inside_shape_count / answer_and_annotation / sample 4463539394043117

- `instance_seed`: `4463539394043117`
- `word_count`: `71`
- `body_word_count`: `21`

```text
The scene shows a panel of icons and a marked region. How many "crescent" icons have centers inside the marked shape?
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every counted "crescent" icon.
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[112,124,172,184],[630,298,690,358]],"answer":2}
```

### task_icons__named_field__scoped_attribute_count / inside_shape_count / answer_only / sample 4463539394043117

- `instance_seed`: `4463539394043117`
- `word_count`: `35`
- `body_word_count`: `21`

```text
The scene shows a panel of icons and a marked region. How many "crescent" icons have centers inside the marked shape?
Answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_icons__named_field__scoped_attribute_count / inside_shelf_count / answer_and_annotation / sample 5657667349903944

- `instance_seed`: `5657667349903944`
- `word_count`: `68`
- `body_word_count`: `21`

```text
The picture shows a panel of icons and a marked region. How many "lock" icons have centers inside the highlighted shelf?
Answer format: set "answer" to the count as an integer.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every counted "lock" icon.
Example JSON:
{"annotation":[[112,124,172,184],[630,298,690,358]],"answer":2}
```

### task_icons__named_field__scoped_attribute_count / inside_shelf_count / answer_only / sample 5657667349903944

- `instance_seed`: `5657667349903944`
- `word_count`: `36`
- `body_word_count`: `21`

```text
The picture shows a panel of icons and a marked region. How many "lock" icons have centers inside the highlighted shelf?
Final answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_icons__named_field__scoped_attribute_count / outside_band_count / answer_and_annotation / sample 833907121494640

- `instance_seed`: `833907121494640`
- `word_count`: `72`
- `body_word_count`: `25`

```text
The picture shows a panel of icons and a marked region. How many "chair" icons have centers outside the band between the two parallel lines?
Answer format: set "answer" to the count as an integer.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every counted "chair" icon.
Example JSON:
{"annotation":[[112,124,172,184],[630,298,690,358]],"answer":2}
```

### task_icons__named_field__scoped_attribute_count / outside_band_count / answer_only / sample 833907121494640

- `instance_seed`: `833907121494640`
- `word_count`: `39`
- `body_word_count`: `25`

```text
The picture shows a panel of icons and a marked region. How many "chair" icons have centers outside the band between the two parallel lines?
Answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_icons__named_field__scoped_attribute_count / outside_shape_count / answer_and_annotation / sample 1960741675400693

- `instance_seed`: `1960741675400693`
- `word_count`: `68`
- `body_word_count`: `21`

```text
The image shows a panel of icons and a marked region. How many "tent" icons have centers outside the marked shape?
Answer format: set "answer" to the count as an integer.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every counted "tent" icon.
Example JSON:
{"annotation":[[112,124,172,184],[630,298,690,358]],"answer":2}
```

### task_icons__named_field__scoped_attribute_count / outside_shape_count / answer_only / sample 1960741675400693

- `instance_seed`: `1960741675400693`
- `word_count`: `35`
- `body_word_count`: `21`

```text
The image shows a panel of icons and a marked region. How many "tent" icons have centers outside the marked shape?
Answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_icons__named_field__single_attribute_membership_count / single / answer_and_annotation / sample 7737839815296844

- `instance_seed`: `7737839815296844`
- `word_count`: `62`
- `body_word_count`: `15`

```text
The figure shows a panel of icons. How many "anchor" icons are in the panel?
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every counted "anchor" icon.
Answer format: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[112,124,172,184],[630,298,690,358]],"answer":2}
```

### task_icons__named_field__single_attribute_membership_count / single / answer_only / sample 7737839815296844

- `instance_seed`: `7737839815296844`
- `word_count`: `30`
- `body_word_count`: `15`

```text
The figure shows a panel of icons. How many "anchor" icons are in the panel?
Final answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_icons__named_grid__group_predicate_count / column_at_least_shape_count / answer_and_annotation / sample 1887661314054002

- `instance_seed`: `1887661314054002`
- `word_count`: `72`
- `body_word_count`: `21`

```text
The scene shows a numbered grid with one icon in each cell. How many columns contain at least 3 "lock" icons?
Required answer format: set "answer" to the number of qualifying columns as an integer.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every qualifying column region.
Example JSON:
{"annotation":[[96,168,620,228],[96,336,620,396]],"answer":2}
```

### task_icons__named_grid__group_predicate_count / column_at_least_shape_count / answer_only / sample 1887661314054002

- `instance_seed`: `1887661314054002`
- `word_count`: `39`
- `body_word_count`: `21`

```text
The scene shows a numbered grid with one icon in each cell. How many columns contain at least 3 "lock" icons?
Final answer format: set "answer" to the number of qualifying columns as an integer.
Example JSON:
{"answer":2}
```

### task_icons__named_grid__group_predicate_count / column_exactly_shape_count / answer_and_annotation / sample 6966729794309525

- `instance_seed`: `6966729794309525`
- `word_count`: `72`
- `body_word_count`: `21`

```text
The picture shows a numbered grid with one icon in each cell. How many columns contain exactly 3 "lightning bolt" icons?
Final answer format: set "answer" to the number of qualifying columns as an integer.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every qualifying column region.
Example JSON:
{"annotation":[[96,168,620,228],[96,336,620,396]],"answer":2}
```

### task_icons__named_grid__group_predicate_count / column_exactly_shape_count / answer_only / sample 6966729794309525

- `instance_seed`: `6966729794309525`
- `word_count`: `38`
- `body_word_count`: `21`

```text
The picture shows a numbered grid with one icon in each cell. How many columns contain exactly 3 "lightning bolt" icons?
Answer format: set "answer" to the number of qualifying columns as an integer.
Example JSON:
{"answer":2}
```

### task_icons__named_grid__group_predicate_count / column_no_shape_count / answer_and_annotation / sample 6039457033859196

- `instance_seed`: `6039457033859196`
- `word_count`: `70`
- `body_word_count`: `19`

```text
The scene shows a numbered grid with one icon in each cell. How many columns contain no "phone" icons?
Final answer format: set "answer" to the number of qualifying columns as an integer.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every qualifying column region.
Example JSON:
{"annotation":[[96,168,620,228],[96,336,620,396]],"answer":2}
```

### task_icons__named_grid__group_predicate_count / column_no_shape_count / answer_only / sample 6039457033859196

- `instance_seed`: `6039457033859196`
- `word_count`: `36`
- `body_word_count`: `19`

```text
The scene shows a numbered grid with one icon in each cell. How many columns contain no "phone" icons?
Answer format: set "answer" to the number of qualifying columns as an integer.
Example JSON:
{"answer":2}
```

### task_icons__named_grid__group_predicate_count / row_at_least_shape_count / answer_and_annotation / sample 2343887113186092

- `instance_seed`: `2343887113186092`
- `word_count`: `72`
- `body_word_count`: `21`

```text
The image shows a numbered grid with one icon in each cell. How many rows contain at least 2 "flower" icons?
Final answer format: set "answer" to the number of qualifying rows as an integer.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every qualifying row region.
Example JSON:
{"annotation":[[96,168,620,228],[96,336,620,396]],"answer":2}
```

### task_icons__named_grid__group_predicate_count / row_at_least_shape_count / answer_only / sample 2343887113186092

- `instance_seed`: `2343887113186092`
- `word_count`: `41`
- `body_word_count`: `21`

```text
The image shows a numbered grid with one icon in each cell. How many rows contain at least 2 "flower" icons?
Format for the "answer" field: set "answer" to the number of qualifying rows as an integer.
Example JSON:
{"answer":2}
```

### task_icons__named_grid__group_predicate_count / row_exactly_shape_count / answer_and_annotation / sample 3402616456914974

- `instance_seed`: `3402616456914974`
- `word_count`: `71`
- `body_word_count`: `20`

```text
The image shows a numbered grid with one icon in each cell. How many rows contain exactly 2 "crescent" icons?
Required answer format: set "answer" to the number of qualifying rows as an integer.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every qualifying row region.
Example JSON:
{"annotation":[[96,168,620,228],[96,336,620,396]],"answer":2}
```

### task_icons__named_grid__group_predicate_count / row_exactly_shape_count / answer_only / sample 3402616456914974

- `instance_seed`: `3402616456914974`
- `word_count`: `38`
- `body_word_count`: `20`

```text
The image shows a numbered grid with one icon in each cell. How many rows contain exactly 2 "crescent" icons?
Required answer format: set "answer" to the number of qualifying rows as an integer.
Example JSON:
{"answer":2}
```

### task_icons__named_grid__group_predicate_count / row_no_shape_count / answer_and_annotation / sample 1869226003119589

- `instance_seed`: `1869226003119589`
- `word_count`: `69`
- `body_word_count`: `19`

```text
The picture shows a numbered grid with one icon in each cell. How many rows contain no "candle" icons?
Answer format: set "answer" to the number of qualifying rows as an integer.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every qualifying row region.
Example JSON:
{"annotation":[[96,168,620,228],[96,336,620,396]],"answer":2}
```

### task_icons__named_grid__group_predicate_count / row_no_shape_count / answer_only / sample 1869226003119589

- `instance_seed`: `1869226003119589`
- `word_count`: `36`
- `body_word_count`: `19`

```text
The picture shows a numbered grid with one icon in each cell. How many rows contain no "candle" icons?
Answer format: set "answer" to the number of qualifying rows as an integer.
Example JSON:
{"answer":2}
```

### task_icons__named_grid__row_column_shape_extreme_number / column_fewest_shape_number / answer_and_annotation / sample 6531517070176659

- `instance_seed`: `6531517070176659`
- `word_count`: `75`
- `body_word_count`: `19`

```text
The image shows a numbered grid with one icon in each cell. Which column has the fewest "shield" icons?
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for the "shield" icons in the selected column.
Answer format: set "answer" to the selected column number as an integer.
Example JSON:
{"annotation":[[176,168,236,228],[384,168,444,228],[592,168,652,228]],"answer":3}
```

### task_icons__named_grid__row_column_shape_extreme_number / column_fewest_shape_number / answer_only / sample 6531517070176659

- `instance_seed`: `6531517070176659`
- `word_count`: `36`
- `body_word_count`: `19`

```text
The image shows a numbered grid with one icon in each cell. Which column has the fewest "shield" icons?
Final answer format: set "answer" to the selected column number as an integer.
Example JSON:
{"answer":3}
```

### task_icons__named_grid__row_column_shape_extreme_number / column_most_shape_number / answer_and_annotation / sample 4479156772626360

- `instance_seed`: `4479156772626360`
- `word_count`: `75`
- `body_word_count`: `19`

```text
The picture shows a numbered grid with one icon in each cell. Which column has the most "butterfly" icons?
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for the "butterfly" icons in the selected column.
Answer format: set "answer" to the selected column number as an integer.
Example JSON:
{"annotation":[[176,168,236,228],[384,168,444,228],[592,168,652,228]],"answer":3}
```

### task_icons__named_grid__row_column_shape_extreme_number / column_most_shape_number / answer_only / sample 4479156772626360

- `instance_seed`: `4479156772626360`
- `word_count`: `35`
- `body_word_count`: `19`

```text
The picture shows a numbered grid with one icon in each cell. Which column has the most "butterfly" icons?
Answer format: set "answer" to the selected column number as an integer.
Example JSON:
{"answer":3}
```

### task_icons__named_grid__row_column_shape_extreme_number / row_fewest_shape_number / answer_and_annotation / sample 533187826583770

- `instance_seed`: `533187826583770`
- `word_count`: `76`
- `body_word_count`: `19`

```text
The scene shows a numbered grid with one icon in each cell. Which row has the fewest "kite" icons?
Final answer format: set "answer" to the selected row number as an integer.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for the "kite" icons in the selected row.
Example JSON:
{"annotation":[[176,168,236,228],[384,168,444,228],[592,168,652,228]],"answer":3}
```

### task_icons__named_grid__row_column_shape_extreme_number / row_fewest_shape_number / answer_only / sample 533187826583770

- `instance_seed`: `533187826583770`
- `word_count`: `35`
- `body_word_count`: `19`

```text
The scene shows a numbered grid with one icon in each cell. Which row has the fewest "kite" icons?
Answer format: set "answer" to the selected row number as an integer.
Example JSON:
{"answer":3}
```

### task_icons__named_grid__row_column_shape_extreme_number / row_most_shape_number / answer_and_annotation / sample 872576557318355

- `instance_seed`: `872576557318355`
- `word_count`: `75`
- `body_word_count`: `19`

```text
The figure shows a numbered grid with one icon in each cell. Which row has the most "dice" icons?
Answer format: set "answer" to the selected row number as an integer.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for the "dice" icons in the selected row.
Example JSON:
{"annotation":[[176,168,236,228],[384,168,444,228],[592,168,652,228]],"answer":3}
```

### task_icons__named_grid__row_column_shape_extreme_number / row_most_shape_number / answer_only / sample 872576557318355

- `instance_seed`: `872576557318355`
- `word_count`: `38`
- `body_word_count`: `19`

```text
The figure shows a numbered grid with one icon in each cell. Which row has the most "dice" icons?
Format for the "answer" field: set "answer" to the selected row number as an integer.
Example JSON:
{"answer":3}
```

### task_icons__named_grid__scoped_attribute_count / column_shape_count / answer_and_annotation / sample 7099472272587253

- `instance_seed`: `7099472272587253`
- `word_count`: `75`
- `body_word_count`: `20`

```text
This image shows a numbered grid with one icon in each cell. How many "watch" icons are in column 3?
Final answer format: set "answer" to the count as an integer.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every counted "watch" icon in column 3.
Example JSON:
{"annotation":[[176,168,236,228],[384,168,444,228],[592,168,652,228]],"answer":3}
```

### task_icons__named_grid__scoped_attribute_count / column_shape_count / answer_only / sample 7099472272587253

- `instance_seed`: `7099472272587253`
- `word_count`: `35`
- `body_word_count`: `20`

```text
This image shows a numbered grid with one icon in each cell. How many "watch" icons are in column 3?
Final answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":3}
```

### task_icons__named_grid__scoped_attribute_count / row_shape_count / answer_and_annotation / sample 311616692529067

- `instance_seed`: `311616692529067`
- `word_count`: `75`
- `body_word_count`: `20`

```text
The figure shows a numbered grid with one icon in each cell. How many "headphones" icons are in row 5?
Required answer format: set "answer" to the count as an integer.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every counted "headphones" icon in row 5.
Example JSON:
{"annotation":[[176,168,236,228],[384,168,444,228],[592,168,652,228]],"answer":3}
```

### task_icons__named_grid__scoped_attribute_count / row_shape_count / answer_only / sample 311616692529067

- `instance_seed`: `311616692529067`
- `word_count`: `35`
- `body_word_count`: `20`

```text
The figure shows a numbered grid with one icon in each cell. How many "headphones" icons are in row 5?
Final answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":3}
```

### task_icons__named_path__path_neighbor_label / after_first_shape_label / answer_and_annotation / sample 953454137435421

- `instance_seed`: `953454137435421`
- `word_count`: `77`
- `body_word_count`: `33`

```text
The image shows a START-to-END icon path with six option icons labeled A-F and other icons. Which labeled icon comes immediately after the first "hourglass" icon along the path from START to END?
Required annotation format: set "annotation" to the [x0, y0, x1, y1] bounding box in image pixel coordinates for the selected answer icon.
Required answer format: set "answer" to the selected option letter as a string.
Example JSON:
{"annotation":[546,246,606,306],"answer":"E"}
```

### task_icons__named_path__path_neighbor_label / after_first_shape_label / answer_only / sample 953454137435421

- `instance_seed`: `953454137435421`
- `word_count`: `49`
- `body_word_count`: `33`

```text
The image shows a START-to-END icon path with six option icons labeled A-F and other icons. Which labeled icon comes immediately after the first "hourglass" icon along the path from START to END?
Answer format: set "answer" to the selected option letter as a string.
Example JSON:
{"answer":"E"}
```

### task_icons__named_path__path_neighbor_label / after_last_shape_label / answer_and_annotation / sample 279008590749551

- `instance_seed`: `279008590749551`
- `word_count`: `77`
- `body_word_count`: `34`

```text
The scene shows a START-to-END icon path with six option icons labeled A-F and other icons. Which labeled icon comes immediately after the last "trash can" icon along the path from START to END?
Final answer format: set "answer" to the selected option letter as a string.
Annotation format: set "annotation" to the [x0, y0, x1, y1] bounding box in image pixel coordinates for the selected answer icon.
Example JSON:
{"annotation":[546,246,606,306],"answer":"E"}
```

### task_icons__named_path__path_neighbor_label / after_last_shape_label / answer_only / sample 279008590749551

- `instance_seed`: `279008590749551`
- `word_count`: `50`
- `body_word_count`: `46`

```text
The scene shows a START-to-END icon path with six option icons labeled A-F and other icons. Which labeled icon comes immediately after the last "trash can" icon along the path from START to END?
Answer field: set "answer" to the selected option letter as a string.
Example JSON:
{"answer":"E"}
```

### task_icons__named_path__path_neighbor_label / after_second_shape_label / answer_and_annotation / sample 2296233589938078

- `instance_seed`: `2296233589938078`
- `word_count`: `77`
- `body_word_count`: `33`

```text
The figure shows a START-to-END icon path with six option icons labeled A-F and other icons. Which labeled icon comes immediately after the second "gear" icon along the path from START to END?
Required annotation format: set "annotation" to the [x0, y0, x1, y1] bounding box in image pixel coordinates for the selected answer icon.
Required answer format: set "answer" to the selected option letter as a string.
Example JSON:
{"annotation":[546,246,606,306],"answer":"E"}
```

### task_icons__named_path__path_neighbor_label / after_second_shape_label / answer_only / sample 2296233589938078

- `instance_seed`: `2296233589938078`
- `word_count`: `49`
- `body_word_count`: `33`

```text
The figure shows a START-to-END icon path with six option icons labeled A-F and other icons. Which labeled icon comes immediately after the second "gear" icon along the path from START to END?
Answer format: set "answer" to the selected option letter as a string.
Example JSON:
{"answer":"E"}
```

### task_icons__named_path__path_neighbor_label / before_first_shape_label / answer_and_annotation / sample 323946661420442

- `instance_seed`: `323946661420442`
- `word_count`: `81`
- `body_word_count`: `33`

```text
This image shows a START-to-END icon path with six option icons labeled A-F and other icons. Which labeled icon comes immediately before the first "bell" icon along the path from START to END?
Format for the "annotation" field: set "annotation" to the [x0, y0, x1, y1] bounding box in image pixel coordinates for the selected answer icon.
Format for the "answer" field: set "answer" to the selected option letter as a string.
Example JSON:
{"annotation":[546,246,606,306],"answer":"E"}
```

### task_icons__named_path__path_neighbor_label / before_first_shape_label / answer_only / sample 323946661420442

- `instance_seed`: `323946661420442`
- `word_count`: `50`
- `body_word_count`: `33`

```text
This image shows a START-to-END icon path with six option icons labeled A-F and other icons. Which labeled icon comes immediately before the first "bell" icon along the path from START to END?
Required answer format: set "answer" to the selected option letter as a string.
Example JSON:
{"answer":"E"}
```

### task_icons__named_path__path_neighbor_label / before_last_shape_label / answer_and_annotation / sample 7353624810392719

- `instance_seed`: `7353624810392719`
- `word_count`: `77`
- `body_word_count`: `34`

```text
The picture shows a START-to-END icon path with six option icons labeled A-F and other icons. Which labeled icon comes immediately before the last "soccer ball" icon along the path from START to END?
Final answer format: set "answer" to the selected option letter as a string.
Annotation format: set "annotation" to the [x0, y0, x1, y1] bounding box in image pixel coordinates for the selected answer icon.
Example JSON:
{"annotation":[546,246,606,306],"answer":"E"}
```

### task_icons__named_path__path_neighbor_label / before_last_shape_label / answer_only / sample 7353624810392719

- `instance_seed`: `7353624810392719`
- `word_count`: `51`
- `body_word_count`: `34`

```text
The picture shows a START-to-END icon path with six option icons labeled A-F and other icons. Which labeled icon comes immediately before the last "soccer ball" icon along the path from START to END?
Final answer format: set "answer" to the selected option letter as a string.
Example JSON:
{"answer":"E"}
```

### task_icons__named_path__path_neighbor_label / before_second_shape_label / answer_and_annotation / sample 3633305337063027

- `instance_seed`: `3633305337063027`
- `word_count`: `76`
- `body_word_count`: `33`

```text
This image shows a START-to-END icon path with six option icons labeled A-F and other icons. Which labeled icon comes immediately before the second "cloud" icon along the path from START to END?
Final answer format: set "answer" to the selected option letter as a string.
Annotation format: set "annotation" to the [x0, y0, x1, y1] bounding box in image pixel coordinates for the selected answer icon.
Example JSON:
{"annotation":[546,246,606,306],"answer":"E"}
```

### task_icons__named_path__path_neighbor_label / before_second_shape_label / answer_only / sample 3633305337063027

- `instance_seed`: `3633305337063027`
- `word_count`: `50`
- `body_word_count`: `33`

```text
This image shows a START-to-END icon path with six option icons labeled A-F and other icons. Which labeled icon comes immediately before the second "cloud" icon along the path from START to END?
Final answer format: set "answer" to the selected option letter as a string.
Example JSON:
{"answer":"E"}
```

### task_icons__named_ring__scoped_attribute_count / clockwise_arc_shape_count / answer_and_annotation / sample 4525877990387976

- `instance_seed`: `4525877990387976`
- `word_count`: `90`
- `body_word_count`: `33`

```text
The picture shows a ring of icons with endpoint markers A and B. Starting at marker A and moving clockwise to marker B, how many "triangle" icons are strictly between A and B?
Final answer format: set "answer" to the count as an integer.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every counted "triangle" icon strictly between A and B along the clockwise arc.
Example JSON:
{"annotation":[[176,168,236,228],[384,298,444,358]],"answer":2}
```

### task_icons__named_ring__scoped_attribute_count / clockwise_arc_shape_count / answer_only / sample 4525877990387976

- `instance_seed`: `4525877990387976`
- `word_count`: `50`
- `body_word_count`: `33`

```text
The picture shows a ring of icons with endpoint markers A and B. Starting at marker A and moving clockwise to marker B, how many "triangle" icons are strictly between A and B?
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_icons__named_ring__scoped_attribute_count / counterclockwise_arc_shape_count / answer_and_annotation / sample 6869640320475465

- `instance_seed`: `6869640320475465`
- `word_count`: `89`
- `body_word_count`: `33`

```text
The picture shows a ring of icons with endpoint markers A and B. Starting at marker A and moving counterclockwise to marker B, how many "car" icons are strictly between A and B?
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every counted "car" icon strictly between A and B along the counterclockwise arc.
Answer field: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[176,168,236,228],[384,298,444,358]],"answer":2}
```

### task_icons__named_ring__scoped_attribute_count / counterclockwise_arc_shape_count / answer_only / sample 6869640320475465

- `instance_seed`: `6869640320475465`
- `word_count`: `47`
- `body_word_count`: `33`

```text
The picture shows a ring of icons with endpoint markers A and B. Starting at marker A and moving counterclockwise to marker B, how many "car" icons are strictly between A and B?
Answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_icons__named_strip__shape_run_length / longest_shape_run_length / answer_and_annotation / sample 7033601339105322

- `instance_seed`: `7033601339105322`
- `word_count`: `78`
- `body_word_count`: `20`

```text
This image shows a horizontal row of boxed icons. What is the maximum length of a consecutive "acorn" icon run?
Required annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates for the icons in the run that determines the answer.
Required answer format: set "answer" to the run length as an integer.
Example JSON:
{"annotation":[[220,132,270,182],[292,132,342,182],[364,132,414,182]],"answer":3}
```

### task_icons__named_strip__shape_run_length / longest_shape_run_length / answer_only / sample 7033601339105322

- `instance_seed`: `7033601339105322`
- `word_count`: `35`
- `body_word_count`: `31`

```text
This image shows a horizontal row of boxed icons. What is the maximum length of a consecutive "acorn" icon run?
Answer field: set "answer" to the run length as an integer.
Example JSON:
{"answer":3}
```

### task_icons__named_strip__shape_run_length / shortest_shape_run_length / answer_and_annotation / sample 847493434050644

- `instance_seed`: `847493434050644`
- `word_count`: `77`
- `body_word_count`: `20`

```text
The image shows a horizontal row of boxed icons. Count the icons in the shortest consecutive block of "star" icons.
Final answer format: set "answer" to the run length as an integer.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates for the icons in the run that determines the answer.
Example JSON:
{"annotation":[[220,132,270,182],[292,132,342,182],[364,132,414,182]],"answer":3}
```

### task_icons__named_strip__shape_run_length / shortest_shape_run_length / answer_only / sample 847493434050644

- `instance_seed`: `847493434050644`
- `word_count`: `38`
- `body_word_count`: `20`

```text
The image shows a horizontal row of boxed icons. Count the icons in the shortest consecutive block of "star" icons.
Format for the "answer" field: set "answer" to the run length as an integer.
Example JSON:
{"answer":3}
```

### task_icons__overlap_grid__occlusion_order_count / single / answer_and_annotation / sample 553596173110781

- `instance_seed`: `553596173110781`
- `word_count`: `81`
- `body_word_count`: `29`

```text
The image shows a Reference cell beside a labeled Scene grid. How many labeled Scene cells match the Reference front-to-back order? Front-to-back order means which icon is on top.
Required annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates around all matching Scene cells.
Required answer format: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[336,104,506,274],[532,104,702,274],[728,104,898,274]],"answer":3}
```

### task_icons__overlap_grid__occlusion_order_count / single / answer_only / sample 553596173110781

- `instance_seed`: `553596173110781`
- `word_count`: `43`
- `body_word_count`: `39`

```text
The image shows a Reference cell beside a labeled Scene grid. How many labeled Scene cells match the Reference front-to-back order? Front-to-back order means which icon is on top.
Answer field: set "answer" to the count as an integer.
Example JSON:
{"answer":3}
```

### task_icons__pair_grid__reference_color_pair_match_label / single / answer_and_annotation / sample 2313902309684269

- `instance_seed`: `2313902309684269`
- `word_count`: `69`
- `body_word_count`: `26`

```text
The scene shows a Reference pair beside a labeled Scene grid. Which labeled Scene cell has the same left and right colors as the Reference pair?
Required annotation format: set "annotation" to one [x0, y0, x1, y1] box in image pixel coordinates around the selected Scene cell.
Required answer format: set "answer" to the selected option letter as a string.
Example JSON:
{"annotation":[336,104,506,274],"answer":"A"}
```

### task_icons__pair_grid__reference_color_pair_match_label / single / answer_only / sample 2313902309684269

- `instance_seed`: `2313902309684269`
- `word_count`: `42`
- `body_word_count`: `26`

```text
The scene shows a Reference pair beside a labeled Scene grid. Which labeled Scene cell has the same left and right colors as the Reference pair?
Answer format: set "answer" to the selected option letter as a string.
Example JSON:
{"answer":"A"}
```

### task_icons__pair_grid__reference_transform_match_label / single / answer_and_annotation / sample 7804392258731527

- `instance_seed`: `7804392258731527`
- `word_count`: `66`
- `body_word_count`: `24`

```text
The image shows a Reference pair beside a labeled Scene grid. Which labeled Scene cell shows the same before-to-after transformation as the Reference pair?
Final answer format: set "answer" to the selected option letter as a string.
Annotation format: set "annotation" to one [x0, y0, x1, y1] box in image pixel coordinates around the selected Scene cell.
Example JSON:
{"annotation":[336,104,506,274],"answer":"A"}
```

### task_icons__pair_grid__reference_transform_match_label / single / answer_only / sample 7804392258731527

- `instance_seed`: `7804392258731527`
- `word_count`: `43`
- `body_word_count`: `24`

```text
The image shows a Reference pair beside a labeled Scene grid. Which labeled Scene cell shows the same before-to-after transformation as the Reference pair?
Format for the "answer" field: set "answer" to the selected option letter as a string.
Example JSON:
{"answer":"A"}
```

### task_icons__paired_canvas__color_change_count / single / answer_and_annotation / sample 7478583881841186

- `instance_seed`: `7478583881841186`
- `word_count`: `83`
- `body_word_count`: `31`

```text
The picture shows two icon panels labeled Left and Right with corresponding icons at matching positions. How many Right-panel icons changed color compared with the corresponding icon in the Left panel?
Format for the "annotation" field: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates for every counted Right-panel icon.
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[620,156,684,220],[834,338,902,406]],"answer":2}
```

### task_icons__paired_canvas__color_change_count / single / answer_only / sample 7478583881841186

- `instance_seed`: `7478583881841186`
- `word_count`: `46`
- `body_word_count`: `31`

```text
The picture shows two icon panels labeled Left and Right with corresponding icons at matching positions. How many Right-panel icons changed color compared with the corresponding icon in the Left panel?
Final answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_icons__paired_canvas__panel_set_relation_count / added_in_right_count / answer_and_annotation / sample 7708997564796638

- `instance_seed`: `7708997564796638`
- `word_count`: `78`
- `body_word_count`: `28`

```text
This image shows two icon panels labeled Left and Right. How many Right-panel icons are new, meaning they do not exactly match any icon in the Left panel?
Final answer format: set "answer" to the count as an integer.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates for every counted icon in the relevant panel.
Example JSON:
{"annotation":[[620,156,684,220],[834,338,902,406]],"answer":2}
```

### task_icons__paired_canvas__panel_set_relation_count / added_in_right_count / answer_only / sample 7708997564796638

- `instance_seed`: `7708997564796638`
- `word_count`: `43`
- `body_word_count`: `28`

```text
This image shows two icon panels labeled Left and Right. How many Right-panel icons are new, meaning they do not exactly match any icon in the Left panel?
Required answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_icons__paired_canvas__panel_set_relation_count / missing_from_right_count / answer_and_annotation / sample 2597212154376201

- `instance_seed`: `2597212154376201`
- `word_count`: `70`
- `body_word_count`: `20`

```text
This image shows two icon panels labeled Left and Right. How many Left-panel icons are missing from the Right panel?
Final answer format: set "answer" to the count as an integer.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates for every counted icon in the relevant panel.
Example JSON:
{"annotation":[[620,156,684,220],[834,338,902,406]],"answer":2}
```

### task_icons__paired_canvas__panel_set_relation_count / missing_from_right_count / answer_only / sample 2597212154376201

- `instance_seed`: `2597212154376201`
- `word_count`: `35`
- `body_word_count`: `20`

```text
This image shows two icon panels labeled Left and Right. How many Left-panel icons are missing from the Right panel?
Required answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_icons__paired_canvas__rotation_change_count / single / answer_and_annotation / sample 3251322991150751

- `instance_seed`: `3251322991150751`
- `word_count`: `79`
- `body_word_count`: `31`

```text
This image shows two icon panels labeled Left and Right with corresponding icons at matching positions. How many Right-panel icons changed rotation compared with the corresponding icon in the Left panel?
Required annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates for every counted Right-panel icon.
Required answer format: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[620,156,684,220],[834,338,902,406]],"answer":2}
```

### task_icons__paired_canvas__rotation_change_count / single / answer_only / sample 3251322991150751

- `instance_seed`: `3251322991150751`
- `word_count`: `48`
- `body_word_count`: `31`

```text
This image shows two icon panels labeled Left and Right with corresponding icons at matching positions. How many Right-panel icons changed rotation compared with the corresponding icon in the Left panel?
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_icons__reference_canvas__anchor_position_count / above_anchor / answer_and_annotation / sample 4501170483339530

- `instance_seed`: `4501170483339530`
- `word_count`: `77`
- `body_word_count`: `28`

```text
The picture shows a Reference icon beside a Scene panel with one icon marked Anchor. Count the Scene icons with the Reference type that are above the Anchor.
Required annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every counted Scene icon.
Required answer format: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[322,152,377,207],[756,318,820,382]],"answer":2}
```

### task_icons__reference_canvas__anchor_position_count / above_anchor / answer_only / sample 4501170483339530

- `instance_seed`: `4501170483339530`
- `word_count`: `42`
- `body_word_count`: `28`

```text
The picture shows a Reference icon beside a Scene panel with one icon marked Anchor. Count the Scene icons with the Reference type that are above the Anchor.
Answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_icons__reference_canvas__anchor_position_count / below_anchor / answer_and_annotation / sample 5726129846258863

- `instance_seed`: `5726129846258863`
- `word_count`: `81`
- `body_word_count`: `28`

```text
The figure shows a Reference icon beside a Scene panel with one icon marked Anchor. How many Scene icons match the Reference type and are below the Anchor?
Format for the "annotation" field: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every counted Scene icon.
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[322,152,377,207],[756,318,820,382]],"answer":2}
```

### task_icons__reference_canvas__anchor_position_count / below_anchor / answer_only / sample 5726129846258863

- `instance_seed`: `5726129846258863`
- `word_count`: `45`
- `body_word_count`: `28`

```text
The figure shows a Reference icon beside a Scene panel with one icon marked Anchor. How many Scene icons match the Reference type and are below the Anchor?
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_icons__reference_canvas__anchor_position_count / left_of_anchor / answer_and_annotation / sample 4279521846268156

- `instance_seed`: `4279521846268156`
- `word_count`: `77`
- `body_word_count`: `29`

```text
The figure shows a Reference icon beside a Scene panel with one icon marked Anchor. What is the number of Reference-type Scene icons to the left of the Anchor?
Final answer format: set "answer" to the count as an integer.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every counted Scene icon.
Example JSON:
{"annotation":[[322,152,377,207],[756,318,820,382]],"answer":2}
```

### task_icons__reference_canvas__anchor_position_count / left_of_anchor / answer_only / sample 4279521846268156

- `instance_seed`: `4279521846268156`
- `word_count`: `43`
- `body_word_count`: `39`

```text
The figure shows a Reference icon beside a Scene panel with one icon marked Anchor. What is the number of Reference-type Scene icons to the left of the Anchor?
Answer field: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_icons__reference_canvas__anchor_position_count / right_of_anchor / answer_and_annotation / sample 1975253822837643

- `instance_seed`: `1975253822837643`
- `word_count`: `79`
- `body_word_count`: `31`

```text
The picture shows a Reference icon beside a Scene panel with one icon marked Anchor. How many Scene icons match the Reference type and are to the right of the Anchor?
Final answer format: set "answer" to the count as an integer.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every counted Scene icon.
Example JSON:
{"annotation":[[322,152,377,207],[756,318,820,382]],"answer":2}
```

### task_icons__reference_canvas__anchor_position_count / right_of_anchor / answer_only / sample 1975253822837643

- `instance_seed`: `1975253822837643`
- `word_count`: `46`
- `body_word_count`: `31`

```text
The picture shows a Reference icon beside a Scene panel with one icon marked Anchor. How many Scene icons match the Reference type and are to the right of the Anchor?
Required answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_icons__reference_canvas__reference_color_match_count / single / answer_and_annotation / sample 2472474435385550

- `instance_seed`: `2472474435385550`
- `word_count`: `73`
- `body_word_count`: `24`

```text
The scene shows a Reference icon beside a Scene panel. How many icons in the Scene panel have the same color as the Reference?
Required annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every counted Scene icon.
Required answer format: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[322,152,377,207],[756,318,820,382]],"answer":2}
```

### task_icons__reference_canvas__reference_color_match_count / single / answer_only / sample 2472474435385550

- `instance_seed`: `2472474435385550`
- `word_count`: `41`
- `body_word_count`: `24`

```text
The scene shows a Reference icon beside a Scene panel. How many icons in the Scene panel have the same color as the Reference?
Format for the "answer" field: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_icons__reference_canvas__reference_metric_relation_count / size_larger / answer_and_annotation / sample 4087781781497375

- `instance_seed`: `4087781781497375`
- `word_count`: `70`
- `body_word_count`: `21`

```text
The image shows a Reference icon beside a Scene panel. What is the number of Scene icons larger than the Reference?
Required annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every counted Scene icon.
Required answer format: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[322,152,377,207],[756,318,820,382]],"answer":2}
```

### task_icons__reference_canvas__reference_metric_relation_count / size_larger / answer_only / sample 4087781781497375

- `instance_seed`: `4087781781497375`
- `word_count`: `36`
- `body_word_count`: `21`

```text
The image shows a Reference icon beside a Scene panel. What is the number of Scene icons larger than the Reference?
Final answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_icons__reference_canvas__reference_metric_relation_count / size_smaller / answer_and_annotation / sample 7501835348025296

- `instance_seed`: `7501835348025296`
- `word_count`: `66`
- `body_word_count`: `19`

```text
The picture shows a Reference icon beside a Scene panel. How many Scene icons are smaller than the Reference?
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every counted Scene icon.
Answer format: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[322,152,377,207],[756,318,820,382]],"answer":2}
```

### task_icons__reference_canvas__reference_metric_relation_count / size_smaller / answer_only / sample 7501835348025296

- `instance_seed`: `7501835348025296`
- `word_count`: `34`
- `body_word_count`: `19`

```text
The picture shows a Reference icon beside a Scene panel. How many Scene icons are smaller than the Reference?
Required answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_icons__reference_canvas__reference_rotation_match_count / single / answer_and_annotation / sample 8646834620240576

- `instance_seed`: `8646834620240576`
- `word_count`: `65`
- `body_word_count`: `18`

```text
The picture shows a Reference icon beside a Scene panel. How many Scene icons match the Reference rotation?
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every counted Scene icon.
Answer format: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[322,152,377,207],[756,318,820,382]],"answer":2}
```

### task_icons__reference_canvas__reference_rotation_match_count / single / answer_only / sample 8646834620240576

- `instance_seed`: `8646834620240576`
- `word_count`: `32`
- `body_word_count`: `28`

```text
The picture shows a Reference icon beside a Scene panel. How many Scene icons match the Reference rotation?
Answer field: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_icons__reference_canvas__reference_type_color_rotation_match_count / single / answer_and_annotation / sample 7626473199769311

- `instance_seed`: `7626473199769311`
- `word_count`: `74`
- `body_word_count`: `27`

```text
This image shows a Reference icon beside a Scene panel. How many icons in the Scene panel have the same type, color, and rotation as the Reference?
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every counted Scene icon.
Answer field: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[322,152,377,207],[756,318,820,382]],"answer":2}
```

### task_icons__reference_canvas__reference_type_color_rotation_match_count / single / answer_only / sample 7626473199769311

- `instance_seed`: `7626473199769311`
- `word_count`: `42`
- `body_word_count`: `27`

```text
This image shows a Reference icon beside a Scene panel. How many icons in the Scene panel have the same type, color, and rotation as the Reference?
Required answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_icons__reference_canvas__reference_type_match_count / single / answer_and_annotation / sample 178224971473616

- `instance_seed`: `178224971473616`
- `word_count`: `67`
- `body_word_count`: `18`

```text
The picture shows a Reference icon beside a Scene panel. How many Scene icons match the Reference type?
Required annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] bounding boxes in image pixel coordinates for every counted Scene icon.
Required answer format: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[322,152,377,207],[756,318,820,382]],"answer":2}
```

### task_icons__reference_canvas__reference_type_match_count / single / answer_only / sample 178224971473616

- `instance_seed`: `178224971473616`
- `word_count`: `33`
- `body_word_count`: `18`

```text
The picture shows a Reference icon beside a Scene panel. How many Scene icons match the Reference type?
Required answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_icons__sequence_strip__count_progression_completion_label / single / answer_and_annotation / sample 2377184592106086

- `instance_seed`: `2377184592106086`
- `word_count`: `84`
- `body_word_count`: `34`

```text
The picture shows a top row of four boxed sequence cells with one question-mark box and a bottom row of four labeled option boxes. Which option completes the icon-count sequence in the question-mark box?
Required annotation format: set "annotation" to one [x0, y0, x1, y1] box in image pixel coordinates for the correct option box.
Required answer format: set "answer" to the correct option label as a string, one of "A", "B", "C", or "D".
Example JSON:
{"annotation":[412,250,540,398],"answer":"C"}
```

### task_icons__sequence_strip__count_progression_completion_label / single / answer_only / sample 2377184592106086

- `instance_seed`: `2377184592106086`
- `word_count`: `57`
- `body_word_count`: `53`

```text
The picture shows a top row of four boxed sequence cells with one question-mark box and a bottom row of four labeled option boxes. Which option completes the icon-count sequence in the question-mark box?
Answer field: set "answer" to the correct option label as a string, one of "A", "B", "C", or "D".
Example JSON:
{"answer":"C"}
```

### task_icons__sequence_strip__rotation_progression_completion_label / single / answer_and_annotation / sample 7153695796642113

- `instance_seed`: `7153695796642113`
- `word_count`: `84`
- `body_word_count`: `34`

```text
This image shows a top row of four boxed sequence cells with one question-mark box and a bottom row of four labeled option boxes. Which option completes the rotation sequence in the question-mark box?
Required annotation format: set "annotation" to one [x0, y0, x1, y1] box in image pixel coordinates for the correct option box.
Required answer format: set "answer" to the correct option label as a string, one of "A", "B", "C", or "D".
Example JSON:
{"annotation":[412,250,540,398],"answer":"C"}
```

### task_icons__sequence_strip__rotation_progression_completion_label / single / answer_only / sample 7153695796642113

- `instance_seed`: `7153695796642113`
- `word_count`: `58`
- `body_word_count`: `34`

```text
This image shows a top row of four boxed sequence cells with one question-mark box and a bottom row of four labeled option boxes. Which option completes the rotation sequence in the question-mark box?
Final answer format: set "answer" to the correct option label as a string, one of "A", "B", "C", or "D".
Example JSON:
{"answer":"C"}
```

### task_icons__sequence_strip__size_progression_completion_label / single / answer_and_annotation / sample 5247823446222219

- `instance_seed`: `5247823446222219`
- `word_count`: `83`
- `body_word_count`: `35`

```text
This image shows a top row of four boxed sequence cells with one question-mark box and a bottom row of four labeled option boxes. Which option has the icon size needed to complete the sequence?
Annotation format: set "annotation" to one [x0, y0, x1, y1] box in image pixel coordinates for the correct option box.
Answer format: set "answer" to the correct option label as a string, one of "A", "B", "C", or "D".
Example JSON:
{"annotation":[412,250,540,398],"answer":"C"}
```

### task_icons__sequence_strip__size_progression_completion_label / single / answer_only / sample 5247823446222219

- `instance_seed`: `5247823446222219`
- `word_count`: `58`
- `body_word_count`: `54`

```text
This image shows a top row of four boxed sequence cells with one question-mark box and a bottom row of four labeled option boxes. Which option has the icon size needed to complete the sequence?
Answer field: set "answer" to the correct option label as a string, one of "A", "B", "C", or "D".
Example JSON:
{"answer":"C"}
```

### task_icons__single_transform_options__geometric_transform_result_label / flip_horizontal_result_label / answer_and_annotation / sample 474308002447364

- `instance_seed`: `474308002447364`
- `word_count`: `80`
- `body_word_count`: `26`

```text
The figure shows a Reference icon with a transform cue and six labeled option icons. Which labeled option shows the Reference icon after a horizontal flip?
Format for the "annotation" field: set "annotation" to a JSON object with keys "reference_icon" and "selected_option", each a [x0, y0, x1, y1] box in image pixel coordinates.
Format for the "answer" field: set "answer" to the selected option letter.
Example JSON:
{"annotation":{"reference_icon":[82,144,250,312],"selected_option":[532,104,702,274]},"answer":"C"}
```

### task_icons__single_transform_options__geometric_transform_result_label / flip_horizontal_result_label / answer_only / sample 474308002447364

- `instance_seed`: `474308002447364`
- `word_count`: `39`
- `body_word_count`: `26`

```text
The figure shows a Reference icon with a transform cue and six labeled option icons. Which labeled option shows the Reference icon after a horizontal flip?
Answer format: set "answer" to the selected option letter.
Example JSON:
{"answer":"C"}
```

### task_icons__single_transform_options__geometric_transform_result_label / flip_vertical_result_label / answer_and_annotation / sample 1029263523659324

- `instance_seed`: `1029263523659324`
- `word_count`: `75`
- `body_word_count`: `27`

```text
The figure shows a Reference icon with a transform cue and six labeled option icons. Select the option that matches a vertical flip of the Reference icon.
Annotation format: set "annotation" to a JSON object with keys "reference_icon" and "selected_option", each a [x0, y0, x1, y1] box in image pixel coordinates.
Answer format: set "answer" to the selected option letter.
Example JSON:
{"annotation":{"reference_icon":[82,144,250,312],"selected_option":[532,104,702,274]},"answer":"C"}
```

### task_icons__single_transform_options__geometric_transform_result_label / flip_vertical_result_label / answer_only / sample 1029263523659324

- `instance_seed`: `1029263523659324`
- `word_count`: `40`
- `body_word_count`: `27`

```text
The figure shows a Reference icon with a transform cue and six labeled option icons. Select the option that matches a vertical flip of the Reference icon.
Answer format: set "answer" to the selected option letter.
Example JSON:
{"answer":"C"}
```

### task_icons__single_transform_options__geometric_transform_result_label / rotate_180_result_label / answer_and_annotation / sample 4387994724023287

- `instance_seed`: `4387994724023287`
- `word_count`: `83`
- `body_word_count`: `29`

```text
The scene shows a Reference icon with a transform cue and six labeled option icons. Find the labeled option that shows the Reference icon after rotating it 180 degrees.
Format for the "annotation" field: set "annotation" to a JSON object with keys "reference_icon" and "selected_option", each a [x0, y0, x1, y1] box in image pixel coordinates.
Format for the "answer" field: set "answer" to the selected option letter.
Example JSON:
{"annotation":{"reference_icon":[82,144,250,312],"selected_option":[532,104,702,274]},"answer":"C"}
```

### task_icons__single_transform_options__geometric_transform_result_label / rotate_180_result_label / answer_only / sample 4387994724023287

- `instance_seed`: `4387994724023287`
- `word_count`: `42`
- `body_word_count`: `29`

```text
The scene shows a Reference icon with a transform cue and six labeled option icons. Find the labeled option that shows the Reference icon after rotating it 180 degrees.
Answer format: set "answer" to the selected option letter.
Example JSON:
{"answer":"C"}
```

### task_icons__single_transform_options__geometric_transform_result_label / rotate_90_clockwise_result_label / answer_and_annotation / sample 5476346005978608

- `instance_seed`: `5476346005978608`
- `word_count`: `82`
- `body_word_count`: `28`

```text
The scene shows a Reference icon with a transform cue and six labeled option icons. Which labeled option shows the Reference icon after a 90 degree clockwise rotation?
Format for the "annotation" field: set "annotation" to a JSON object with keys "reference_icon" and "selected_option", each a [x0, y0, x1, y1] box in image pixel coordinates.
Format for the "answer" field: set "answer" to the selected option letter.
Example JSON:
{"annotation":{"reference_icon":[82,144,250,312],"selected_option":[532,104,702,274]},"answer":"C"}
```

### task_icons__single_transform_options__geometric_transform_result_label / rotate_90_clockwise_result_label / answer_only / sample 5476346005978608

- `instance_seed`: `5476346005978608`
- `word_count`: `41`
- `body_word_count`: `28`

```text
The scene shows a Reference icon with a transform cue and six labeled option icons. Which labeled option shows the Reference icon after a 90 degree clockwise rotation?
Answer format: set "answer" to the selected option letter.
Example JSON:
{"answer":"C"}
```

### task_icons__single_transform_options__geometric_transform_result_label / rotate_90_counterclockwise_result_label / answer_and_annotation / sample 5114016568751050

- `instance_seed`: `5114016568751050`
- `word_count`: `78`
- `body_word_count`: `30`

```text
The picture shows a Reference icon with a transform cue and six labeled option icons. Find the labeled option that shows the Reference icon after rotating it 90 degrees counterclockwise.
Annotation format: set "annotation" to a JSON object with keys "reference_icon" and "selected_option", each a [x0, y0, x1, y1] box in image pixel coordinates.
Answer field: set "answer" to the selected option letter.
Example JSON:
{"annotation":{"reference_icon":[82,144,250,312],"selected_option":[532,104,702,274]},"answer":"C"}
```

### task_icons__single_transform_options__geometric_transform_result_label / rotate_90_counterclockwise_result_label / answer_only / sample 5114016568751050

- `instance_seed`: `5114016568751050`
- `word_count`: `46`
- `body_word_count`: `30`

```text
The picture shows a Reference icon with a transform cue and six labeled option icons. Find the labeled option that shows the Reference icon after rotating it 90 degrees counterclockwise.
Format for the "answer" field: set "answer" to the selected option letter.
Example JSON:
{"answer":"C"}
```

### task_icons__venn_field__scoped_attribute_count / inside_both_circles_count / answer_and_annotation / sample 6527654714005800

- `instance_seed`: `6527654714005800`
- `word_count`: `75`
- `body_word_count`: `28`

```text
The image shows a panel of icons and two overlapping marked circles. How many cyan [#34C4E0] "cloud" icons have centers in the shared region of the marked circles?
Final answer format: set "answer" to the count as an integer.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates for every counted target icon.
Example JSON:
{"annotation":[[116,128,168,180],[634,302,686,354]],"answer":2}
```

### task_icons__venn_field__scoped_attribute_count / inside_both_circles_count / answer_only / sample 6527654714005800

- `instance_seed`: `6527654714005800`
- `word_count`: `42`
- `body_word_count`: `38`

```text
The image shows a panel of icons and two overlapping marked circles. How many cyan [#34C4E0] "cloud" icons have centers in the shared region of the marked circles?
Answer field: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_icons__venn_field__scoped_attribute_count / inside_either_circle_count / answer_and_annotation / sample 4642504592202265

- `instance_seed`: `4642504592202265`
- `word_count`: `71`
- `body_word_count`: `25`

```text
This image shows icons arranged around two overlapping marked circles. Find the number of blue [#2D75E6] "spoon" icons with centers inside at least one circle.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates for every counted target icon.
Answer field: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[116,128,168,180],[634,302,686,354]],"answer":2}
```

### task_icons__venn_field__scoped_attribute_count / inside_either_circle_count / answer_only / sample 4642504592202265

- `instance_seed`: `4642504592202265`
- `word_count`: `40`
- `body_word_count`: `25`

```text
This image shows icons arranged around two overlapping marked circles. Find the number of blue [#2D75E6] "spoon" icons with centers inside at least one circle.
Final answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_icons__venn_field__scoped_attribute_count / inside_exactly_one_circle_count / answer_and_annotation / sample 4578230396005133

- `instance_seed`: `4578230396005133`
- `word_count`: `73`
- `body_word_count`: `26`

```text
The figure shows a panel of icons with two overlapping marked circles. Find the number of brown [#887044] "egg" icons with centers in only one circle.
Final answer format: set "answer" to the count as an integer.
Annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates for every counted target icon.
Example JSON:
{"annotation":[[116,128,168,180],[634,302,686,354]],"answer":2}
```

### task_icons__venn_field__scoped_attribute_count / inside_exactly_one_circle_count / answer_only / sample 4578230396005133

- `instance_seed`: `4578230396005133`
- `word_count`: `40`
- `body_word_count`: `36`

```text
The figure shows a panel of icons with two overlapping marked circles. Find the number of brown [#887044] "egg" icons with centers in only one circle.
Answer field: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_icons__venn_field__scoped_attribute_count / outside_both_circles_count / answer_and_annotation / sample 3321587919451593

- `instance_seed`: `3321587919451593`
- `word_count`: `72`
- `body_word_count`: `24`

```text
The image shows a panel of icons and two overlapping marked circles. How many brown [#887044] "tree" icons have centers in neither marked circle?
Required annotation format: set "annotation" to a JSON array of [x0, y0, x1, y1] boxes in image pixel coordinates for every counted target icon.
Required answer format: set "answer" to the count as an integer.
Example JSON:
{"annotation":[[116,128,168,180],[634,302,686,354]],"answer":2}
```

### task_icons__venn_field__scoped_attribute_count / outside_both_circles_count / answer_only / sample 3321587919451593

- `instance_seed`: `3321587919451593`
- `word_count`: `38`
- `body_word_count`: `24`

```text
The image shows a panel of icons and two overlapping marked circles. How many brown [#887044] "tree" icons have centers in neither marked circle?
Answer format: set "answer" to the count as an integer.
Example JSON:
{"answer":2}
```

### task_icons__wallpaper_panels__motif_violation_label / single / answer_and_annotation / sample 871873066030903

- `instance_seed`: `871873066030903`
- `word_count`: `64`
- `body_word_count`: `26`

```text
The figure shows four labeled wallpaper panels filled with repeated icon motifs. Select the labeled wallpaper panel that has a different wallpaper pattern from the rest.
Annotation format: set "annotation" to one [x0, y0, x1, y1] box in image pixel coordinates for the selected wallpaper panel.
Answer format: set "answer" to the selected panel letter.
Example JSON:
{"annotation":[420,220,620,400],"answer":"C"}
```

### task_icons__wallpaper_panels__motif_violation_label / single / answer_only / sample 871873066030903

- `instance_seed`: `871873066030903`
- `word_count`: `42`
- `body_word_count`: `26`

```text
The figure shows four labeled wallpaper panels filled with repeated icon motifs. Select the labeled wallpaper panel that has a different wallpaper pattern from the rest.
Format for the "answer" field: set "answer" to the selected panel letter.
Example JSON:
{"answer":"C"}
```

### task_icons__wallpaper_panels__same_pattern_as_reference_label / single / answer_and_annotation / sample 4792880301869547

- `instance_seed`: `4792880301869547`
- `word_count`: `78`
- `body_word_count`: `28`

```text
The scene shows one Reference wallpaper panel above four labeled wallpaper panels filled with repeated icon motifs. Find the labeled wallpaper panel that matches the Reference panel's pattern.
Annotation format: set "annotation" to a JSON object with keys "reference_panel" and "selected_panel", each mapped to one [x0, y0, x1, y1] box in image pixel coordinates.
Answer field: set "answer" to the selected panel letter.
Example JSON:
{"annotation":{"reference_panel":[36,36,320,604],"selected_panel":[420,220,620,400]},"answer":"C"}
```

### task_icons__wallpaper_panels__same_pattern_as_reference_label / single / answer_only / sample 4792880301869547

- `instance_seed`: `4792880301869547`
- `word_count`: `41`
- `body_word_count`: `37`

```text
The scene shows one Reference wallpaper panel above four labeled wallpaper panels filled with repeated icon motifs. Find the labeled wallpaper panel that matches the Reference panel's pattern.
Answer field: set "answer" to the selected panel letter.
Example JSON:
{"answer":"C"}
```

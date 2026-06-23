# `task_icons__paired_canvas__panel_attribute_change_count`

## 1) Identity
1. Domain: `icons`
2. Scene id: `paired_canvas`
3. Scene package: `paired_canvas`
4. Task id: `task_icons__paired_canvas__panel_attribute_change_count`
5. Objective: count Right-panel icons whose queried attribute changed from the corresponding Left-panel icon.

## Program Contract
`count.pairwise_comparison(scene=paired_canvas, scope=aligned_left_right_icon_pairs, predicate=changed_color|changed_rotation, output=count)`

## 2) Scene + task contract
1. Entities/relations: two large icon panels labeled `Left` and `Right`; corresponding icons appear at matching relative positions.
2. Branch metadata: `query_id`
3. Query ids: `color_changed_count`, `rotation_changed_count`.
4. Answer type: `answer_gt.type = integer`.
5. Annotation type: `annotation_gt.type = bbox_set` over every counted Right-panel icon.
   `projected_annotation` mirrors this as typed bbox-set annotation with
   `bbox_set`, `pixel_bbox_set`, and bbox-center `pixel_point_set`.
6. Unique-answer policy: only target pairs change the queried attribute; distractors either do not change or change a different attribute.
7. Scalar annotation checked: not applicable. The count can have zero or multiple visual witnesses, so `bbox_set` is the stable annotation schema.

## 3) Prompt contract
1. `prompt_bundle_id`: `icons_paired_canvas_v0`
2. `scene_key`: `paired_canvas_attribute_change`
3. `task_key`: `paired_canvas_query`
4. Answer+annotation JSON shape: `{"annotation":[[620,156,684,220],[834,338,902,406]],"answer":2}`
5. Prompt wording specifies whether color or rotation is queried.

## 4) Determinism + constraints
1. The per-pair changed attributes are recorded in trace metadata.
2. Annotation is computed from the Right-panel icons whose queried attribute changed.
3. Generation fails rather than relaxing correspondence, attribute-change, or placement constraints.
4. Render metadata records panel-title text legibility.

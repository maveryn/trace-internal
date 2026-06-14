# `task_icons__paired_canvas__panel_movement_direction_count`

## 1) Identity
1. Domain: `icons`
2. Scene id: `paired_canvas`
3. Scene package: `paired_canvas`
4. Task id: `task_icons__paired_canvas__panel_movement_direction_count`
5. Objective: count icons that moved in the requested direction from the Left panel to the Right panel.

## 2) Scene + task contract
1. Entities/relations: two large icon panels labeled `Left` and `Right`; the same icon identities appear in both panels with changed positions.
2. Branch metadata: `query_id`
3. Query id: `moved_left_count|moved_right_count|moved_up_count|moved_down_count`.
4. Answer type: `answer_gt.type = integer`.
5. Annotation type: `annotation_gt.type = bbox_set` over every counted Right-panel destination icon.
   `projected_annotation` mirrors this as typed bbox-set annotation with
   `bbox_set`, `pixel_bbox_set`, and bbox-center `pixel_point_set`.
6. Unique-answer policy: target pairs move in the queried direction; distractor pairs move in other cardinal directions with a configured minimum displacement.

## 3) Prompt contract
1. `prompt_bundle_id`: `icons_paired_canvas_v0`
2. `scene_key`: `paired_canvas_movement_direction`
3. `task_key`: `paired_canvas_query`
4. Answer+annotation JSON shape: `{"annotation":[[620,156,684,220],[834,338,902,406]],"answer":2}`
5. Prompt wording specifies the active movement direction.

## 4) Determinism + constraints
1. The movement direction for each pair is recorded in trace metadata.
2. Annotation is computed from the Right-panel destination icons for target pairs.
3. Generation fails rather than relaxing movement-direction, correspondence, or placement constraints.
4. Render metadata records panel-title text legibility.

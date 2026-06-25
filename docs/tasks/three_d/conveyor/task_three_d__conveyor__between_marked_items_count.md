# `task_three_d__conveyor__between_marked_items_count`

## Summary
- Domain: `three_d`
- Scene id: `conveyor`
- Scene package: `conveyor`
- Query ids: `between_color_anchors_count`, `between_object_anchors_count`
- Answer type: `integer`
- Annotation type: `bbox_set`
- Annotation schema: `bbox_set`

## Program Contract
- `count(lane_sequence[target_lane_key][j] for start_anchor_index < j < end_anchor_index); scene=conveyor; scope=between_marked_items_count`
- `count(lane_sequence[target_lane_key][j] for start_anchor_index < j < end_anchor_index); scene=conveyor; scope=between_marked_items_count`

## Contract
The image shows one straight 3D conveyor scene with three visible parallel
lanes. Landscape canvases use `TOP`, `MIDDLE`, and `BOTTOM` lane positions.
Portrait canvases use `LEFT`, `MIDDLE`, and `RIGHT` lane positions. Square
canvases may use either orientation.

The task selects one lane and marks two anchor objects on that lane with red
boxes and labels `A` and `B`. The answer is the number of objects strictly
between the two marked anchor objects on the selected lane. The marked anchor
objects are excluded from the count.

For `between_color_anchors_count`, anchor descriptions in the prompt use the
anchor color labels. For `between_object_anchors_count`, anchor descriptions
use the anchor object names. The program is otherwise the same; the query id
branch only changes the prompt-facing anchor descriptor.

Answer support is `1..5`. Each lane contains at most 8 objects for this task.

## Annotation Contract
Annotation is a `bbox_set`. Each box marks one counted object strictly between
the marked anchors. The marked anchor objects, marker boxes, labels, belt
surfaces, arrows, and decorative context are not annotation.

## Prompt And Trace
The prompt bundle is `three_d_conveyor_v1` under
`prompts/three_d/conveyor/`. Named color prompts use the canonical repo-wide
color format, such as `blue [#2D75E6]`.

The trace records scene variant, lane orientation, selected lane key, marked
anchor object ids, anchor labels, lane object sequence, counted between-object
ids, object specs, projected object boxes and centers, camera, projection
frame, and solver count predicate.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config
defaults, prompt bundle, and code versions. Answers and annotation come from
the same finalized conveyor trace.

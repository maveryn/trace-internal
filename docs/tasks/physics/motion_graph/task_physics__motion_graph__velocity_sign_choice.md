# `task_physics__motion_graph__velocity_sign_choice`

## Summary
- Domain: `physics`
- Scene id: `motion_graph`
- Implementation scene: `mechanics`
- Implementation source: `trace/tasks/physics/mechanics/motion_graph.py`

## Task Contract
Chooses the velocity-sign motion state represented by a marked interval on a position-time graph.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `velocity_sign_choice` | `option_letter(classify_velocity_sign(marked_x_t_segment)); scene=motion_graph; scope=velocity_sign_choice` |

## Program Metadata
- Program signatures: `physics.motion_graph_velocity_sign_choice`
- Base program contract: `option_letter(classify_velocity_sign(marked_position_time_graph_interval)); scene=motion_graph; scope=velocity_sign_choice`
- Parameter axes: `scene_variant`, `motion_state`, `correct_option_letter`
- Arguments:
  - `marked_position_time_graph_interval`: semantic_role; allowed `highlighted_time_interval_with_local_position_curve_segment`; source `program_schema_concrete`
  - `motion_state`: query_operand; allowed `moving_right|moving_left|stationary`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `velocity_sign_choice`

## Answer Contract
- Answer schema: `option_letter`
- Generator `answer_gt.type`: `option_letter`
- The answer value is the letter of the visible option describing whether the object is moving right, moving left, or stationary over the marked interval.

## Annotation Contract
- Annotation schema: `keyed_bbox_map`
- Generator `annotation_gt.type`: `keyed_bbox_map`
- Annotation keys are `query_region` and `curve_segment`.
- Annotation must mark minimal visual witnesses from the final rendered diagram: the highlighted time interval and the local position-time graph segment used to infer velocity sign. Annotation must not mark axes, tick labels, option boxes, option letters, or decorative graph chrome.
- Annotation and answer must be projected from the same generated execution trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the physics prompt bundles, with scene and task/query layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, marked interval, curve values, option mapping, and verifier payloads must be explicit in the instance trace.
- Diagrams must keep the axis labels, marked interval, local segment, and visual option boxes readable.

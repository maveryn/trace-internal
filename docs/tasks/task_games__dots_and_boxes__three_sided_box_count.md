# `task_games__dots_and_boxes__three_sided_box_count`

## Contract
1. Domain: `games`
2. Scene id: `dots_and_boxes`
3. Source task group: `dots_and_boxes`
4. Query id: `three_sided_box_count`
5. Objective: Count boxes that currently have exactly three drawn sides.

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: bbox_set over three-sided boxes.
3. `three_sided_box_count` is retained as `query_id`; `query_spec.params.query_id` is internal replay diagnostics.

## Implementation
1. This task uses the shared games scene renderer for its scene id.
2. Prompt bundle: `games_dots_and_boxes_v0`
## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Semantic mirror knobs such as player color, board size, axis, direction, style, and target-answer support remain explicit params inside the task.

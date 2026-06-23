# `task_icons__sequence_strip__missing_count_value`

## Program Contract
`numeric.sequence_completion_value(scene=sequence_strip, scope=horizontal_box_sequence, rule=arithmetic_progression, missing_role=question_mark_box, output=missing_count)`

## Identity
- domain: `icons`
- scene_id: `sequence_strip`
- module: `trace/tasks/icons/sequence_strip/missing_count_value.py`
- prompt bundle: `icons_sequence_strip_v1`

## Contract
- The image shows a horizontal row of boxed icon groups.
- Exactly one box is marked with a question mark and contains no icons.
- Visible counts and the hidden count follow one integer arithmetic progression.
- Supported `query_id` values: `single`.
- Answer schema: integer missing icon count.
- Annotation schema: scalar `bbox`, the question-mark box in final image pixel coordinates.

## Generation
- Sequence length support: `4..6`.
- Missing count support: `0..10`.
- Arithmetic step delta support: `-2, -1, 0, 1, 2`.
- The missing position can be any row position when feasible, including row ends.
- All visible icons use one curated icon type and one tint; rotations may vary.
- Generation rejects infeasible arithmetic sequences or failed in-cell placement.

## Prompt
- Scene key: `sequence_strip`.
- Task key: `sequence_strip_query`.
- Query key: `missing_count_value`.
- Answer+annotation JSON example: `{"annotation":[540,126,654,458],"answer":5}`.
- Answer-only JSON example: `{"answer":5}`.

## Tests
- `tests/test_icons_sequence_missing_count_tasks.py`
- `tests/test_icons_sequence_missing_count_contracts.py`
- `tests/test_icons_scene_config.py`

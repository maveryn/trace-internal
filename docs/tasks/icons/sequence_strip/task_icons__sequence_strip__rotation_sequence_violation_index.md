# `task_icons__sequence_strip__rotation_sequence_violation_index`

## Program Contract
`selection.rule_violation(scene=sequence_strip, scope=horizontal_numbered_box_sequence, rule=constant_rotation_step, candidate=numbered_box, output=violating_index)`

## Identity
- domain: `icons`
- scene_id: `sequence_strip`
- module: `trace/tasks/icons/sequence_strip/rotation_sequence_violation_index.py`
- prompt bundle: `icons_sequence_strip_v1`

## Contract
- The image shows a horizontal row of numbered boxes, each containing one icon.
- The row is intended to follow one constant rotation step.
- Exactly one numbered box is corrupted so its icon rotation breaks the rule.
- Supported `query_id` values: `single`.
- Answer schema: integer 1-based violating box index.
- Annotation schema: scalar `bbox`, the violating numbered box in final image pixel coordinates.

## Generation
- Default sequence length is `10`.
- Answer support is `2..6` so there is visible context before and after the violation.
- Rotation candidates are `{0, 90, 180, 270}`.
- Step candidates are `{90, 180}`.
- The task uses the asymmetric curated icon subset so orientation is visually meaningful.
- Generation rejects ambiguous rows where another supported rotation rule would imply a different single violating box.

## Prompt
- Scene key: `sequence_strip`.
- Task key: `sequence_strip_query`.
- Query key: `rotation_sequence_violation_index`.
- Answer+annotation JSON example: `{"annotation":[540,126,654,458],"answer":5}`.
- Answer-only JSON example: `{"answer":5}`.

## Tests
- `tests/test_icons_pattern_structured_violation_tasks.py`
- `tests/test_icons_pattern_structured_violation_contracts.py`
- `tests/test_icons_scene_config.py`

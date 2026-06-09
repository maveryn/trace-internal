# `task_puzzles__balance_scale__weight_order_label`

## Contract
1. Domain: `puzzles`
2. Scene id: `balance_scale`
3. Source implementation domain/group: `puzzles/logic`
4. Task id: `task_puzzles__balance_scale__weight_order_label`
5. Objective contract: weight order label.
6. Supported sampled `query_id`: `heaviest_object_label`, `lightest_object_label`
7. `answer_gt.type`: `string`
8. `annotation_gt.type`: `keyed_bbox_map`
9. Annotation policy: minimal role-bound witnesses for the comparison scales and the selected candidate object.

## Implementation
1. Registered class: `trace.tasks.puzzles.logic.balance_scale.PuzzlesLogicWeightOrderLabelTask`
2. Prompt lookup domain/group: `puzzles/logic`
3. Prompt bundle: `puzzles_logic_v0`
4. Scene variants: `balance_sheet`, `balance_card`, `balance_outline`
5. Target cue mode: `query_row_only`

## Notes
1. Visible comparison panels are tilted by construction.
2. The lower pan is the heavier side and the higher pan is the lighter side.
3. The generator constructs a strict object-weight order and verifies that the requested heaviest or lightest label is uniquely determined from the comparisons.
4. Numeric weights are not shown for this task.

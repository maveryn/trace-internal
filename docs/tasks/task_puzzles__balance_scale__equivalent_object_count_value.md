# `task_puzzles__balance_scale__equivalent_object_count_value`

## Contract
1. Domain: `puzzles`
2. Scene id: `balance_scale`
3. Source implementation domain/group: `puzzles/logic`
4. Task id: `task_puzzles__balance_scale__equivalent_object_count_value`
5. Objective contract: equivalent object count value.
6. Supported sampled `query_id`: `equivalent_object_count_value`
7. `answer_gt.type`: `integer`
8. `annotation_gt.type`: `keyed_bbox_map`
9. Annotation policy: minimal role-bound witnesses for the source object, repeated object, and missing-count box in the query row.

## Implementation
1. Registered class: `trace.tasks.puzzles.logic.balance_scale.PuzzlesLogicEquivalentObjectCountValueTask`
2. Prompt lookup domain/group: `puzzles/logic`
3. Prompt bundle: `puzzles_logic_v0`
4. Scene variants: `balance_sheet`, `balance_card`, `balance_outline`
5. Target cue modes: `query_row_only`, `query_row_and_highlight`

## Notes
1. Every visible scale panel is balanced by construction.
2. The target answer is sampled from `2..8`.
3. The generator verifies that the equivalent-object count is uniquely determined over the configured count support before rendering.
4. Supporting scale equations remain in trace metadata; prompt-facing annotation stays on `source_object`, `missing_count_box`, and `repeated_object`.

# `task_puzzles__arithmetic_constraint__letter_digit_value`

## Contract
1. Domain: `puzzles`
2. Scene id: `arithmetic_constraint`
3. Source implementation domain/group: `puzzles/logic`
4. Task id: `task_puzzles__arithmetic_constraint__letter_digit_value`
5. Objective contract: letter digit value.
6. Supported sampled `query_id`: `letter_digit_value`
7. `answer_gt.type`: `integer`
8. `annotation_gt.type`: `bbox_set`
9. Annotation policy: minimal visual witnesses for the visible objects, cells, panels, or role-keyed components needed to solve the task.

## Implementation
1. Registered class: `trace.tasks.puzzles.logic.arithmetic_constraint.PuzzlesLogicLetterDigitValueTask`
2. Prompt lookup domain/group: `puzzles/logic`
3. Prompt bundle: `see trace prompt metadata`
4. Example sampled scene variant: `constraint_sheet`

## Notes
2. Generation must remain deterministic from explicit seeds, params, prompt bundle, renderer config, and code versions.
3. Answers and annotation must come from the same metadata execution trace.

# `task_puzzles__arithmetic_constraint__cryptarithm_digit_value`

## Contract
1. Domain: `puzzles`
2. Scene id: `arithmetic_constraint`
3. Source implementation domain/group: `puzzles/logic`
4. Query id: sampled from `hidden_addition_digit_value`, `hidden_subtraction_digit_value`, `letter_digit_value`
5. Public `query_variant` is `default`; semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.puzzles.logic.arithmetic_constraint.PuzzlesLogicCryptarithmDigitValueTask`
2. Prompt lookup domain/group: `puzzles/logic`
3. Prompt bundle: `puzzles_logic_v0`
4. Scene variants: `constraint_sheet`, `constraint_card`, `constraint_outline`
5. The scene shows one compact arithmetic puzzle with a question-mark digit or highlighted target letter.
6. Structural variation is sampled per instance:
   - vertical addition/subtraction varies digit width and, for addition, addend count,
   - letter-digit puzzles vary the number of displayed letters and the number of displayed equations.
7. `answer_gt.type`: `integer`
8. `evidence_gt.type`: `bbox_set` over the puzzle panel and the marked digit/letter cell.
9. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
10. Answers and evidence are produced from the same metadata execution trace.

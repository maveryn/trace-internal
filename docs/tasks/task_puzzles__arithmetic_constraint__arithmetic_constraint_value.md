# `task_puzzles__arithmetic_constraint__arithmetic_constraint_value`

## Contract
1. Domain: `puzzles`
2. Scene id: `arithmetic_constraint`
3. Source implementation domain/group: `puzzles/logic`
4. Query id: sampled from `equal_sum_line_constraint_value`, `paired_cluster_sum_relation_value`, `consecutive_window_sum_value`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.puzzles.logic.arithmetic_constraint.PuzzlesLogicArithmeticConstraintValueTask`
2. Prompt lookup domain/group: `puzzles/logic`
3. Prompt bundle: `puzzles_logic_v0`
4. Scene variants: `constraint_sheet`, `constraint_card`, `constraint_outline`
5. The scene shows a compact arithmetic-constraint puzzle with numbered shapes or cells, visible relation/rule text, and one marked question target.
6. `answer_gt.type`: `integer`
7. `evidence_gt.type`: `bbox_set` over the marked target node/cell only.
8. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
9. Answers and evidence are produced from the same metadata execution trace.

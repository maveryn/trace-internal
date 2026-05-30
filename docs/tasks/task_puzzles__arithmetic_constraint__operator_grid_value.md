# `task_puzzles__arithmetic_constraint__operator_grid_value`

## Contract
1. Domain: `puzzles`
2. Scene id: `arithmetic_constraint`
3. Source implementation domain/group: `puzzles/logic`
4. Query id: sampled from `row_column_total_missing_value`, `operation_table_cell_value`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.puzzles.logic.arithmetic_constraint.PuzzlesLogicOperatorGridValueTask`
2. Prompt lookup domain/group: `puzzles/logic`
3. Prompt bundle: `puzzles_logic_v0`
4. Scene variants: `constraint_sheet`, `constraint_card`, `constraint_outline`
5. The scene shows a compact grid or operation table with one marked question target.
6. Structural variation is sampled per instance:
   - row/column total grids vary row and column counts,
   - operation tables vary row-header and column-header counts.
7. Operation-table rules are not printed in the prompt or image; the table operation is inferred from the filled cells.
8. `answer_gt.type`: `integer`
9. `evidence_gt.type`: `bbox_set` over the marked grid/table cell only.
10. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
11. Answers and evidence are produced from the same metadata execution trace.

# `task_puzzles__arithmetic_constraint__number_wall_value`

## Contract
1. Domain: `puzzles`
2. Scene id: `arithmetic_constraint`
3. Source implementation domain/group: `puzzles/logic`
4. Query id: sampled from `addition_wall_missing_value`, `difference_wall_missing_value`, `multiplication_pyramid_value`
5. Semantic query details are recorded in `query_id` and trace params.

## Implementation
1. Registered class: `trace.tasks.puzzles.logic.arithmetic_constraint.PuzzlesLogicNumberWallValueTask`
2. Prompt lookup domain/group: `puzzles/logic`
3. Prompt bundle: `puzzles_logic_v0`
4. Scene variants: `constraint_sheet`, `constraint_card`, `constraint_outline`
5. The scene shows a compact number wall or multiplication pyramid with one question-mark brick.
6. Structural variation is sampled per instance:
   - adjacent-rule walls vary base width,
   - multiplication pyramids vary base width while capping visible product size for readability.
7. The rule text is not printed in the prompt or image; the required relation is inferred from repeated visible brick examples.
8. `answer_gt.type`: `integer`
9. `evidence_gt.type`: `bbox_set` over the marked question-mark brick only.
10. Generation is deterministic from `instance_seed`, explicit params, prompt bundle, renderer config, and code versions.
11. Answers and evidence are produced from the same metadata execution trace.

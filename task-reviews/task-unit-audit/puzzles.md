# Puzzles Task-Unit Audit

Task-unit audit for `domain=puzzles` using `docs/workflows/TASK_UNIT_AUDIT.md`.

## Domain summary
1. The puzzles domain is in very good shape as a task-unit inventory.
2. It has strong visual diversity across arithmetic, logic, spatial, and topology families without overloading any one task id with multiple incompatible scaffolds.
3. Most puzzle tasks are narrow in a good way: each keeps one stable interaction grammar while still having enough internal scene/query variety to justify uniform task-level sampling.
4. Recommended domain outcome:
   - `Keep`: `10`
   - `Split`: `0`
   - `Merge`: `0`
   - `Retire`: `0`

## Task findings

### `task_puzzles_arithmetic_balance_value`
- Outcome: `Keep`
- Why: one coherent equality-panel arithmetic family with a stable “solve the queried symbol value” interaction.
- Scene variety: moderate; stacked equality panels with multiple visual frames and varying chain depth.
- Query variety: moderate (`sum_pair_unknown|two_panel_chain_unknown|three_panel_chain_unknown`) but still one stable unknown-symbol family.
- Grounding necessity: strong; the model must read the actual panel contents and query row from the image.
- Evidence fit: good; the question-mark query box is the right local witness.
- Follow-up: none required now.

### `task_puzzles_arithmetic_equation_value`
- Outcome: `Keep`
- Why: one coherent single-equation unknown-slot family.
- Scene variety: moderate; one equation row with varying operand count, operators, and missing slot position.
- Query variety: modest but coherent (`result_unknown|operand_unknown`).
- Grounding necessity: strong; the solver must read the visible arithmetic expression and the location of the unknown slot.
- Evidence fit: good; the unknown-slot bbox is the natural witness.
- Follow-up: none required now.

### `task_puzzles_arithmetic_grid_value`
- Outcome: `Keep`
- Why: one coherent arithmetic-rule grid family with a stable grid-reading scaffold.
- Scene variety: moderate; grid size, hidden-cell position, and rule family vary while the board grammar stays fixed.
- Query variety: moderate (`sum_rule_missing|difference_rule_missing|product_rule_missing`) within one stable row-rule grid family.
- Grounding necessity: strong; the model must infer the visible row rule from the grid itself.
- Evidence fit: good; the unknown cell is the right witness.
- Follow-up: none required now.

### `task_puzzles_logic_adjacency_completion_label`
- Outcome: `Keep`
- Why: one coherent option-completion logic family with an explicit non-touch rule.
- Scene variety: moderate; stable board-plus-options scaffold with varying board size and symbol placements.
- Query variety: narrow but appropriate (`king_non_touch`).
- Grounding necessity: strong; the model must inspect the board neighborhood around the `?` cell and compare with the option set.
- Evidence fit: good; the winning option-panel bbox is the right witness.
- Follow-up: none required now.

### `task_puzzles_logic_grid_completion_label`
- Outcome: `Keep`
- Why: one coherent Latin-style row/column uniqueness completion family.
- Scene variety: moderate; stable board-plus-options scaffold with varying board size and hidden-cell location.
- Query variety: moderate (`row_uniqueness|column_uniqueness|row_and_column_uniqueness`) but still one consistent completion-by-uniqueness family.
- Grounding necessity: strong; the solver must read the grid and test completion under the active uniqueness rule.
- Evidence fit: good; the winning option-panel bbox is the natural witness.
- Follow-up: none required now.

### `task_puzzles_spatial_assembly_label`
- Outcome: `Keep`
- Why: one coherent piece-to-silhouette assembly family.
- Scene variety: moderate; stable top-pieces / bottom-options scaffold with variable piece sets and option silhouettes.
- Query variety: narrow but appropriate (`can_be_built`).
- Grounding necessity: strong; the model must reason over the shown pieces and candidate silhouettes.
- Evidence fit: good; the winning option panel is the natural witness.
- Follow-up: none required now.

### `task_puzzles_spatial_cube_removal_count`
- Outcome: `Keep`
- Why: one coherent original-vs-remaining block comparison family.
- Scene variety: moderate; stable two-structure comparison scaffold with varied stack footprints and removal patterns.
- Query variety: narrow but appropriate (`cube_removal_count`).
- Grounding necessity: strong; the model must compare both visible structures and infer the removed cube count.
- Evidence fit: acceptable; the pair of structure boxes is a broad witness, but still the right semantic unit for this task.
- Follow-up: none required now.

### `task_puzzles_spatial_fold_result_label`
- Outcome: `Keep`
- Why: one coherent paper-fold result family with a stable reference-sheet plus options scaffold.
- Scene variety: moderate; fold axis, fold direction, mark layout, and option arrangement vary while the scene grammar stays fixed.
- Query variety: modest but coherent (`vertical_fold_result|horizontal_fold_result`).
- Grounding necessity: strong; the solver must map the shown fold instruction to the correct folded result.
- Evidence fit: good; the winning option image bbox is the natural witness.
- Follow-up: none required now.

### `task_puzzles_spatial_overlay_result_label`
- Outcome: `Keep`
- Why: one coherent transparent-sheet overlay family.
- Scene variety: moderate; stable two-source-sheets plus options scaffold with variable mark layouts and overlaps.
- Query variety: narrow but appropriate (`overlay_union_same_grid`).
- Grounding necessity: strong; the model must combine the two source patterns visually under the stated overlay rule.
- Evidence fit: good; the winning option image bbox is the natural witness.
- Follow-up: none required now.

### `task_puzzles_topology_bead_equivalence_count`
- Outcome: `Keep`
- Why: one coherent cyclic bead-order equivalence family.
- Scene variety: moderate; stable reference-loop plus option-loops scaffold with varied loop deformations, bead sequences, and option layouts.
- Query variety: moderate (`color_cycle_count|shape_cycle_count|mixed_cycle_count`) but still one stable cyclic-order family.
- Grounding necessity: strong; the solver must compare cyclic order visually rather than rely on simple row reading.
- Evidence fit: good; valid option-loop boxes are the natural witness.
- Follow-up: none required now.

## Recommended next action
1. Leave the puzzles domain unchanged for now.
2. Use puzzles as one of the benchmark examples of a healthy task-unit inventory: strong visual variety, but each task still keeps one stable interaction grammar.

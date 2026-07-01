# `task_symbolic__abacus__place_digit_readout`

## 1) Identity
1. Domain: `symbolic`
2. Scene id: `abacus`
3. Task id: `task_symbolic__abacus__place_digit_readout`
4. Objective: read the digit shown in one queried place-value column of a three-column soroban-style abacus.

## Program Contract
Program: `readout.digit(scene=abacus, scope=queried_place_value_column, rule=soroban_digit_sum, output=integer_digit)`

Candidate set: the three visible place-value columns labeled `100`, `10`, and `1`.
Operands: the queried place-value label and the active upper/lower bead states in that column after final layout.
Operation: compute the soroban digit for that column.
Output binding: `answer` is the queried column digit in `0..9`.
Annotation witnesses: a `point_set` containing zero or more active bead center points for the queried column. The point set is empty when the digit is `0`.
Query ids: `single`.

## 2) Scene + Task Contract
1. Supported public `query_id` values: `single`
2. `answer_gt.type`: `integer`
3. Annotation schema: `point_set`
4. `annotation_gt.type`: `point_set`
5. Non-semantic visual axes: `scene_variant=clean_card|wood_frame|worksheet`, plus shared symbolic background/noise.
6. Scene contract:
   - exactly three place-value columns labeled `100`, `10`, and `1`,
   - each column has one upper bead worth `5` and four lower beads worth `1`,
   - active beads are moved toward the center beam,
   - the prompt identifies the queried column by its visible place-value label,
   - the answer is the digit represented by that column alone.

## 3) Prompt Contract
1. Bundle: `symbolic_abacus_v1`
2. `scene_key`: `abacus`
3. `task_key`: `abacus_place_digit_query`
4. Required task slot: `question_text`
5. Prompt-facing answer is the integer digit shown in the queried column.

## 4) Annotation + Trace Contract
1. Annotation is the variable-cardinality unordered point set of active bead centers in the queried column.
2. Empty lists are valid for a queried column whose digit is `0`.
3. Annotation marks active bead center points only, not rods, labels, inactive beads, or the frame.
4. The trace records `target_column_role`, `target_place_label`, `target_place_value`, `digits_by_role`, and the selected annotation key.
5. Answer and annotation are bound from the same finalized rendered bead positions.

## 5) Tests
1. Behavior/trace/prompt tests: `tests/test_symbolic_abacus_tasks.py`
2. Prompt/config tests: `tests/test_prompt_system.py`, `tests/test_symbolic_core_scene_config.py`
3. Scene-package migration tests: `tests/test_scene_package_migration_contracts.py`

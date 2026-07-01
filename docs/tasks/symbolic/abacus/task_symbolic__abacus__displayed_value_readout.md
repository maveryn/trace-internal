# `task_symbolic__abacus__displayed_value_readout`

## 1) Identity
1. Domain: `symbolic`
2. Scene id: `abacus`
3. Task id: `task_symbolic__abacus__displayed_value_readout`
4. Objective: read the integer value represented by a three-column soroban-style abacus.

## Program Contract
Program: `readout.value(scene=abacus, scope=three_place_value_columns, rule=soroban_digit_sum, output=integer)`

Candidate set: the three visible place-value columns labeled `100`, `10`, and `1`.
Operands: the active upper and lower bead states in each column after final layout.
Operation: compute each soroban digit from the active beads, then combine the digits as `100 * hundreds + 10 * tens + ones`.
Output binding: `answer` is the resulting integer in `0..999`.
Annotation witnesses: role-keyed active-bead center-point sets for `hundreds_active_beads`, `tens_active_beads`, and `ones_active_beads`.
Query ids: `single`.

## 2) Scene + Task Contract
1. Supported public `query_id` values: `single`
2. `answer_gt.type`: `integer`
3. Annotation schema: `point_set_map`
4. `annotation_gt.type`: `point_set_map`
5. Non-semantic visual axes: `scene_variant=clean_card|wood_frame|worksheet`, plus shared symbolic background/noise.
6. Scene contract:
   - exactly three place-value columns labeled `100`, `10`, and `1`,
   - each column has one upper bead worth `5` and four lower beads worth `1`,
   - active beads are moved toward the center beam,
   - the answer is `hundreds_digit * 100 + tens_digit * 10 + ones_digit`,
   - answer support is `0..999`.

## 3) Prompt Contract
1. Bundle: `symbolic_abacus_v1`
2. `scene_key`: `abacus`
3. `task_key`: `abacus_displayed_value_query`
4. Required task slot: `question_text`
5. Prompt-facing answer is the integer shown by the abacus.

## 4) Annotation + Trace Contract
1. Annotation is role-keyed:
   - `hundreds_active_beads`: active bead center points in the `100` column,
   - `tens_active_beads`: active bead center points in the `10` column,
   - `ones_active_beads`: active bead center points in the `1` column.
2. Empty lists are valid for columns whose digit is `0`.
3. Annotation marks active bead center points only, not rods, labels, or the frame.
4. Answer and annotation are bound from the same finalized rendered bead positions.

## 5) Tests
1. Behavior/trace/prompt tests: `tests/test_symbolic_abacus_tasks.py`
2. Prompt/config tests: `tests/test_prompt_system.py`, `tests/test_symbolic_core_scene_config.py`
3. Scene-package migration tests: `tests/test_scene_package_migration_contracts.py`

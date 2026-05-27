# `task_games__sudoku__unit_missing_digits_count`

## Contract
1. Domain: `games`
2. Scene id: `sudoku`
3. Source task group: `sudoku`
4. Query id: `unit_missing_digits_count`
5. Objective: Count how many different digit values from 1 through 9 are missing from the highlighted Sudoku unit.

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: bbox_set over visible filled cells in the highlighted unit.
3. `unit_missing_digits_count` is retained as `query_id`; `query_spec.params.query_id` is internal replay diagnostics.

## Implementation
1. This task uses the shared games Sudoku-grid renderer for its scene id.
2. Prompt bundle: `games_sudoku_v0`
3. Generation samples highlighted rows, columns, and 3 by 3 boxes and enforces the requested missing-digit count by construction.

## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Scene density, highlighted unit type, visual style, and target-answer support remain explicit params inside the task.

# `task_games__sudoku__repeated_digit_count`

## Contract
1. Domain: `games`
2. Scene id: `sudoku`
3. Source task group: `sudoku`
4. Query id: `repeated_digit_count`
5. Objective: Count how many different digit values appear more than once in the highlighted Sudoku unit.

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: bbox_set over every highlighted-unit cell whose digit is one of the repeated values.
3. `repeated_digit_count` is retained as `query_id`; `query_spec.params.query_id` is internal replay diagnostics.

## Implementation
1. This task uses the shared games Sudoku-grid renderer for its scene id.
2. Prompt bundle: `games_sudoku_v0`
3. Generation samples highlighted rows, columns, and 3 by 3 boxes and enforces the requested repeated-digit count by construction.

## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Scene density, highlighted unit type, visual style, and target-answer support remain explicit params inside the task.

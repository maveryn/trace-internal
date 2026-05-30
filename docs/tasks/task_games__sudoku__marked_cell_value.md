# `task_games__sudoku__marked_cell_value`

## Contract
1. Domain: `games`
2. Scene id: `sudoku`
3. Source task group: `sudoku`
4. Query id: `marked_cell_value`
5. Objective: Identify the only valid digit for the marked empty Sudoku cell.

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: bbox_set containing the marked cell and visible filled cells from its row, column, and 3 by 3 box.
3. `marked_cell_value` is retained as `query_id`; `query_spec.params.query_id` is internal replay diagnostics.

## Implementation
1. This task uses the shared games Sudoku-grid renderer for its scene id.
2. Prompt bundle: `games_sudoku_v0`
3. Generation enforces a unique candidate digit for the marked empty cell under standard Sudoku row, column, and 3 by 3 box constraints.
4. Rendering samples shared games-domain panel backgrounds, digit fonts, layout jitter, post-image noise, and Sudoku board palettes.

## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Scene density, highlighted unit type, visual style, and target-answer support remain explicit params inside the task.

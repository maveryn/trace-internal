# `task_games__minesweeper__satisfied_clue_count`

## Contract
1. Domain: `games`
2. Scene id: `minesweeper`
3. Source task group: `minesweeper`
4. Query id: `satisfied_clue_count`
5. Objective: Count opened number cells whose clue value exactly equals the number of adjacent flags while ignoring unsatisfied numbered cells.

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: `bbox_set` over the opened number cells being counted.
3. `satisfied_clue_count` is retained as `query_id`; `query_spec.params.query_id` is internal replay diagnostics.

## Implementation
1. This task uses the shared games Minesweeper-grid renderer for its scene id.
2. Prompt bundle: `games_minesweeper_v0`
3. Generation builds flagged-mine satisfied clues plus a separate adjacent pair of hidden unflagged mines, so the scene contains opened number cells whose clue is greater than their adjacent flag count and should not be counted.
4. Calibrated board size support is `4..8`.
5. Calibrated answer support is the contiguous range `1..5`.
6. Rendering uses shared game panel backgrounds, six scene-local board styles,
   sampled fonts for clue numbers, unit-size jitter, and layout jitter.

## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Board size, scene density, visual style, and target-answer support remain explicit params inside the task.

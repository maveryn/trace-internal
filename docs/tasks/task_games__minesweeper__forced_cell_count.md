# `task_games__minesweeper__forced_cell_count`

## Contract
1. Domain: `games`
2. Scene id: `minesweeper`
3. Source task group: `minesweeper`
4. Query ids: `forced_mine_count`, `forced_safe_count`
5. Objective: Count hidden cells forced to be mines or forced to be safe by opened numbers and flags.

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: bbox_set over the forced hidden cells being counted.
3. Public `query_variant` is `default`; the sampled forced-cell query is recorded as `query_id` and `query_spec.params.query_variant`.

## Implementation
1. This task uses the shared games Minesweeper-grid renderer for its scene id.
2. Prompt bundle: `games_minesweeper_v0`
3. The satisfied-clue count remains a separate task because it counts opened number cells rather than hidden forced cells.
4. Calibrated board size support is `4..5` for this forced-cell task; the
   broader Minesweeper scene remains available to other Minesweeper tasks.
5. Answer support remains contiguous at `1..5` for both forced-mine and
   forced-safe queries.
6. The opened clue cell(s) used for the local deduction are outlined in the
   image, but evidence remains the hidden forced cells being counted.

## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Board size, scene density, visual style, and target-answer support remain explicit params inside the task.

# `task_games__2048__move_result_value`

## Contract
1. Domain: `games`
2. Task group: `2048`
3. Scene id: `2048`
4. Query ids: `merge_count`, `score_value`, `max_tile_value`
5. Objective: apply the shown 2048 move once and answer the requested integer property of the result.
6. Answer type: `integer`.
7. Evidence type: `bbox_set` over the original visible tile cells that support the move result.

## Query Notes
1. `merge_count` counts the number of equal-tile merge events created by the shown move.
2. `score_value` returns the sum of newly created merged tile values.
3. `max_tile_value` returns the largest tile value after the shown move.

## Generation Notes
1. Boards follow standard 2048 slide-and-merge rules.
2. The sampled answer is fixed by construction from the traced move simulation.
3. Merge and score evidence uses source tile cells for every merge; zero-merge or zero-score scenes use an empty evidence set.
4. Max-tile evidence uses the original tile cells that form the unique largest post-move tile.

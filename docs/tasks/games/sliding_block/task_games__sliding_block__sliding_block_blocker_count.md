# `task_games__sliding_block__sliding_block_blocker_count`

## Summary
1. Domain: `games`
2. Scene: `sliding_block`
3. Task id: `task_games__sliding_block__sliding_block_blocker_count`
4. Scene id: `sliding_block`
5. Goal: count the rectangular blocks currently occupying the red target block's straight path to the exit arrow.

## Contract
1. Branch metadata: `query_id`
2. `query_id`: `blocker_count`
3. Board size: `6..8` rows by `6..8` columns
4. Target blocker count support: `1..6`
5. Answer type: `integer`
6. Annotation type: `bbox_set`
7. Annotation target: all blocks in the target block's straight exit path
8. Scene variants: `wooden_tray|cool_grid|paper_board`

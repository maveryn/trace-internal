# `task_games__sliding_block__movable_block_count`

## Summary
1. Domain: `games`
2. Task group: `sliding_block`
3. Task id: `task_games__sliding_block__movable_block_count`
4. Scene id: `sliding_block`
5. Goal: count the non-target rectangular blocks that can legally slide at least one cell.

## Contract
1. Branch metadata: `query_id`
2. `query_id`: `movable_block_count`
3. Board size: `6..8` rows by `6..8` columns
4. Movable block count support: `4..9`
5. Answer type: `integer`
6. Annotation type: `bbox_set`
7. Annotation target: every non-target block with at least one legal one-cell slide
8. Scene variants: `wooden_tray|cool_grid|paper_board`

# `task_games__platformer__collectible_count`

1. Domain: `games`
2. Task group: `platformer`
3. Scene id: `platformer`
4. Query id: `collectible_count`
5. Prompt bundle: `games_platformer_v0`

The image shows a side-scroller platformer level with a player character, platforms, hazards, coins, and a dashed jump arc. The task asks how many coins lie on the dashed jump arc.

The answer is an integer coin count. Evidence is `point_set`: one pixel point at the center of each coin that lies on the jump arc.

Generation is deterministic for a fixed seed and records the full arc, on-path coin ids, distractor coin ids, prompt keys, render style, and projected evidence in the trace payload.

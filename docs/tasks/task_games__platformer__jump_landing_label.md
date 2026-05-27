# `task_games__platformer__jump_landing_label`

1. Domain: `games`
2. Task group: `platformer`
3. Scene id: `platformer`
4. Query id: `jump_landing_label`
5. Prompt bundle: `games_platformer_v0`

The image shows a side-scroller platformer level with a player character, platforms, hazards, coins, and a short dashed jump arc. The task asks for the label of the platform where the jump lands after extending the same smooth arc.

The answer is a string platform label. Evidence is `bbox_set`: one pixel bounding box around the landing platform.

Generation is deterministic for a fixed seed and records the hidden full arc, platform geometry, selected landing platform, prompt keys, render style, and projected evidence in the trace payload.

# task_games__minecraft__ore_block_count

1. Domain: `games`
2. Task group: `minecraft`
3. Scene id: `minecraft`
4. Query id: `ore_block_count`
5. Objective: count visible blocks of the requested ore type.

The image renders a Minecraft-like isometric block world with mixed visible cube blocks. The query names one ore type, such as diamond ore or gold ore.

The answer is an integer: the number of visible blocks of that ore type.

Evidence is `bbox_set`: one bounding box for every counted ore block.

Generation samples grid size, visual style, target ore kind, counted ore positions, and distractor blocks. The answer support is `1..6`, with balanced answer sampling by default.

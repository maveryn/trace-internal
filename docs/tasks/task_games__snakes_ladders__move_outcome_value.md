# `task_games__snakes_ladders__move_outcome_value`

## Contract
1. Domain: `games`
2. Task group: `snakes_ladders`
3. Scene id: `snakes_ladders`
4. Query id: `move_outcome_value`
5. Objective: compute the final square after the shown die roll, including one immediate snake or ladder if the direct landing square starts one.
6. Answer type: `integer`
7. Evidence type: `bbox_set` over the start square, shown die, direct landing square, and jump endpoint when a jump is used.

## Generation Notes
1. The scene shows a 10 x 10 numbered serpentine Snakes and Ladders board with one visible token.
2. The die value is shown in the side panel.
3. The final square is sampled from broad explicit support and is unique by construction.
4. The query branch is retained as `query_id` and trace metadata.
5. Default generation samples jump-triggered move outcomes with probability `0.30`; snakes and ladders remain visible as board context.

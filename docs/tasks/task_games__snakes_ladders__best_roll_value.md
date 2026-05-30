# `task_games__snakes_ladders__best_roll_value`

## Contract
1. Domain: `games`
2. Task group: `snakes_ladders`
3. Scene id: `snakes_ladders`
4. Query id: `best_roll_value`
5. Objective: return the highest numbered final square reachable after exactly 1 or 2 rolls, where each roll result can be independently chosen from 1 to 6.
6. Answer type: `integer`
7. Evidence type: `bbox_set` over the final board square named by the answer.

## Generation Notes
1. The horizon is sampled as `1` or `2` rolls and shown in the side panel.
2. The answer is sampled from `14..49`, bounded by the sampled board side; the token start square is chosen so the sampled final square is the highest reachable board position for the horizon.
3. The scene uses the same 5 x 5, 6 x 6, or 7 x 7 Snakes and Ladders renderer as the other tasks.
4. `best_roll_value` is retained as `query_id`.
5. The board uses shared games-domain panel backgrounds, sampled fonts, layout jitter, and five scene-local board palettes.

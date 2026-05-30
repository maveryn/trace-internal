# `task_games__hex__connection_gap_count`

## Contract
1. Domain: `games`
2. Task group: `hex`
3. Scene id: `hex`
4. Query id: `connection_gap_count`
5. Objective: count the minimum number of empty cells the queried player must fill to connect the required sides.
6. Answer type: `integer`.
7. Evidence type: `point_set` over the centers of empty cells in the unique minimum connection gap for the queried player.

## Generation Notes
1. Red connects the left and right red sides.
2. Blue connects the top and bottom blue sides.
3. Opponent stones block a route; own stones cost zero; empty cells cost one.
4. The sampled answer is verified by shortest-path search over the hex adjacency graph.
5. Generation rejects boards where more than one distinct minimum empty-cell set can witness the answer.
6. Rendering varies board style, shared panel treatment, label font, unit scale, and board placement jitter before projecting evidence.

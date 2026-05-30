# `task_games__pacman__route_pellet_count`

## Contract
1. Domain: `games`
2. Task group: `pacman`
3. Scene id: `pacman`
4. Query ids: `path_pellet_count`, `pellet_count_before_ghost`
5. Objective: follow the highlighted route from Pac-Man and count the requested normal pellets.
6. Answer type: `integer`.
7. Evidence type: `point_set`.

## Query Notes
1. `path_pellet_count` counts all normal pellets lying on the highlighted route; evidence is the counted pellet center points.
2. `pellet_count_before_ghost` counts only normal pellets before the first ghost on the highlighted route; evidence is the counted pellet center points plus the first route ghost center point.
3. Current calibration samples both count queries from answer support `1..5`.

## Generation Notes
1. The highlighted route starts at the visible Pac-Man marker and follows open maze cells.
2. The answer is unique by construction: route-pellet branches place exactly the target counted pellet set, and ghost-stop branches place exactly one first route ghost after the counted pellets.
3. Off-route pellets and decorative off-route ghosts may appear as distractors and are not part of the answer.

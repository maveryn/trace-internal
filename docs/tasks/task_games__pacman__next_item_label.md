# `task_games__pacman__next_item_label`

## Contract
1. Domain: `games`
2. Task group: `pacman`
3. Scene id: `pacman`
4. Query id: `next_item_label`
5. Objective: identify the first labeled bonus item reached when following the highlighted route from Pac-Man.
6. Answer type: `string`.
7. Evidence type: `bbox_set` over the selected bonus item.

## Generation Notes
1. Labeled bonus items use labels `A..F`, with `5..6` items shown.
2. The target bonus item is placed before all other labeled bonus items along the highlighted route.
3. Other labeled bonus items may appear later on the route or off the route as distractors.

# `task_games__battleship__last_ship_cell_label`

## Contract
1. Domain: `games`
2. Scene id: `battleship`
3. Public task id: `task_games__battleship__last_ship_cell_label`
4. Supported `query_id` values: `single`
5. Answer schema: `option_label`
6. Annotation schema: `point_set`
7. Program schema: `label(select(candidate_cells, completes_only_not_sunk_ship)); scene=battleship; scope=last_ship_cell_label`

## Program Contract
- `label(select(candidate_cells, completes_only_not_sunk_ship)); scene=battleship; scope=last_ship_cell_label`

## Generation Notes
1. The Battleship scene uses five fleet shapes: `Line 5`, `Line 4`, `Line 3`, `Square 2x2`, and `L 3`.
2. This task renders a hidden-ship tracking grid: red hit markers, gray miss markers, fleet-shape panel, and six labeled candidate cells `A-F`.
3. All non-target ships are fully hit. The target ship has exactly one unhit cell, and exactly one candidate label marks that cell.
4. Annotation is a one-point `point_set` at the selected answer cell center.

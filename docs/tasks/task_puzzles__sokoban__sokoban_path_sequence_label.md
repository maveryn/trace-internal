# `task_puzzles__sokoban__sokoban_path_sequence_label`

## Summary
1. Domain: `puzzles`
2. Task group: `spatial`
3. Task id: `task_puzzles__sokoban__sokoban_path_sequence_label`
4. Scene id: `sokoban`
5. Goal: choose the labeled move-sequence option that satisfies the requested path property on a Sokoban grid.

## Contract
1. Public `query_variant`: `default`
2. `query_id`: `shortest_path_sequence_label|valid_path_sequence_label|blocked_path_sequence_label`
3. Answer type: `option_letter`
4. Evidence type: `bbox_set`
5. Evidence targets: exactly one bbox for the selected option panel
6. Scene variants: `warehouse_classic|paper_grid|cool_room`
7. Trace contract: walls, box blockers, start/goal cells, shortest path, option sequences, and selected path simulation are recorded in metadata.

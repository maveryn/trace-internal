# `task_puzzles__sokoban__sokoban_box_target_relation_label`

## Summary
1. Domain: `puzzles`
2. Task group: `spatial`
3. Task id: `task_puzzles__sokoban__sokoban_box_target_relation_label`
4. Scene id: `sokoban`
5. Goal: choose the option letter drawn on the board object or same-letter object pair matching a box-target Manhattan-distance relation.

## Contract
1. Branch metadata: `query_id`
2. `query_id`: `nearest_target_for_marked_box_label|box_closest_to_marked_target_label|box_target_manhattan_rank_label`
3. Answer type: `option_letter`
4. Evidence type: `bbox_set`
5. Evidence targets: selected option-lettered board cell bbox; pair queries include the selected box cell followed by the selected target cell.
6. Scene variants: `warehouse_classic|paper_grid|cool_room`
7. Trace contract: labeled box/target cells, marked reference entity, same-letter pair distances, option specs, and answer relation are recorded in metadata.

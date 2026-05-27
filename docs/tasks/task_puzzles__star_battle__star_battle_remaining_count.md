# `task_puzzles__star_battle__star_battle_remaining_count`

## Summary
1. Domain: `puzzles`
2. Task group: `logic`
3. Task id: `task_puzzles__star_battle__star_battle_remaining_count`
4. Scene id: `star_battle`
5. Goal: count legal remaining star placements in a marked row, column, or region.

## Contract
1. Branch metadata: `query_id`
2. `query_id`: `remaining_valid_cells_in_marked_region_count|remaining_valid_cells_in_marked_row_count|remaining_valid_cells_in_marked_column_count`
3. Grid size: `6x6..9x9`
4. Answer support: `1..6`
5. Answer type: `integer`
6. Evidence type: `bbox_set`
7. Evidence target: marked row, column, or region followed by every legal cell in that scope
8. Scene variants: `star_battle_classic|star_battle_pastel|star_battle_blueprint`

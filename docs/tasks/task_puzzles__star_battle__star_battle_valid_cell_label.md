# `task_puzzles__star_battle__star_battle_valid_cell_label`

## Summary
1. Domain: `puzzles`
2. Task group: `logic`
3. Task id: `task_puzzles__star_battle__star_battle_valid_cell_label`
4. Scene id: `star_battle`
5. Goal: choose the labeled cell where a star can still be legally placed.

## Contract
1. Public `query_variant`: `default`
2. `query_id`: `valid_cell_anywhere_label|valid_cell_in_marked_region_label|valid_cell_for_marked_row_label`
3. Grid size: `6x6..9x9`
4. Candidate labels: `A..H` with `5..8` shown per instance
5. Answer type: `option_letter`
6. Evidence type: `bbox_set`
7. Evidence target: selected candidate cell, plus the marked row or region when the query scopes the choice
8. Scene variants: `star_battle_classic|star_battle_pastel|star_battle_blueprint`

# `task_puzzles__star_battle__remaining_valid_cell_count`

## Program Contract

- Program schema: `count(star_battle.valid_cells, scope=marked_region|marked_row|marked_column); scene=star_battle; scope=marked_scope_cells`
- Scene: `star_battle`
- Scope: cells inside the marked row, column, or colored region
- Query ids: `remaining_valid_cells_in_marked_region_count`, `remaining_valid_cells_in_marked_row_count`, `remaining_valid_cells_in_marked_column_count`
- Answer schema: integer
- Annotation schema: bbox_set

## Behavior

The task renders a partial Star Battle board with visible fixed stars and one marked row, column, or colored region. The model counts cells in that marked scope where another star could legally be placed under the Star Battle rules. The annotation is the bbox set of counted legal cells only.

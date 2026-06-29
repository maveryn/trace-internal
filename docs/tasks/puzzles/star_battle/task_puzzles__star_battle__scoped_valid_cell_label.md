# `task_puzzles__star_battle__scoped_valid_cell_label`

## Program Contract

- Program schema: `select_option(star_battle.valid_cell, scope=marked_region|marked_row); scene=star_battle; scope=marked_scope_candidates`
- Scene: `star_battle`
- Scope: labeled candidate cells inside the marked row or marked colored region
- Query ids: `valid_cell_in_marked_region_label`, `valid_cell_for_marked_row_label`
- Answer schema: option letter
- Annotation schema: bbox

## Behavior

The task renders a partial Star Battle board with visible fixed stars, one marked row or region, and labeled candidate cells. Exactly one labeled candidate in the marked scope is legal under the Star Battle rules. The answer is that candidate label. The annotation is the selected candidate cell bbox.

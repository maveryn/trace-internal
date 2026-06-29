# `task_puzzles__star_battle__valid_cell_anywhere_label`

## Program Contract

- Program schema: `select_option(star_battle.valid_cell, scope=whole_board); scene=star_battle; scope=visible_board_candidates`
- Scene: `star_battle`
- Scope: labeled candidate cells on the visible Star Battle board
- Query ids: `single` publicly; internal query `valid_cell_anywhere_label`
- Answer schema: option letter
- Annotation schema: bbox

## Behavior

The task renders a partial Star Battle board with visible fixed stars and labeled candidate cells. Exactly one candidate cell is legal under the rules: each row, column, and colored region has exactly one star, and stars may not touch by edge or corner. The answer is the label of that legal candidate. The annotation is the selected candidate cell bbox.

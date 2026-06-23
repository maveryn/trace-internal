# `task_games__sokoban__box_target_manhattan_rank_label`

## Contract
1. Domain: `games`
2. Scene id: `sokoban`
3. Public task id: `task_games__sokoban__box_target_manhattan_rank_label`
4. Supported `query_id` values: `single`
5. Answer schema: `option_letter`
6. Annotation schema: `bbox_set`
7. Program schema: `select_option(ranked_box_target_manhattan_pair); scene=sokoban; scope=box_target_manhattan_rank_label`
8. Scalar annotation checked: `true`

## Program Contract
- `select_option(ranked_box_target_manhattan_pair); scene=sokoban; scope=box_target_manhattan_rank_label`

## Generation Notes
1. The board shows same-letter box-target candidate pairs.
2. The task asks for the pair with a requested Manhattan-distance rank.
3. Annotation contains bboxes for the selected same-letter box cell and its matching target cell.
4. Prompt wording comes from `prompts/games/sokoban/games_sokoban_v1.json`.

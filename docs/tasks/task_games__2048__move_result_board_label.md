# `task_games__2048__move_result_board_label`

## Contract
1. Domain: `games`
2. Scene package: `trace/tasks/games/2048/`
3. Scene id: `2048`
4. Public task id: `task_games__2048__move_result_board_label`
5. Supported public `query_id` values: `default`
6. Prompt query key: `move_result_board_label`
7. Answer schema: `string_label`
8. Annotation schema: `bbox_set`
9. Program schema: `label(select_option(candidate_result_boards, option_board = simulate(board, rules=slide_merge_2048, action=move_direction).final_board)); scene=2048; scope=move_result_board_label`

## Program Contract
- `label(select_option(candidate_result_boards, option_board = simulate(board, rules=slide_merge_2048, action=move_direction).final_board)); scene=2048; scope=move_result_board_label`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.

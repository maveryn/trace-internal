# task_games__ludo_board__move_result_option_label

Public taxonomy: `games -> ludo_board -> task_games__ludo_board__move_result_option_label`.

## Program Contract

Program code: `select(destination_label where destination_cell == advance(token_position, shown_roll_sequence)); scene=ludo_board; scope=move_result_option_label`.

The scene renders a Ludo-style cross board with one visible token for each player color, twelve two-cell arrows showing clockwise flow, a visible dice sequence, and destination letters on board cells. The task asks which destination letter the named token reaches after applying the shown sequence.

Answer schema: `option_letter`.

Annotation schema: `keyed_point_map` with `moving_token`, `roll_sequence`, and `destination_cell`.

Supported `query_id`: `single`.

## Generator

- Implementation: `trace/tasks/games/ludo_board/move_result_option_label.py`
- Config: `configs/domains/games/ludo_board.yaml`
- Prompt bundle: `prompts/games/ludo_board/games_ludo_board_v1.json`

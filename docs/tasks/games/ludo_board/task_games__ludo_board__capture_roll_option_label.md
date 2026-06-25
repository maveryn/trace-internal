# task_games__ludo_board__capture_roll_option_label

Public taxonomy: `games -> ludo_board -> task_games__ludo_board__capture_roll_option_label`.

## Program Contract

Program code: `select(option_label where clockwise_distance(mover_token, target_token) == option_roll_distance); scene=ludo_board; scope=capture_roll_option_label`.

The scene renders a Ludo-style cross board with one visible token for each player color, twelve two-cell arrows showing clockwise flow, and visible roll-option cards. The task asks which displayed option moves the named token onto the named target token. A `6 then k` option means move six spaces, then k more spaces.

Answer schema: `option_letter`.

Annotation schema: `point_map` with `mover_token` and `target_token`.

Supported `query_id`: `single`.

## Generator

- Implementation: `trace/tasks/games/ludo_board/capture_roll_option_label.py`
- Config: `configs/domains/games/ludo_board.yaml`
- Prompt bundle: `prompts/games/ludo_board/games_ludo_board_v1.json`

# task_games__ludo_board__winning_roll_value

Public taxonomy: `games -> ludo_board -> task_games__ludo_board__winning_roll_value`.

## Program Contract

Program code: `exact_finish_roll(token_position, finish_cell); scene=ludo_board; scope=winning_roll_value`.

The scene renders a Ludo-style cross board with one visible token for each player color and twelve two-cell arrows showing clockwise flow. The task asks what single die roll the named token needs to land exactly on its matching finish. No capture, blocking, bonus-turn, or strategy rule is used.

Answer schema: `integer` in `1..5`.

Annotation schema: `keyed_bbox_map` with `token` and `finish`.

Supported `query_id`: `single`.

## Generator

- Implementation: `trace/tasks/games/ludo_board/winning_roll_value.py`
- Config: `configs/domains/games/ludo_board.yaml`
- Prompt bundle: `prompts/games/ludo_board/games_ludo_board_v1.json`

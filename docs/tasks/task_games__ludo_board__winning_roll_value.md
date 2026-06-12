# task_games__ludo_board__winning_roll_value

Public taxonomy: `games -> ludo_board -> task_games__ludo_board__winning_roll_value`.

## Contract

1. The scene renders a Ludo-style cross board with one visible token for each player color and twelve two-cell arrows showing clockwise track flow.
2. The task asks for the exact die roll a named token needs to reach its matching finish.
3. The token is already in its home lane; no capture, blocking, bonus-turn, or strategy rule is used.
4. Answer type: `integer`.
5. Annotation type: `keyed_bbox_map` with `token` and `finish`.
6. Query id: `winning_roll_value`.

## Generator

- Implementation: `trace/tasks/games/ludo_board/winning_roll_value.py`
- Config: `configs/domains/games/ludo_board.yaml`
- Prompt bundle: `prompts/games/ludo_board/games_ludo_board_v1.json`

# task_games__ludo_board__capture_roll_option_label

Public taxonomy: `games -> ludo_board -> task_games__ludo_board__capture_roll_option_label`.

## Contract

1. The scene renders a Ludo-style cross board with one visible token for each player color, twelve two-cell arrows showing clockwise track flow, and six image-drawn roll options.
2. The task asks which option lets the named mover token land on the named target token by moving clockwise.
3. A single `6` is allowed, and a `6 then k` option means moving six spaces, then moving `k` more spaces.
4. Answer type: `string`.
5. Annotation type: `keyed_bbox_map` with `mover_token` and `target_token`.
6. Query id: `capture_roll_option_label`.

## Generator

- Implementation: `trace/tasks/games/ludo_board/capture_roll_option_label.py`
- Config: `configs/domains/games/ludo_board.yaml`
- Prompt bundle: `prompts/games/ludo_board/games_ludo_board_v1.json`

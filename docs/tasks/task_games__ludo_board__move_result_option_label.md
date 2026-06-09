# task_games__ludo_board__move_result_option_label

Public taxonomy: `games -> ludo_board -> task_games__ludo_board__move_result_option_label`.

## Contract

1. The scene renders a Ludo-style cross board with one visible token for each player color, twelve two-cell arrows showing clockwise track flow, a dice sequence below the board, and six destination letters on board cells.
2. The task asks which board letter the named token reaches after applying the shown dice sequence.
3. The dice sequence may be a single roll, `6` followed by a non-6 roll, or `6`, `6`, followed by a non-6 roll.
4. Answer type: `option_letter`.
5. Annotation type: `keyed_bbox_map` with `moving_token`, `roll_sequence`, and `destination_cell`.
6. Query id: `move_result_option_label`.

## Generator

- Implementation: `trace/tasks/games/ludo_board/board_tasks.py`
- Config: `configs/domains/games/ludo_board.yaml`
- Prompt bundle: `prompts/games/ludo_board/games_ludo_board_v0.json`

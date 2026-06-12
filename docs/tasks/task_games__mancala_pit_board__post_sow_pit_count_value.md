# task_games__mancala_pit_board__post_sow_pit_count_value

Public taxonomy: `games -> mancala_pit_board -> task_games__mancala_pit_board__post_sow_pit_count_value`.

## Contract

1. The scene renders a simplified two-row pit board with 12 labeled pits, visible seeds, a sowing direction arrow, one X-marked source pit, and one target-marked pit.
2. The task asks how many seeds are in the target-marked pit after one sowing move from the source pit.
3. The task does not use stores, captures, extra turns, or strategy rules.
4. Answer type: `integer`.
5. Annotation type: `keyed_bbox_map` with `source_pit` and `target_pit`.
6. Query id: `post_sow_pit_count_value`.

## Generator

- Implementation: `trace/tasks/games/mancala_pit_board/post_sow_pit_count_value.py`
- Config: `configs/domains/games/mancala_pit_board.yaml`
- Prompt bundle: `prompts/games/mancala_pit_board/games_mancala_pit_board_v1.json`

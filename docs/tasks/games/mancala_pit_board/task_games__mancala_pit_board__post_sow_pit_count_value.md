# task_games__mancala_pit_board__post_sow_pit_count_value

Public taxonomy: `games -> mancala_pit_board -> task_games__mancala_pit_board__post_sow_pit_count_value`.

## Program Contract

Program code: `count(final_seeds(target_pit) after sow_all_seeds_from(source_pit)); scene=mancala_pit_board; scope=post_sow_pit_count_value`.

The scene renders a simplified two-row pit board with 12 labeled pits, visible seeds, a sowing direction arrow, one X-marked source pit, and one target-marked pit. The task asks how many seeds are in the target-marked pit after one sowing move from the source pit. No stores, captures, extra turns, or strategy rules are used.

Answer schema: `integer`.

Annotation schema: `keyed_bbox_map` with `source_pit` and `target_pit`.

Supported `query_id`: `single`.

## Generator

- Implementation: `trace/tasks/games/mancala_pit_board/post_sow_pit_count_value.py`
- Config: `configs/domains/games/mancala_pit_board.yaml`
- Prompt bundle: `prompts/games/mancala_pit_board/games_mancala_pit_board_v1.json`

# task_games__mancala_pit_board__sowing_landing_pit_label

Public taxonomy: `games -> mancala_pit_board -> task_games__mancala_pit_board__sowing_landing_pit_label`.

## Program Contract

Program code: `select(pit_label where pit == last(sow_all_seeds_from(source_pit))); scene=mancala_pit_board; scope=sowing_landing_pit_label`.

The scene renders a simplified two-row pit board with 12 labeled pits, visible seeds, a sowing direction arrow, and one X-marked source pit. The task asks which labeled pit receives the last seed after picking up all seeds from the source pit and sowing one seed at a time in the arrow direction. No stores, captures, extra turns, or strategy rules are used.

Answer schema: `string` capital pit label.

Annotation schema: `bbox_set` containing the selected landing pit bounding box.

Supported `query_id`: `single`.

## Generator

- Implementation: `trace/tasks/games/mancala_pit_board/sowing_landing_pit_label.py`
- Config: `configs/domains/games/mancala_pit_board.yaml`
- Prompt bundle: `prompts/games/mancala_pit_board/games_mancala_pit_board_v1.json`

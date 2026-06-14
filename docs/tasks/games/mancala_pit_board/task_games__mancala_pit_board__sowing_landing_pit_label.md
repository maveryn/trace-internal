# task_games__mancala_pit_board__sowing_landing_pit_label

Public taxonomy: `games -> mancala_pit_board -> task_games__mancala_pit_board__sowing_landing_pit_label`.

## Contract

1. The scene renders a simplified two-row pit board with 12 labeled pits, visible seeds, a sowing direction arrow, and one X-marked source pit.
2. The task asks which labeled pit receives the last seed after picking up all seeds from the source pit and sowing one seed at a time in the arrow direction.
3. The task does not use stores, captures, extra turns, or strategy rules.
4. Answer type: `string`.
5. Annotation type: `bbox_set` containing the selected landing pit bounding box.
6. Query id: `sowing_landing_pit_label`.

## Generator

- Implementation: `trace/tasks/games/mancala_pit_board/sowing_landing_pit_label.py`
- Config: `configs/domains/games/mancala_pit_board.yaml`
- Prompt bundle: `prompts/games/mancala_pit_board/games_mancala_pit_board_v1.json`

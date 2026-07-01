# task_games__ludo_board__move_result_option_label

Public taxonomy: `games -> ludo_board -> task_games__ludo_board__move_result_option_label`.

## Program Contract

Program: `select(destination_label where destination_cell == advance(token_position, shown_roll_sequence)); scene=ludo_board; scope=move_result_option_label`

Candidate set: the visible game board, pieces, tokens, cards, tiles, marked state, legal-move cues, result panels, and labeled options inside the `move_result_option_label` objective scope.
Operands: visible scene state and prompt-bound operands named by `destination_label`, `where`, `destination_cell`, `advance`, `token_position`, `shown_roll_sequence`, `ludo_board`, `move_result_option_label`.
Operation: evaluate `select` over the candidate set using the visible game state, rules, legal moves, comparisons, counts, simulations, or option-selection constraints encoded in the program expression; generation enforces a unique final answer.
Output binding: `answer` uses the `option_letter` schema; generation binds a unique final answer.
Annotation witnesses: `annotation` uses the `bbox` schema; the prompt/annotation contract defines the minimal visual witnesses.
Query ids: `single`.

## Generator

- Implementation: `trace/tasks/games/ludo_board/move_result_option_label.py`
- Config: `configs/domains/games/ludo_board.yaml`
- Prompt bundle: `prompts/games/ludo_board/games_ludo_board_v1.json`

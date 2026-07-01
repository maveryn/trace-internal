# `task_games__reversi__legal_destination_count`

## Program Contract

Program: `count(legal_moves(current_player)); scene=reversi; scope=legal_destination_count`

Candidate set: the visible game board, pieces, tokens, cards, tiles, marked state, legal-move cues, result panels, and labeled options inside the `legal_destination_count` objective scope.
Operands: visible scene state and prompt-bound target operands named by the task contract.
Operation: evaluate `count(legal_moves(current_player))` over the candidate set using the visible Reversi board state; generation enforces a unique final answer.
Output binding: `answer` uses the `integer` schema; generation binds a unique final answer.
Annotation witnesses: `annotation` uses the `bbox_set` schema for every legal destination cell.
Query ids: `single`.

## Generation Notes

- The task counts all legal empty destination cells for the current player.
- Annotation boxes are the board-cell bboxes for every counted destination cell.
- The answer and annotation are bound from the same generated legal-move set.

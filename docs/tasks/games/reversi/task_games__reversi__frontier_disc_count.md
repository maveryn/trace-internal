# `task_games__reversi__frontier_disc_count`

## Program Contract

Program: `count(filter(discs(query_color), touches_empty_neighbor)); scene=reversi; scope=frontier_disc_count`

Candidate set: the visible game board, pieces, tokens, cards, tiles, marked state, legal-move cues, result panels, and labeled options inside the `frontier_disc_count` objective scope.
Operands: visible scene state and prompt-bound target operands named by the task contract.
Operation: evaluate `count(filter(discs(query_color), touches_empty_neighbor))` over the candidate set using the visible Reversi board state; generation enforces a unique final answer.
Output binding: `answer` uses the `integer` schema; generation binds a unique final answer.
Annotation witnesses: `annotation` uses the `point_set` schema for the counted frontier disc centers.
Query ids: `single`.

## Generation Notes

- A frontier disc is a queried-color disc adjacent horizontally, vertically, or diagonally to at least one empty board cell.
- The target disc color is sampled with `target_player` (`black` or `white`).
- Annotation points are the centers of all counted frontier discs.
- The answer and annotation are bound from the same generated board state.

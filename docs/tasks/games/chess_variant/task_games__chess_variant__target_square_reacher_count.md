# `task_games__chess_variant__target_square_reacher_count`

## Contract
1. Domain: `games`
2. Scene id: `chess_variant`
3. Public task id: `task_games__chess_variant__target_square_reacher_count`
4. Supported `query_id` values: `white_piece_reaches_target_count`, `black_piece_reaches_target_count`
5. Answer schema: `integer_count`
6. Annotation schema: `bbox_set`
7. Program schema: `count(filter(pieces(target_color), target_square in legal_destinations(piece))); scene=chess_variant; scope=target_square_reacher_count`

## Program Contract

Program: `count(filter(pieces(target_color), target_square in legal_destinations(piece))); scene=chess_variant; scope=target_square_reacher_count`

Candidate set: the visible game board, pieces, tokens, cards, tiles, marked state, legal-move cues, result panels, and labeled options inside the `target_square_reacher_count` objective scope.
Operands: visible scene state and prompt-bound operands named by `filter`, `pieces`, `target_color`, `target_square`, `legal_destinations`, `piece`, `chess_variant`, `target_square_reacher_count` plus the active `query_id` branch.
Operation: evaluate `count` over the candidate set using the visible game state, rules, legal moves, comparisons, counts, simulations, or option-selection constraints encoded in the program expression; generation enforces a unique final answer.
Output binding: `answer` uses the `integer` schema; generation binds a unique final answer.
Annotation witnesses: `annotation` uses the `bbox_set` schema; the prompt/annotation contract defines the minimal visual witnesses.
Query ids: `white_piece_reaches_target_count`, `black_piece_reaches_target_count`.

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. The blue outlined square is the target square; annotation marks the source-piece boxes that can legally reach it.

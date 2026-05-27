# `task_games__chess__player_capture_piece_count`

## Contract
1. Domain: `games`
2. Scene id: `chess`
3. Source task group: `chess`
4. Query id: `player_capture_piece_count`
5. Objective: Count the opponent pieces that the named side can capture in one move.

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: bbox_set containing the capturable opponent-piece boxes.
3. Public `query_variant` is `default`; `player_capture_piece_count` is retained as `query_id` and `query_spec.params.query_variant` for diagnostics.

## Implementation
1. This task uses the shared games Chess-board renderer for its scene id.
2. Prompt bundle: `games_chess_v0`
3. Generation uses standard piece movement, excluding castling, en passant, and promotion cases; each capturable opponent piece is counted once even if multiple pieces attack it.

## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Scene density, visual style, player color, and target-answer support remain explicit params inside the task.

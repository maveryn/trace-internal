# `task_games__chess__marked_piece_destination_count`

## Contract
1. Domain: `games`
2. Scene id: `chess`
3. Source task group: `chess`
4. Query ids: `marked_piece_move_count`, `marked_piece_capture_count`
5. Objective: Count marked-piece destination squares matching the sampled move condition.

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: `bbox_set` over qualifying destination board cells.
3. For `marked_piece_capture_count`, evidence is the occupied destination cell, not the tighter opponent-piece glyph box.
4. Public `query_variant` is `default`; the sampled condition is retained as `query_id` and `query_spec.params.query_variant` for diagnostics.

## Implementation
1. This task uses the shared games Chess-board renderer.
2. Prompt bundle: `games_chess_v0`
3. Generation uses standard piece movement, excluding castling, en passant, and promotion cases.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.

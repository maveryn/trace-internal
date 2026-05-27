# `task_games__chess_variant__marked_piece_destination_count`

## Contract
1. Domain: `games`
2. Scene id: `chess_variant`
3. Source task group: `chess_variant`
4. Query ids: `marked_piece_move_count`, `marked_piece_capture_count`
5. Objective: Count marked-token destination squares matching the sampled condition under the visible rule card.

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: `bbox_set` over qualifying destination board cells.
3. For `marked_piece_capture_count`, evidence is the occupied destination cell, not the tighter opponent-token box.
4. The sampled condition is retained as `query_id` and `query_spec.params.query_id` for diagnostics.

## Implementation
1. The scene shows an 8 by 8 chess-like board with W/B tokens and a visible rule card.
2. Internal rule families include straight range, diagonal range, straight-or-diagonal range, and leaper rules.
3. Prompt bundle: `games_chess_variant_v0`

## Determinism
Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.

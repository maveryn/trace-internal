# `task_games__chess__king_escape_square_count`

## Contract
1. Domain: `games`
2. Scene id: `chess`
3. Source task group: `chess`
4. Query id: `king_escape_square_count`
5. Objective: Count safe one-step destination squares for the blue-outlined king.

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: bbox_set containing the safe destination-square boxes.
3. Public `query_variant` is `default`; `king_escape_square_count` is retained as `query_id` and `query_spec.params.query_variant` for diagnostics.

## Implementation
1. This task uses the shared games Chess-board renderer for its scene id.
2. Prompt bundle: `games_chess_v0`
3. Generation constructs a marked-king board with target answer support `0..5`; a safe square is empty or capturable and is not attacked after the king moves there.

## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Scene density, visual style, marked king color, and target-answer support remain explicit params inside the task.

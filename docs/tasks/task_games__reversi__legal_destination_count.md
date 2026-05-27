# `task_games__reversi__legal_destination_count`

## Contract
1. Domain: `games`
2. Scene id: `reversi`
3. Source task group: `reversi`
4. Query ids: `legal_move_count`, `corner_move_count`
5. Objective: Count legal destination squares for the current player, optionally restricted to corner destinations.

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: bbox_set over legal destination squares being counted.
3. Public `query_variant` is `default`; the sampled destination-count query is recorded as `query_id` and `query_spec.params.query_variant`.

## Implementation
1. This task uses the shared games Reversi-board renderer for its scene id.
2. Prompt bundle: `games_reversi_v0`
3. The marked-move flip-count query remains a separate task because it asks about a specific highlighted move rather than destination-set counting.

## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Board size, current player, visual style, and target-answer support remain explicit params inside the task.

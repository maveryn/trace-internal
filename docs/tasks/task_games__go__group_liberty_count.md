# `task_games__go__group_liberty_count`

## Contract
1. Domain: `games`
2. Scene id: `go`
3. Source task group: `go`
4. Query ids: `marked_group_liberty_count`, `marked_group_shared_liberty_count`
5. Objective: Count marked-group liberties matching the sampled liberty condition.

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: `bbox_set` over counted liberty intersections.
3. Public `query_variant` is `default`; the sampled liberty condition is retained as `query_id` and `query_spec.params.query_variant` for diagnostics.

## Implementation
1. This task uses the shared games Go-board renderer.
2. Prompt bundle: `games_go_v0`

## Determinism
Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.

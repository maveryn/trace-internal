# `task_games__dominoes__property_count`

## Contract
1. Domain: `games`
2. Scene id: `dominoes`
3. Source task group: `dominoes`
4. Query ids: `matching_end_count`, `higher_sum_than_reference_count`, `sum_to_target_count`, `double_count`
5. Objective: Count loose dominoes satisfying the sampled property query.

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: bbox_set over the loose dominoes being counted.
3. Public `query_variant` is `default`; the sampled property is recorded as `query_id` and `query_spec.params.query_variant`.

## Implementation
1. This task uses the shared games domino-chain renderer for its scene id.
2. Prompt bundle: `games_dominoes_v0`
3. Mirror query branches stay inside the task as `query_id` values.

## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Scene style, scene layout, target-answer support, candidate count, and property query remain explicit params inside the task.

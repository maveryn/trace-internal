# `task_games__checkers__max_capture_chain_length`

## Contract
1. Domain: `games`
2. Scene id: `checkers`
3. Source task group: `checkers`
4. Query id: `max_capture_chain_length`
5. Objective: Find the maximum number of opponent pieces the marked king checker can capture in one continuous jump chain.

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: bbox_set over the opponent pieces captured along the longest chain.
3. Public `query_variant` is `default`; `max_capture_chain_length` is retained as `query_id` and `query_spec.params.query_variant` for diagnostics.

## Implementation
1. This task uses the shared games scene renderer for its scene id.
2. Prompt bundle: `games_checkers_v0`

## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Semantic knobs such as player color, scene density, style, and target-answer support remain explicit params inside the task.

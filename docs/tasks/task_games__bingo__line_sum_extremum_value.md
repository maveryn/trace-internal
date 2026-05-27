# `task_games__bingo__line_sum_extremum_value`

## Contract
1. Domain: `games`
2. Scene id: `bingo`
3. Source task group: `bingo`
4. Query id: `line_sum_extremum_value`
5. Objective: Sum printed numbers in each completed bingo row or column on the sampled axis, then report the unique maximum or minimum sum.

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: bbox_set over the five cells in the completed line whose sum is the unique extremum.
3. Public `query_variant` is `default`; `line_sum_extremum_value` is retained as `query_id` and `query_spec.params.query_variant` for diagnostics.

## Implementation
1. This task uses the shared games bingo-card renderer for its scene id.
2. Prompt bundle: `games_bingo_v0`
3. Generation samples 2-5 completed lines on the queried axis and rejects scenes where the selected extremum sum is tied.

## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Axis, extremum direction, visual style, and completed-line-count support remain explicit params inside the task.

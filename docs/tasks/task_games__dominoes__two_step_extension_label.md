# `task_games__dominoes__two_step_extension_label`

## Contract
1. Domain: `games`
2. Scene id: `dominoes`
3. Source task group: `dominoes`
4. Query id: `two_step_extension_label`
5. Objective: Identify the labeled loose domino that can be played second after one other loose domino extends the `REF` tile's open right end.

## Answer and Evidence
1. Answer type: `string`
2. Evidence type: bbox_set containing the first-step loose domino box and the answer domino box.
3. `two_step_extension_label` is retained as `query_id`; `query_spec.params.query_id` is internal replay diagnostics.

## Implementation
1. This task uses the shared games domino-chain renderer for its scene id.
2. Prompt bundle: `games_dominoes_v0`
3. Generation constructs a unique two-step path: exactly one loose domino can connect to `REF`, and exactly one labeled loose domino can connect to the new open end after that first play.

## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Scene layout, visual style, candidate count, target label index, and target-answer support remain explicit params inside the task.
3. Current calibration uses five labeled loose candidate dominoes (`A..E`) for this task, with both one-row and two-row layouts still sampled.

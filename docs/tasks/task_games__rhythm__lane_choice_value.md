# `task_games__rhythm__lane_choice_value`

## Contract
1. Domain: `games`
2. Scene id: `rhythm`
3. Source task group: `rhythm`
4. Query ids: `most_hits_lane_label`, `earliest_hit_lane_label`
5. Objective: Choose the lane number with either the most arriving notes or the earliest arriving note.

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: `bbox_set` over the visible note or notes that justify the selected lane.
3. The active lane-choice branch is retained as `query_id` and `query_spec.params.query_id`.

## Implementation
1. This task uses the shared games rhythm-lanes renderer.
2. Prompt bundle: `games_rhythm_v0`
3. Generation enforces a unique winning lane by construction for both most-hit and earliest-hit queries.

## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Lane count, row count, beat window, winning lane, note layout, and visual style are recorded in the trace payload.

# `task_games__rhythm__hit_window_count`

## Contract
1. Domain: `games`
2. Scene id: `rhythm`
3. Source task group: `rhythm`
4. Query ids: `lane_hit_count`, `lane_color_hit_count`
5. Objective: Count notes in a specified lane that reach the hit line within a beat window, optionally filtered by note color.

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: `bbox_set` over every counted note.
3. The active timing/count branch is retained as `query_id` and `query_spec.params.query_id`.

## Implementation
1. This task uses the shared games rhythm-lanes renderer.
2. Prompt bundle: `games_rhythm_v0`
3. Generation constructs a unique target count, then adds same-lane and other-lane distractor notes that do not alter the answer.

## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Lane count, row count, beat window, target count, note colors, and visual style remain explicit params or recorded sampled axes.

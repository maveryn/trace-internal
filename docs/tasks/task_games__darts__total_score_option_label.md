# `task_games__darts__total_score_option_label`

## Contract
1. Domain: `games`
2. Scene id: `darts`
3. Source task group: `darts`
4. Query id: `total_score`
5. Objective: Choose the visible option letter for the score of the shown dart throw.

## Answer and Evidence
1. Answer type: `string` option letter.
2. Evidence type: `point_set` over the center of the scored dart marker.
3. `total_score` is retained as `query_id`; `query_spec.params.query_id` is internal replay diagnostics.

## Implementation
1. This task uses the shared games scene renderer for its scene id.
2. Prompt bundle: `games_darts_v0`
3. The renderer uses a simplified dartboard with wide scoring bands and large sector numbers to keep scoring regions visually legible.
4. The task draws five score options on the image and asks for the matching option letter; the evidence remains the scored dart marker, not the answer option.
5. Rendering uses the shared games/puzzles panel background layer, sampled text fonts, layout jitter, and six dartboard palette variants.
## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Semantic and render knobs such as dart count, score-option label, style variant, panel style, font family, layout jitter, and target-answer support remain explicit params or trace metadata.

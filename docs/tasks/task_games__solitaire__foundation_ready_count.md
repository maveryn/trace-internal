# `task_games__solitaire__foundation_ready_count`

## Contract
1. Domain: `games`
2. Scene id: `solitaire`
3. Public task id: `task_games__solitaire__foundation_ready_count`
4. Query id: `foundation_ready_count`
5. Objective: Count exposed tableau cards that can move to a foundation pile now.

## Answer and Evidence
1. Answer type: `integer`.
2. Evidence type: `bbox_set` over counted exposed cards and the foundation piles used for the decision.
3. `foundation_ready_count` is retained as `query_id`; `query_spec.params.query_id` is internal replay diagnostics.

## Implementation
1. This task uses the shared `solitaire` renderer with Klondike-like and FreeCell-like layouts.
2. Prompt bundle: `games_solitaire_v0`
3. The scene records foundation tops and exposed-card identities in trace metadata.
4. Rendering combines shared games panel backgrounds, layout jitter, sampled fonts, post-image noise, and five scene-local card/tableau styles.

## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Scene layout, target-answer support, and panel style are explicit params or recorded sampling axes.

# `task_games__solitaire__move_legality_label`

## Contract
1. Domain: `games`
2. Scene id: `solitaire`
3. Public task id: `task_games__solitaire__move_legality_label`
4. Query id: `move_legality_label`
5. Objective: Choose the visible move option that is legal under tableau and foundation move rules.

## Answer and Evidence
1. Answer type: `string` option letter.
2. Evidence type: `keyed_bbox_map` with `source_card` and `target` boxes.
3. `move_legality_label` is retained as `query_id`; `query_spec.params.query_id` is internal replay diagnostics.

## Implementation
1. This task uses the shared `solitaire` renderer with Klondike-like and FreeCell-like layouts.
2. Prompt bundle: `games_solitaire_v0`
3. The renderer draws visible tableau columns, foundation piles, labeled exposed cards, and image-drawn move options.
4. Rendering combines shared games panel backgrounds, layout jitter, sampled fonts, post-image noise, and five scene-local card/tableau styles.

## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Scene layout, answer option position, option count, and panel style are explicit params or recorded sampling axes.

# `task_games__solitaire__tableau_sequence_count`

## Contract
1. Domain: `games`
2. Scene id: `solitaire`
3. Source task group: `solitaire`
4. Query id: `tableau_sequence_count`
5. Objective: Count adjacent visible tableau pairs that already satisfy descending alternating-color order.

## Answer and Evidence
1. Answer type: `integer`.
2. Evidence type: `bbox_set` over cards that belong to counted adjacent tableau pairs.
3. Public `query_variant` is `default`; `tableau_sequence_count` is retained as `query_id` and `query_spec.params.query_variant` for diagnostics.

## Implementation
1. This task uses the shared `solitaire` renderer with Klondike-like and FreeCell-like layouts.
2. Prompt bundle: `games_solitaire_v0`
3. The trace records the counted adjacent card-pair ids as `valid_sequence_pairs`.

## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Scene layout, target-answer support, and panel style are explicit params or recorded sampling axes.

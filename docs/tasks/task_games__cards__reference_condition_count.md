# `task_games__cards__reference_condition_count`

## Contract
1. Domain: `games`
2. Scene id: `cards`
3. Source task group: `cards`
4. Query ids: `same_suit_as_reference_count`, `higher_than_reference_count`
5. Objective: Count non-reference cards satisfying the sampled condition relative to the marked reference card.

## Answer and Evidence
1. Answer type: `integer`
2. Evidence type: `bbox_set` over every counted non-reference card.
3. Public `query_variant` is `default`; the sampled condition is retained as `query_id` and `query_spec.params.query_variant` for diagnostics.

## Implementation
1. This task uses the shared games card renderer with the `multi_row` scene variant.
2. Prompt bundle: `games_cards_v0`

## Determinism
Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.

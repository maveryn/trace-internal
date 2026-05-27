# `task_games__cards__trick_taking_winner_label`

## Contract
1. Domain: `games`
2. Scene id: `cards`
3. Source task group: `cards`
4. Query id: `trick_taking_winner_label`
5. Objective: Choose the player whose played card wins the trick using led-suit and optional trump rules.

## Answer and Evidence
1. Answer type: `string`; the answer is the compact option letter only, such as `A` or `C`, not the full rendered label `Player A`.
2. Evidence type: bbox_set over the single winning played card.
3. The execution trace records both `winning_label` for the full rendered label and `winning_option` for the public answer.
4. Public `query_variant` is `default`; `trick_taking_winner_label` is retained as `query_id` and `query_spec.params.query_variant` for diagnostics.

## Implementation
1. This task uses the shared games card renderer with the `trick_row` scene variant.
2. The leftmost card is the led card. Generation samples 4..6 played cards, an optional trump suit, and enforces a unique winning player.
3. Prompt bundle: `games_cards_v0`

## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Trump rule, style, and visual jitter remain explicit recorded params.

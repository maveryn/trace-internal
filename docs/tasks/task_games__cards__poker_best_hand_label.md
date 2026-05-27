# `task_games__cards__poker_best_hand_label`

## Contract
1. Domain: `games`
2. Scene id: `cards`
3. Source task group: `cards`
4. Query id: `poker_best_hand_label`
5. Objective: Choose the strongest labeled five-card poker hand under standard poker rules.

## Answer and Evidence
1. Answer type: `string`; the answer is the compact option letter only, such as `A` or `C`, not the full rendered label `Hand A`.
2. Evidence type: bbox_set over every card in the winning poker hand.
3. The execution trace records both `winning_label` for the full rendered label and `winning_option` for the public answer.
4. `poker_best_hand_label` is retained as `query_id`; `query_spec.params.query_id` is internal replay diagnostics.

## Implementation
1. This task uses the shared games card renderer with the `poker_multi_hand` scene variant.
2. Generation samples 4..6 labeled five-card hands and rejects ties so the winner is unique by construction.
3. Prompt bundle: `games_cards_v0`

## Determinism
1. Generation is deterministic from `instance_seed`, explicit params, prompt bundle version, and renderer/config versions.
2. Option count, style, and visual jitter remain explicit recorded params.

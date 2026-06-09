# `task_games__solitaire__tableau_sequence_count`

## Contract
1. Domain: `games`
2. Task group: `solitaire`
3. Scene id: `solitaire`
4. Public task id: `task_games__solitaire__tableau_sequence_count`
5. Supported `query_id` values: `tableau_sequence_count`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set`
8. Program schema: `count(tableau_descending_alternating_sequences(tableau_columns)); scene=solitaire; scope=tableau_sequence_count`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.

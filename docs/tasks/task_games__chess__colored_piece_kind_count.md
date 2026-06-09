# `task_games__chess__colored_piece_kind_count`

## Contract
1. Domain: `games`
2. Task group: `chess`
3. Scene id: `chess`
4. Public task id: `task_games__chess__colored_piece_kind_count`
5. Supported `query_id` values: `colored_piece_kind_count`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set`
8. Program schema: `count(filter(pieces, piece_kind=target_kind and piece_color=target_color)); scene=chess; scope=colored_piece_kind_count`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.

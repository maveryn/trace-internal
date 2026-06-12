# `task_games__chess_variant__marked_piece_destination_count`

## Contract
1. Domain: `games`
2. Scene id: `chess_variant`
3. Public task id: `task_games__chess_variant__marked_piece_destination_count`
4. Supported `query_id` values: `marked_piece_capture_count`, `marked_piece_move_count`
5. Answer schema: `integer_count`
6. Annotation schema: `bbox_set`
7. Program schema: `count(filter(legal_destinations(marked_piece), destination_filter)); scene=chess_variant; scope=marked_piece_destination_count`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.

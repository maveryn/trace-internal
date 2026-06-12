# `task_games__checkers__max_capture_chain_length`

## Contract
1. Domain: `games`
2. Scene package: `checkers`
3. Scene id: `checkers`
4. Public task id: `task_games__checkers__max_capture_chain_length`
5. Supported `query_id` values: `default`
6. Answer schema: `integer_value`
7. Annotation schema: `bbox_set`
8. Program schema: `longest_path(capture_state_graph(marked_king, board_state), source=marked_king, target=terminal_no_capture_state); scene=checkers; scope=max_capture_chain_length`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.

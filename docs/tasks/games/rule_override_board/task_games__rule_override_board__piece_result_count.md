# `task_games__rule_override_board__piece_result_count`

## Contract
1. Domain: `games`
2. Scene: `rule_override_board`
3. Scene id: `rule_override_board`
4. Public task id: `task_games__rule_override_board__piece_result_count`
5. Supported `query_id` values: `piece_override_loss_count`, `piece_override_win_count`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set`
8. Program schema: `count(filter(pieces, result_after_rule_override(piece)=override_result)); scene=rule_override_board; scope=piece_result_count; query_branch=piece_override_loss_count`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.

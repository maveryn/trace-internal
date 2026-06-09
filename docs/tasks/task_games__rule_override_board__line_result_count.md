# `task_games__rule_override_board__line_result_count`

## Contract
1. Domain: `games`
2. Task group: `rule_override_board`
3. Scene id: `rule_override_board`
4. Public task id: `task_games__rule_override_board__line_result_count`
5. Supported `query_id` values: `line_override_loss_count`, `line_override_win_count`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set`
8. Program schema: `count(filter(lines, result_after_rule_override(line)=override_result)); scene=rule_override_board; scope=line_result_count; query_branch=line_override_loss_count`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.

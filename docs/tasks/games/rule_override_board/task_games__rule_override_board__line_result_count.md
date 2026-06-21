# `task_games__rule_override_board__line_result_count`

## Program Contract

- Domain: `games`
- Scene: `rule_override_board`
- Public task id: `task_games__rule_override_board__line_result_count`
- Supported `query_id` values: `line_override_win_count`, `line_override_loss_count`
- Answer schema: `integer_count`
- Annotation schema: `bbox_set`
- Program schema: `count(filter(mini_boards, anti_line_result(target_player)=target_result)); scene=rule_override_board; scope=line_result_count`
- Program code: `count.filter.rule_override_line_result`
- Scalar annotation checked: `true`

## Generation Notes

- The prompt states the anti-line rule: a full row, column, or diagonal is a loss for the target player.
- `line_override_win_count` counts mini-boards where the target player wins; `line_override_loss_count` counts losses.
- Annotation bboxes are the counted mini-board panels.
- The answer and annotation are bound from the same generated board state.

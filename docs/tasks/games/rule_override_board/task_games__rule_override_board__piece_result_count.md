# `task_games__rule_override_board__piece_result_count`

## Program Contract

- Domain: `games`
- Scene: `rule_override_board`
- Public task id: `task_games__rule_override_board__piece_result_count`
- Supported `query_id` values: `piece_override_win_count`, `piece_override_loss_count`
- Answer schema: `integer_count`
- Annotation schema: `bbox_set`
- Program schema: `count(filter(mini_boards, fewer_pieces_result(target_player)=target_result)); scene=rule_override_board; scope=piece_result_count`
- Program code: `count.filter.rule_override_piece_result`
- Scalar annotation checked: `true`

## Generation Notes

- The prompt states the fewer-pieces rule: the target player wins by having fewer pieces than the other player.
- `piece_override_win_count` counts mini-boards where the target player wins; `piece_override_loss_count` counts losses.
- Annotation bboxes are the counted mini-board panels.
- The answer and annotation are bound from the same generated board state.

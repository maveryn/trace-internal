# task_games__rule_override_board__line_result_count

1. Domain: `games`
2. Task group: `rule_override_board`
3. Scene id: `rule_override_board`
4. Query ids: `line_override_win_count`, `line_override_loss_count`
5. Objective: count mini-boards where the target player wins or loses under the rule stated in the prompt.

The image shows several small X/O line boards. The prompt states the rule: for the target player, making a full row, column, or diagonal loses; otherwise that player wins.

The answer is an integer from `0..board_count`: the number of mini-boards where the target player has the requested result under the stated rule.

Evidence is `bbox_set`: one bounding box around every counted mini-board. Use an empty set when the answer is `0`. This is a homogeneous count witness, so no keyed evidence is needed.

Generation samples board count from `4..6`, 3x3 or 4x4 board size, target player, win/loss query id, target answer from `0..board_count`, board style, shared canvas treatment, font family, unit scale, and layout jitter.

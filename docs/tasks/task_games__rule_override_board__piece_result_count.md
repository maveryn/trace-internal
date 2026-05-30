# task_games__rule_override_board__piece_result_count

1. Domain: `games`
2. Task group: `rule_override_board`
3. Scene id: `rule_override_board`
4. Query ids: `piece_override_win_count`, `piece_override_loss_count`
5. Objective: count mini-boards where the target player wins or loses under the rule stated in the prompt.

The image shows several small token boards. The prompt states the rule: for the target player, having fewer pieces than the other player wins, and having more pieces loses.

The answer is an integer from `0..board_count`: the number of mini-boards where the target player has the requested result under the stated rule.

Evidence is `bbox_set`: one bounding box around every counted mini-board. Use an empty set when the answer is `0`. This is a homogeneous count witness, so no keyed evidence is needed.

Generation samples board count from `4..6`, 4x4 or 5x5 board size, target player, win/loss query id, target answer from `0..board_count`, board style, shared canvas treatment, font family, unit scale, and layout jitter.

# `task_games__match3__target_clear_swap_label`

## Contract
1. Domain: `games`
2. Scene id: `match3`
3. Public task id: `task_games__match3__target_clear_swap_label`
4. Supported `query_id` values: `single`
5. Answer schema: `option_letter`
6. Annotation schema: `point_set`

## Program Contract
`selection.option_value_match(candidate_set=visible_swap_arrows, option_value=target_clear_count, option_metric=immediate_clear_count_after_arrow_swap); scene=match3; scope=target_clear_swap_label`

## Generation Notes
1. The selected arrow is the only displayed option whose immediate clear count equals the prompted target.
2. The immediate clear rule counts horizontal or vertical runs of three or more after the swap; no falling, refill, special effects, or cascades are applied.
3. Annotation is one point on the selected swap arrow.

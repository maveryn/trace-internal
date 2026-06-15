# `task_games__match3__max_clear_swap_label`

## Contract
1. Domain: `games`
2. Scene id: `match3`
3. Public task id: `task_games__match3__max_clear_swap_label`
4. Supported `query_id` values: `single`
5. Answer schema: `option_letter`
6. Annotation schema: `point_set`

## Program Contract
`selection.extreme_metric_label(candidate_set=visible_swap_arrows, metric=immediate_clear_count_after_arrow_swap, direction=maximum); scene=match3; scope=max_clear_swap_label`

## Generation Notes
1. The selected arrow is the only displayed option with the largest immediate clear count.
2. The immediate clear rule counts horizontal or vertical runs of three or more after the swap; no falling, refill, special effects, or cascades are applied.
3. Annotation is one point on the selected swap arrow.

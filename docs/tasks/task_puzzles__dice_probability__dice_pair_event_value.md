# `task_puzzles__dice_probability__dice_pair_event_value`

## Summary
1. Domain: `puzzles`
2. Task group: `probability`
3. Task id: `task_puzzles__dice_probability__dice_pair_event_value`
4. Scene id: `dice_probability`
5. Goal: compute a reduced-fraction probability for selecting one visible-top die from each of two shown dice trays.

## Contract
1. Branch metadata: `query_id`
2. `query_id`: `pair_sum_probability|pair_sum_threshold_probability|pair_difference_probability|pair_parity_combo_probability|pair_color_value_combo_probability`
3. Dice count per tray: `3..5`
4. Answer type: `string`
5. Evidence type: `bbox_set`
6. Evidence target: the full Tray A box followed by the full Tray B box
7. Scene variants: `dice_tray_clean|dice_tray_felt|dice_tray_notebook`

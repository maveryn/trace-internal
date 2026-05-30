# `task_puzzles__dice_probability__dice_single_event_value`

## Summary
1. Domain: `puzzles`
2. Task group: `probability`
3. Task id: `task_puzzles__dice_probability__dice_single_event_value`
4. Scene id: `dice_probability`
5. Goal: compute a reduced-fraction probability for selecting one visible-top die from a shown dice tray.

## Contract
1. Branch metadata: `query_id`
2. `query_id`: `single_parity_probability|single_threshold_probability|single_value_set_probability|single_color_and_value_probability|single_color_or_value_probability`
3. Dice count: `6..12`
4. Answer type: `string`
5. Evidence type: `keyed_bbox_map`
6. Evidence key: `dice_tray`
7. Scene variants: `dice_tray_clean|dice_tray_felt|dice_tray_notebook`
8. Render metadata records the sampled shared panel style, `dice_visual_style`, tray label font, and the reduced post-image noise policy used to preserve semantic die color and pip readability.

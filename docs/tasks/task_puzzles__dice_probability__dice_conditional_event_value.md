# `task_puzzles__dice_probability__dice_conditional_event_value`

## Summary
1. Domain: `puzzles`
2. Task group: `probability`
3. Task id: `task_puzzles__dice_probability__dice_conditional_event_value`
4. Scene id: `dice_probability`
5. Goal: compute a reduced-fraction conditional probability for selecting one visible-top die from a shown dice tray.

## Contract
1. Public `query_variant`: `default`
2. `query_id`: `conditional_value_property_given_color_probability|conditional_color_given_value_property_probability|conditional_color_given_value_set_probability`
3. Dice count: `8..12`
4. Conditional denominator support: `4..6` visible dice
5. Conditional favorable support: `2..3` visible dice
6. Answer type: `string`
7. Evidence type: `bbox_set`
8. Evidence target: the full dice tray box
9. Scene variants: `dice_tray_clean|dice_tray_felt|dice_tray_notebook`

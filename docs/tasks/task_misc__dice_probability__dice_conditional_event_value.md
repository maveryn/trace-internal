# `task_misc__dice_probability__dice_conditional_event_value`

## Summary
1. Domain: `misc`
2. Task group: `probability`
3. Task id: `task_misc__dice_probability__dice_conditional_event_value`
4. Scene id: `dice_probability`
5. Goal: compute a reduced-fraction conditional probability for selecting one visible-top die from a shown dice tray.

## Contract
1. Branch metadata: `query_id`
2. `query_id`: `conditional_value_property_given_color_probability|conditional_color_given_value_property_probability|conditional_color_given_value_set_probability`
3. Dice count: `8..12`
4. Conditional denominator support: `4..6` visible dice
5. Conditional favorable support: `2..3` visible dice
6. Answer type: `string`
7. Annotation type: `keyed_bbox_map`
8. Annotation key: `dice_tray`
9. Scene variants: `dice_tray_clean|dice_tray_felt|dice_tray_notebook`
10. Render metadata records the sampled shared panel style, `dice_visual_style`, tray label font, and the reduced post-image noise policy used to preserve semantic die color and pip readability.

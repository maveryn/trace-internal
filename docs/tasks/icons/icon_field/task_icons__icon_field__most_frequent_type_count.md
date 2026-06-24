# `task_icons__icon_field__most_frequent_type_count`

## Identity
- domain: `icons`
- scene_id: `icon_field`
- module: `trace/tasks/icons/icon_field/most_frequent_type_count.py`
- prompt bundle: `icons_icon_field_v1`

## Program Contract
`count.group_predicate(scene=icon_field, scope=single_panel_icon_types, groups=icon_type, predicate=unique_most_frequent, output=count)`

Renders one panel with assorted icons and asks how many icons belong to the
unique most frequent icon type.

Query ids:
- `single`: fixed public query id; sampled generation axes are trace metadata.

Answer schema: integer.
Annotation schema: `bbox_set` over the bounding box of every counted icon
instance.
Answer support: `2..6`.

## Notes
The scene enforces exactly one most frequent icon type by construction. Other
singleton and repeated types are distractors with lower frequencies.

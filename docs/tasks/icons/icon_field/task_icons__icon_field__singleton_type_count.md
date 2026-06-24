# `task_icons__icon_field__singleton_type_count`

## Identity
- domain: `icons`
- scene_id: `icon_field`
- module: `trace/tasks/icons/icon_field/singleton_type_count.py`
- prompt bundle: `icons_icon_field_v1`

## Program Contract
`count.group_predicate(scene=icon_field, scope=single_panel_icon_types, groups=icon_type, predicate=singleton, output=count)`

Renders one panel with assorted icons and asks how many icons have a type
that appears exactly once in the panel.

Query ids:
- `single`: fixed public query id; sampled generation axes are trace metadata.

Answer schema: integer.
Annotation schema: `bbox_set` over the bounding box of every counted icon
instance.
Answer support: `0..4`.

## Notes
The scene enforces the requested singleton count by construction, while
repeated icon types serve as distractors.

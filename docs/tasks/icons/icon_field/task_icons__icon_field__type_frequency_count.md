# `task_icons__icon_field__type_frequency_count`

## Identity
- domain: `icons`
- scene_id: `icon_field`
- module: `trace/tasks/icons/icon_field/type_frequency_count.py`
- prompt bundle: `icons_icon_field_v1`

## Program Contract
`count.group_predicate(scene=icon_field, scope=single_panel_icon_types, groups=icon_type, predicates=singleton|unique_most_frequent, output=count)`

Renders one panel with assorted icons and asks for an integer count based
on icon-type frequency.

Query ids:
- `singleton_type_count`: count icons whose type appears exactly once.
- `most_frequent_type_count`: count icons belonging to the unique most frequent type.

Answer schema: integer.
Annotation schema: `bbox_set` over every counted icon instance.
Answer support:
- `singleton_type_count`: `0..4`
- `most_frequent_type_count`: `2..6`

## Notes
The two frequency predicates share the same single-panel icon-field view and
annotation contract. The query id records which predicate was sampled.

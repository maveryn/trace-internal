# `task_icons__named_field__shape_pair_difference_count`

## Identity
- domain: `icons`
- scene_id: `named_field`
- task_group: `counting`
- module: `trace/tasks/icons/counting/named_shape_pair_arithmetic_count.py`
- prompt bundle: `icons_counting_v0`

## Contract
Renders one Scene panel containing procedural named shape icons. The prompt
names two visible icon groups and asks for the absolute difference between their
counts.

Query ids:
- `two_shape_difference_count`
- `two_bound_color_difference_count`

Answer schema: integer.
Evidence schema: `bbox_set` over every icon in either operand group.

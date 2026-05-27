# `task_icons__named_field__shape_pair_total_count`

## Identity
- domain: `icons`
- scene_id: `named_field`
- task_group: `counting`
- module: `trace/tasks/icons/counting/named_shape_pair_arithmetic_count.py`
- prompt bundle: `icons_counting_v0`

## Contract
Renders one Scene panel containing procedural named shape icons. The prompt
names two visible icon groups and asks for their total count.

Query ids:
- `two_shape_total_count`
- `two_bound_color_total_count`

Answer schema: integer.
Evidence schema: `bbox_set` over every icon in either operand group.

# `task_icons__named_field__multi_attribute_or_count`

Status: pending taxonomy-v0 review refresh.

## Identity
- domain: `icons`
- scene_id: `named_field`
- task_group: `counting`
- task: `named_shape_color_boolean_count`
- module: `trace/tasks/icons/counting/named_shape_color_boolean_count.py`
- prompt bundle: `prompts/icons/counting/icons_counting_v0.json`

## Scene And Query
The task renders one panel labeled `Scene` containing procedurally generated
named shape icons. Each icon has a semantic procedural `shape_id`, a semantic
`color_name` sampled from the shared TRACE named-color palette, and a semantic
`fill_style`.

The prompt names one shape and one secondary attribute, then asks for the count
satisfying one Boolean predicate. The secondary attribute axis is sampled with
50% probability from color and 50% probability from fill style. Queryable fill
styles are `striped`, `dotted`, and `half_filled`; `solid` remains a rendered
baseline/distractor style.

Supported Boolean query ids:
- `shape_and_color_count`
- `shape_or_color_count` (inclusive OR: shape, color, or both)
- `shape_and_not_color_count`
- `color_and_not_shape_count`
- `neither_shape_nor_color_count`
- `exactly_one_shape_or_color_count`

The target shape support is the full procedural named-icon vocabulary in
`trace/tasks/icons/shared/procedural_named_icons.py`. Color prompts use the
shared named-color label with hex notation, such as `red [#E63232]`, from
`trace/tasks/shared/named_colors.py`. Fill-style prompts use display labels
from `trace/tasks/icons/shared/procedural_named_icons.py`, such as
`striped`, `dotted`, or `half-filled`.

The scene uses only non-stack named-icon arrangements: jittered/ordered grids,
shelf rows, collision-free scatter, and clusters by shape. Stack arrangements
are intentionally excluded because Boolean shape/attribute membership should be
answered by attribute filtering rather than row/column stack arithmetic.

## Answer Contract
- `answer_gt.type = integer`
- value is the count of icons satisfying the active Boolean predicate
- default answer support is `1..5` for every query id, with lower counts
  sampled more often to keep the task in calibration range

## Annotation Contract
- `annotation_gt.type = bbox_set`
- one `[x0, y0, x1, y1]` pixel bbox for each counted icon
- annotation boxes are sorted in reading order

## Trace Contract
- `scene_ir.entities` contains one entity for each rendered procedural icon.
- Each entity records `shape_id`, prompt-facing `shape_name`, `color_name`,
  `fill_style`, RGB tint, bbox, size, rotation, placement group, row/column layout
  coordinates, and icon-noise metadata.
- `query_spec.params.query_id` records the sampled Boolean predicate.
- `query_spec.params.target_attribute_axis` records whether the secondary
  attribute is `color` or `fill_style`.
- `query_spec.params.partition_counts` records the four target-relative
  partitions: `both`, `shape_only`, `attribute_only`, and `neither`.
- `execution_trace.target_answer` equals the integer answer.
- `render_map.counted_instance_ids`, `witness_symbolic.counted_instance_ids`,
  and `projected_annotation.bbox_set` are derived from the same rendered
  instances.

## Prompt Contract
- `scene_key = single_scene_counting`
- `task_key = counting_query`
- prompts ask for the count of one named shape plus color-or-fill-style
  Boolean condition
- answer-only and answer+annotation modes both include contract-valid JSON
  examples

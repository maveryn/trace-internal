# `task_icons__named_field__multi_attribute_exclusion_count`

## Identity
- domain: `icons`
- scene_id: `named_field`
- task: `multi_attribute_exclusion`
- module: `trace/tasks/icons/named_field/multi_attribute_exclusion_count.py`
- prompt bundle: `prompts/icons/named_field/icons_named_field_v1.json`

## Program Contract
`count.multi_attribute_exclusion(scene=named_field, scope=all_icons, predicates=shape_without_color|color_without_shape, secondary_attribute=color, output=count)`

## Scene And Query
The task renders one panel containing procedurally generated
named shape icons. Each icon has a semantic procedural `shape_id` and a semantic
`color_name` sampled from the shared TRACE named-color palette. Icons may also
render with non-semantic fill patterns (`solid`, `striped`, or `dotted`) as
visual variation, but fill style is not queried by this task.

The prompt names one shape and one color, then asks for the count satisfying
one Boolean predicate.

Supported public query ids:
- `shape_and_not_color_count`: count target-shape icons that do not have the target color.
- `color_and_not_shape_count`: count icons with the target color that are not the target shape.

The selected public query id is also recorded as `query_spec.internal_query_id`
because it directly changes the user-facing exclusion side.

The target shape support is the full procedural named-icon vocabulary in
`trace/tasks/icons/shared/procedural_named_icons.py`. Color prompts use the shared named-color label with hex notation, such as
`red [#E63232]`, from `trace/tasks/shared/named_colors.py`.

The scene uses only non-stack named-icon arrangements: jittered/ordered grids,
shelf rows, collision-free scatter, and clusters by shape. Stack arrangements
are intentionally excluded because Boolean shape/color membership should be
answered by attribute filtering rather than row/column stack arithmetic.

## Answer Contract
- `answer_gt.type = integer`
- value is the count of icons satisfying the selected exclusion predicate
- default answer support is `1..5`, with lower counts sampled more often to
  keep the generated answer distribution stable

## Annotation Contract
- `annotation_gt.type = point_set`
- one `[x, y]` pixel center point for each counted icon
- annotation points are sorted by the witnesses in reading order

## Trace Contract
- `scene_ir.entities` contains one entity for each rendered procedural icon.
- Each entity records `shape_id`, prompt-facing `shape_name`, `color_name`,
  `fill_style`, RGB tint, bbox, size, rotation, placement group, row/column layout
  coordinates, and icon-noise metadata.
- `query_spec.params.query_id` records the selected exclusion predicate.
- `query_spec.params.internal_query_id` mirrors the selected public query id.
- `query_spec.params.target_attribute_axis` records whether the secondary
  attribute is `color` or `fill_style`.
- `query_spec.params.partition_counts` records the four target-relative
  partitions: `both`, `shape_only`, `attribute_only`, and `neither`.
- `execution_trace.target_answer` equals the integer answer.
- `render_map.counted_instance_ids`, `witness_symbolic.counted_instance_ids`,
  and `projected_annotation.point_set` are derived from the same rendered
  instances.

## Prompt Contract
- `scene_key = single_scene_counting`
- `task_key = counting_query`
- prompts ask for the count of one named shape plus color-or-fill-style
  Boolean condition
- answer-only and answer+annotation modes both include contract-valid JSON
  examples

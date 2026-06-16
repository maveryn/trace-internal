# `task_icons__named_field__counterfactual_attribute_count`

## Identity
- domain: `icons`
- scene_id: `named_field`
- task: `named_shape_counterfactual_count`
- module: `trace/tasks/icons/named_field/counterfactual_attribute_count.py`
- prompt bundle: `prompts/icons/named_field/icons_named_field_v1.json`

## Program Contract
`count.counterfactual(scene=named_field, scope=visible_icons, edit=shape_replacement, target=shape_count, output=count)`

## Scene And Query
The task renders one panel containing procedurally generated
named shape icons. The prompt describes a hypothetical edit and asks for the
integer count after applying that edit mentally.

Supported public query ids:
- `single`

The fixed internal hypothetical branch is `target_count_after_shape_replacement`. Trace metadata
records it as `query_spec.internal_query_id` and
`query_spec.params.internal_query_id`; it selects the shape-replacement edit.

The target shape support is the full procedural named-icon vocabulary in
`trace/tasks/icons/shared/procedural_named_icons.py`. Icons also sample a
rendered `fill_style` from `solid`, `striped`, and `dotted`;
fill style is metadata/visual variation only for this task and does not affect
the hypothetical edit semantics.

## Answer Contract
- `answer_gt.type = integer`
- default answer support is `1..8`
- value is the final count after applying the stated hypothetical edit

## Annotation Contract
- `annotation_gt.type = point_set`
- one `[x, y]` pixel center point for every visible icon that contributes to
  the final count
- annotation points are sorted by the witnesses in reading order
- hypothetical additions are intentionally not sampled because they would not
  have visible point annotation

## Trace Contract
- `scene_ir.entities` contains one entity for each rendered procedural icon,
  including its `fill_style`.
- `scene_ir.relations.role_by_instance_id` records each icon's
  counterfactual role and whether it is counted after the edit.
- `query_spec.params.query_id` is `single`.
- `query_spec.params.internal_query_id` records the fixed hypothetical branch.
- `execution_trace.target_answer` equals the integer answer.
- `render_map.counted_instance_ids`, `witness_symbolic.counted_instance_ids`,
  and `projected_annotation.point_set` are derived from the same rendered
  instances.

## Prompt Contract
- `scene_key = single_scene_counting`
- `task_key = counting_query`
- prompts ask for the resulting target-shape count after a replacement edit
- answer-only and answer+annotation modes both include contract-valid JSON
  examples

# `task_icons__named_field__counterfactual_total_count`

Status: pending taxonomy-v0 review refresh.

## Identity
- domain: `icons`
- scene_id: `named_field`
- scene_id: `counting`
- task: `named_shape_counterfactual_count`
- module: `trace/tasks/icons/counting/named_shape_counterfactual_count.py`
- prompt bundle: `prompts/icons/counting/icons_counting_v0.json`

## Scene And Query
The task renders one panel labeled `Scene` containing procedurally generated
named shape icons. The prompt describes a hypothetical edit and asks for the
integer count after applying that edit mentally.

Supported query ids:
- `target_count_after_shape_replacement`: every source-shape icon changes into
  the target shape; answer is existing target-shape icons plus source-shape
  icons.
- `total_count_after_shape_removal`: every remove-shape icon is removed; answer
  is the number of visible icons that would remain.
- `target_count_after_remove_and_replace`: remove-shape icons are removed and
  source-shape icons change into the target shape; answer is the final target
  shape count.

The target shape support is the full procedural named-icon vocabulary in
`trace/tasks/icons/shared/procedural_named_icons.py`. Icons also sample a
rendered `fill_style` from `solid`, `striped`, `dotted`, and `half_filled`;
fill style is metadata/visual variation only for this task and does not affect
the hypothetical edit semantics.

## Answer Contract
- `answer_gt.type = integer`
- default answer support is `1..8`
- value is the final count after applying the stated hypothetical edit

## Annotation Contract
- `annotation_gt.type = bbox_set`
- one `[x0, y0, x1, y1]` pixel bbox for every visible icon that contributes to
  the final count
- annotation boxes are sorted in reading order
- hypothetical additions are intentionally not sampled because they would not
  have visible bbox annotation

## Trace Contract
- `scene_ir.entities` contains one entity for each rendered procedural icon,
  including its `fill_style`.
- `scene_ir.relations.role_by_instance_id` records each icon's
  counterfactual role and whether it is counted after the edit.
- `query_spec.params.query_id` records the selected hypothetical branch.
- `execution_trace.target_answer` equals the integer answer.
- `render_map.counted_instance_ids`, `witness_symbolic.counted_instance_ids`,
  and `projected_annotation.bbox_set` are derived from the same rendered
  instances.

## Prompt Contract
- `scene_key = single_scene_counting`
- `task_key = counting_query`
- prompts ask for the resulting count after a removal or replacement edit
- answer-only and answer+annotation modes both include contract-valid JSON
  examples

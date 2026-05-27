# task_icons__named_field__shape_count

Status: accepted after qwen25vl7b solve-rate calibration.

## Identity
- domain: `icons`
- scene_id: `named_field`
- task_group: `counting`
- task: `named_shape_count`
- module: `trace/tasks/icons/counting/named_shape_count.py`
- prompt bundle: `prompts/icons/counting/icons_counting_v0.json`

## Scene And Query
The task renders one panel labeled `Scene` containing procedurally generated
named shape icons. The prompt names one shape, such as `star`, `crescent`,
`plus sign`, or `lightning bolt`, and asks how many icons of that shape are
present.

The target shape support is the full procedural named-icon vocabulary in
`trace/tasks/icons/shared/procedural_named_icons.py`. Icons also sample a
non-semantic `fill_style` visual attribute from `solid`, `striped`, `dotted`,
and `half_filled`; this varies rendering but is not part of this task's
answer.

The scene samples several internal arrangement modes while keeping the same
public task id and answer contract: jittered/ordered grids, shelf rows,
collision-free scatter, clusters by shape, shape stacks, mixed stacks, and a
target-stack-with-oddballs mode. Stack modes may use moderately larger target counts
because the visual strategy is structural row/column counting rather than
pure visual search. Stack-family renderers place same-group icons as compact
row/column blocks with minimal internal gaps so a queried icon type can be
counted from its stack. The `target_stack_with_oddballs` arrangement renders
only one stack: the target shape icons plus exactly one odd non-target icon in
that same stack, with no additional distractor stacks.

## Answer Contract
- `answer_gt.type = integer`
- value is the count of icons whose `shape_id` equals the target shape
- default answer support is layout-dependent: non-stack layouts use smaller
  counts, and stack layouts are capped at moderate row/column counts

## Evidence Contract
- `evidence_gt.type = bbox_set`
- one `[x0, y0, x1, y1]` pixel bbox for each counted target-shape icon
- evidence boxes are sorted in reading order

## Trace Contract
- `scene_ir.entities` contains one entity for each rendered procedural icon.
- Each entity records `shape_id`, prompt-facing `shape_name`, bbox, size,
  rotation, tint, `fill_style`, placement group, row/column layout
  coordinates, and icon noise metadata.
- `query_spec.params.arrangement_mode` records the sampled arrangement mode.
- `scene_ir.relations.arrangement_details` records stack/oddball details when
  applicable.
- `execution_trace.shape_counts[target_shape_id]` equals the integer answer.
- `render_map.counted_instance_ids`, `witness_symbolic.counted_instance_ids`,
  and `projected_evidence.bbox_set` are derived from the same rendered
  instances.

## Prompt Contract
- `scene_key = single_scene_counting`
- `task_key = counting_query`
- `query_key = named_shape_count`
- prompts ask for the count of one named procedural shape
- answer-only and answer+evidence modes both include contract-valid JSON
  examples

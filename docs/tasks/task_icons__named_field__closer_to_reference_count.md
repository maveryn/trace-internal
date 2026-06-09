# `task_icons__named_field__closer_to_reference_count`

Status: pending taxonomy-v0 review refresh.

## Identity
- domain: `icons`
- scene_id: `named_field`
- task_group: `counting`
- task: `named_shape_closer_to_reference_count`
- module: `trace/tasks/icons/counting/named_shape_closer_to_reference_count.py`
- prompt bundle: `prompts/icons/counting/icons_counting_v0.json`

## Scene And Query
The task renders one panel labeled `Scene` containing two larger reference
icons plus several icons of one prompt-named target shape. The references are
identified in the prompt by icon name, and there are no unrelated distractor
icon types in the scene.

Supported query ids:
- `closer_to_reference_a_count`
- `closer_to_reference_b_count`

The prompt asks how many target-shape icons are closer to one named reference
icon than to the other named reference icon.

## Answer Contract
- `answer_gt.type = integer`
- default answer support is `0..4`
- default total target-icon support is `4..8`

## Annotation Contract
- `annotation_gt.type = bbox_set`
- annotation contains one bbox for every counted target-shape icon
- reference icons are recorded in trace metadata but are not included in the
  counting annotation

## Trace Contract
- `scene_ir.entities` contains two reference entities and all target entities.
- Each target entity stores distances to references `A` and `B`, its closer
  internal reference key, and whether it was counted.
- `query_spec.params.closer_count_by_reference` stores both `A` and `B` counts,
  including zero values.
- `render_map.counted_instance_ids`, `witness_symbolic.counted_instance_ids`,
  and `projected_annotation.bbox_set` are derived from the same rendered target
  entities.
- The reference icons are not visibly letter-labeled; internal `A`/`B` keys are
  used only for trace bookkeeping.

## Prompt Contract
- `scene_key = single_scene_counting`
- `task_key = counting_query`
- prompts ask for the target-shape count closer to one prompt-named reference
  icon than to the other prompt-named reference icon
- answer-only and answer+annotation modes both include contract-valid JSON
  examples

## Current Review Status
Current v0 review and solve-rate artifacts are pending. Browser-review sidecars
belong under
`review/task-reviews/icons/named_field/task_icons__named_field__closer_to_reference_count/`;
solve-rate status is tracked in `review/calibration_sweep_status.json`.

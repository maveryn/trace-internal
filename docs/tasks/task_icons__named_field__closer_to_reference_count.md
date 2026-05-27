# `task_icons__named_field__closer_to_reference_count`

Status: accepted.

## Identity
- domain: `icons`
- scene_id: `named_field`
- task_group: `counting`
- task: `named_shape_closer_to_reference_count`
- module: `trace/tasks/icons/counting/named_shape_closer_to_reference_count.py`
- prompt bundle: `prompts/icons/counting/icons_counting_v0.json`

## Scene And Query
The task renders one panel labeled `Scene` containing two labeled reference
icons, `A` and `B`, plus several icons of one prompt-named target shape. There
are no unrelated distractor icon types in the scene.

Supported query ids:
- `closer_to_reference_a_count`
- `closer_to_reference_b_count`

The prompt asks how many target-shape icons are closer to the queried reference
than to the other reference.

## Answer Contract
- `answer_gt.type = integer`
- default answer support is `0..4`
- default total target-icon support is `4..8`

## Evidence Contract
- `evidence_gt.type = bbox_set`
- evidence contains one bbox for every counted target-shape icon
- reference icons are recorded in trace metadata but are not included in the
  counting evidence

## Trace Contract
- `scene_ir.entities` contains two reference entities and all target entities.
- Each target entity stores distances to references `A` and `B`, its closer
  reference label, and whether it was counted.
- `query_spec.params.closer_count_by_reference` stores both `A` and `B` counts,
  including zero values.
- `render_map.counted_instance_ids`, `witness_symbolic.counted_instance_ids`,
  and `projected_evidence.bbox_set` are derived from the same rendered target
  entities.

## Prompt Contract
- `scene_key = single_scene_counting`
- `task_key = counting_query`
- prompts ask for the target-shape count closer to reference `A` or `B`
- answer-only and answer+evidence modes both include contract-valid JSON
  examples

## Calibration
- qwen25vl7b `100 x 24`, seed `20260507`: hard `0.130`, easy `0.020`,
  mean solve rate `0.250`, response cap `0.000`, prompt max `121`
- distribution gate: `5` unique answers, max answer frequency `0.280`

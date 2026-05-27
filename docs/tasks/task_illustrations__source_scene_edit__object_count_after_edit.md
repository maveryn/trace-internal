# task_illustrations__source_scene_edit__object_count_after_edit

Status: accepted after qwen25vl7b solve-rate calibration.

## Taxonomy
- domain: `illustrations`
- task_group: `counterfactual`
- scene_id: `source_scene_edit`
- module: `trace/tasks/illustrations/counterfactual/object_count_after_edit.py`

## Contract
The task renders one accepted illustration source scene with a known current
count of a named target object. The prompt asks for the resulting count after a
hypothetical add or remove edit.

Public variants:
- `after_added_k_objects_count`
- `after_removed_k_objects_count`

The edit count `K` is sampled internally from `1..3`. Source scenes and targets
are sampled from visually readable whole-object counting tasks, avoiding dense
book/window-style counts.

## Answer And Evidence
- `answer_gt.type = integer`
- `evidence_gt.type = bbox_set`
- evidence contains one pixel-space bbox for every currently visible target
  object before the hypothetical edit

For add variants, the hypothetical new object has no bbox because it is not
drawn. For remove variants, no specific object is selected for removal, so
evidence includes all current target objects.

## Trace
The trace stores `current_count`, `edit_count_k`, `edit_operation`,
`result_count`, source scene metadata, and current target bboxes. The verifier
source of truth is the source task evidence plus the sampled hypothetical edit,
not pixels alone.

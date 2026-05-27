# task_illustrations__difference_pair__object_difference_count

Status: pending fresh v0 task review and solve-rate calibration.

## Taxonomy
- domain: `illustrations`
- task_group: `visual`
- scene_id: `difference_pair`
- task: `object_difference_count`
- module: `trace/tasks/illustrations/visual/object_difference_count.py`

## Contract
The task shows two panels, `Scene A` and `Scene B`, and asks for the count of
object-level differences. Query ids are `added_object_count`,
`removed_object_count`, `changed_color_object_count`, and `moved_object_count`.

## Answer And Evidence
- `answer_gt.type = integer`
- `evidence_gt.type = bbox_set`
- evidence is one final-image pixel bbox per changed object
- added, moved, and color-changed evidence boxes are from `Scene B`
- removed-object evidence boxes are from `Scene A`

The answer and evidence are generated from the same placement records used to
render the paired panels.

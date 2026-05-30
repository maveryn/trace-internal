# task_illustrations__difference_pair__object_difference_count

Status: reviewed_pending_probe. Fresh v0 task review regenerated; solve-rate
calibration pending.

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
Moved-object instances enforce a minimum center displacement so the visual
difference is not just small placement jitter.

## Answer And Evidence
- `answer_gt.type = integer`
- `evidence_gt.type = bbox_set`
- evidence is one final-image pixel bbox per changed object
- added, moved, and color-changed evidence boxes are from `Scene B`
- removed-object evidence boxes are from `Scene A`
- `bbox_set` is intentional: the witnesses are homogeneous counted objects
  within each query instance, so keyed role binding is not needed.

The answer and evidence are generated from the same placement records used to
render the paired panels.

## Prompt And Rendering Notes
- Scene A/B labels use one sampled family from the role-appropriate shared font pool,
  recorded in `render_spec.style.panel_label_font`.
- The prompt evidence hint asks for boxes around the objects counted by the
  question and states the Scene A exception for removed objects.

## Calibration Notes
- Fresh artifact review on 2026-05-28 regenerated
  `review/task-reviews/illustrations/difference_pair/scene_review.xlsx`.
- Distribution review passed for all four query ids.
- Solve-rate calibration remains pending.

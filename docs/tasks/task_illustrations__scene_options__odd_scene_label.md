# task_illustrations__scene_options__odd_scene_label

Status: reviewed pending solve-rate calibration.

## Taxonomy
- domain: `illustrations`
- task_group: `visual`
- scene_id: `scene_options`
- task: `odd_scene_label`
- module: `trace/tasks/illustrations/visual/odd_scene_label.py`

## Contract
The task shows six labeled illustration panels. All panels are rendered from
the same illustration source query. Five panels contain the same number of the
named target, and one panel contains a different number. The query asks for the
label of the odd panel.

The task records `query_id=odd_scene_label`.

## Answer And Evidence
- `answer_gt.type = option_letter`
- `evidence_gt.type = bbox_set`
- evidence contains one final-image pixel bbox around the full selected odd
  panel image

Source panels are sampled from current illustration scene renderers using
controlled target-count overrides. The verifier source of truth is the sampled
odd option and its target count, not pixel analysis. Default source queries use
environment, park/playground, and construction-site canvases.

Option labels use the role-appropriate shared font pool with one consistent label font
per generated option set. Option frame style is sampled and recorded in
`render_spec.style`.

Fresh v0 review artifacts:
- `review/task-reviews/illustrations/scene_options/scene_review.xlsx`
- `review/task-reviews/illustrations/scene_options/task_illustrations__scene_options__odd_scene_label/task_illustrations__scene_options__odd_scene_label.xlsx`

Solve-rate calibration remains pending.

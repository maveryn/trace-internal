# task_illustrations__missing_patch__missing_patch_label

Status: reviewed_pending_probe. Fresh v0 task review regenerated; solve-rate
calibration pending.

## Taxonomy
- domain: `illustrations`
- task_group: `visual`
- scene_id: `missing_patch`
- task: `missing_patch_label`
- module: `trace/tasks/illustrations/visual/missing_patch_label.py`

## Contract
The task shows a source illustration with one blacked-out missing region and
labeled patch options. The default render uses six options, with explicit
`option_count=4` still supported for 2x2 option-grid checks. Query ids are `plain_patch_label`,
`transformed_patch_label`, and `irregular_cutout_patch_label`. All missing
regions are axis-aligned rectangles; no cutout uses diagonal or diamond-shaped
edges.

For `transformed_patch_label`, the correct option may need to be mentally
rotated or reflected before fitting the missing region.

## Answer And Evidence
- `answer_gt.type = option_letter`
- `evidence_gt.type = keyed_bbox_map`
- evidence keys are:
  - `missing_region`: the missing region in the Source panel
  - `selected_option`: the selected option image

Keyed evidence is intentional because the two boxes have distinct semantic
roles; an unordered `bbox_set` would not bind the Source witness to the option
witness.

Source illustrations are sampled from current illustration scene renderers,
excluding `object_field`. Missing regions keep a minimum configured margin
from the source-image boundary.

## Prompt And Rendering Notes
- The prompt asks for evidence as a JSON object keyed by `missing_region` and
  `selected_option`.
- Source and option labels use one sampled family from the readout font
  pool, recorded in `render_spec.style.label_font`.
- Non-semantic frame style variation is recorded in
  `render_spec.style.frame_style`.

## Calibration Notes
- Fresh artifact review on 2026-05-28 regenerated
  `review/task-reviews/illustrations/missing_patch/scene_review.xlsx`.
- Distribution review passed for all three query ids.
- Solve-rate calibration remains pending.

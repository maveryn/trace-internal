# task_illustrations__missing_patch__missing_patch_label

Status: accepted after qwen25vl7b solve-rate calibration.

## Taxonomy
- domain: `illustrations`
- task_group: `visual`
- scene_id: `missing_patch`
- task: `missing_patch_label`
- module: `trace/tasks/illustrations/visual/missing_patch_label.py`

## Contract
The task shows a source illustration with one blacked-out missing region and
four labeled patch options. Public variants are `plain_patch_label`,
`transformed_patch_label`, and `irregular_cutout_patch_label`. All missing
regions are axis-aligned rectangles; no cutout uses diagonal or diamond-shaped
edges.

For `transformed_patch_label`, the correct option may need to be mentally
rotated or reflected before fitting the missing region.

## Answer And Evidence
- `answer_gt.type = option_letter`
- `evidence_gt.type = bbox_set`
- evidence contains two final-image pixel bboxes:
  - the missing region in the Source panel
  - the selected option panel

Source illustrations are sampled from accepted illustration scene renderers,
excluding `object_field` and `market`. Missing regions keep
a minimum configured margin from the source-image boundary.

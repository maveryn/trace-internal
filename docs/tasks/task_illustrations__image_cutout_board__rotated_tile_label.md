# task_illustrations__image_cutout_board__rotated_tile_label

Status: accepted after qwen25vl7b solve-rate calibration.

## Taxonomy
- domain: `illustrations`
- task_group: `visual`
- scene_id: `image_cutout_board`
- task: `rotated_tile_label`
- module: `trace/tasks/illustrations/visual/rotated_tile_label.py`

## Contract
The task renders one accepted illustration source scene, fits it to a square
image, cuts it into a labeled `3x3` tile grid, and rotates exactly one tile in
place. The answer is the label of the rotated tile.

The source pool matches the illustration jigsaw-order task:
`market`, `library`, `park_playground`, and
`construction_site`.

## Answer And Evidence
- `answer_gt.type = option_letter`
- `evidence_gt.type = bbox_set`
- evidence contains one final-image pixel bbox around the rotated tile

The verifier source of truth is the sampled rotated-tile record and its
projected grid-cell bbox. The source image is used only to render the visible
tile content; the verifier does not infer from pixels.

# task_illustrations__image_cutout_board__rotated_tile_label

Status: reviewed_pending_probe. Fresh v0 task review regenerated; solve-rate
calibration pending.

## Taxonomy
- domain: `illustrations`
- task_group: `visual`
- scene_id: `image_cutout_board`
- task: `rotated_tile_label`
- module: `trace/tasks/illustrations/visual/rotated_tile_label.py`

## Contract
The task renders one current illustration source scene, fits it to a square
image, cuts it into a labeled `3x3` tile grid, and rotates exactly one tile in
place. The answer is the label of the rotated tile.

The source pool matches the illustration jigsaw-order task:
`library`, `park_playground`, and `construction_site`.

## Answer And Evidence
- `answer_gt.type = option_letter`
- `evidence_gt.type = bbox_set`
- evidence contains one final-image pixel bbox around the whole selected
  rotated tile

The verifier source of truth is the sampled rotated-tile record and its
projected grid-cell bbox. The source image is used only to render the visible
tile content; the verifier does not infer from pixels.

## Prompt And Rendering Notes
- Tile labels use one sampled family from the role-appropriate shared font pool,
  recorded in `render_spec.style.tile_label_font`.
- Non-semantic grid style variation is recorded in
  `render_spec.style.grid_style`.
- The prompt evidence hint asks for the whole rotated grid tile.

## Calibration Notes
- Fresh artifact review on 2026-05-28 regenerated
  `review/task-reviews/illustrations/image_cutout_board/scene_review.xlsx`.
- Distribution review passed.
- Solve-rate calibration remains pending.

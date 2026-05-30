# task_illustrations__image_cutout_board__jigsaw_piece_order

Status: reviewed_pending_probe. Fresh v0 task review regenerated; solve-rate
calibration pending.

## Taxonomy
- domain: `illustrations`
- task_group: `visual`
- scene_id: `image_cutout_board`
- task: `jigsaw_piece_order`
- module: `trace/tasks/illustrations/visual/jigsaw_piece_order.py`

## Contract
The task shows a partial reconstruction board with one piece already anchored
in its original position. The original full image is not displayed. The
remaining pieces are shuffled and labeled below the board. The query asks for
the labels in the specified empty-cell order.

Supported board-shape variants are:
- `board_1x3`: left cell anchored; answer order is middle, right.
- `board_2x2`: top-left cell anchored; answer order is top-right,
  bottom-left, bottom-right.

Default sampling uses equal weight across the two board shapes.
For `board_2x2`, random option display order excludes the already-correct
top-right, bottom-left, bottom-right order.

## Answer And Evidence
- `answer_gt.type = string`
- the answer is a space-separated label string, for example `2 1` or `2 1 3`
- `evidence_gt.type = bbox_sequence`
- evidence is the displayed piece-option bboxes in the same order as the answer
- this is a true visual option-image task, so option-image bboxes are the
  minimal prompt-facing witnesses; label badges are not used as evidence

Source illustrations are sampled from current illustration scene renderers,
excluding `object_field`.

## Prompt And Rendering Notes
- The prompt states the empty-cell order explicitly.
- Option label badges use one sampled family from the role-appropriate shared font pool,
  recorded in `render_spec.style.option_label_font`.
- Non-semantic board style variation is recorded in
  `render_spec.style.board_style`.

## Calibration Notes
- Fresh artifact review on 2026-05-28 regenerated
  `review/task-reviews/illustrations/image_cutout_board/scene_review.xlsx`.
- Distribution review passed.
- Solve-rate calibration remains pending.

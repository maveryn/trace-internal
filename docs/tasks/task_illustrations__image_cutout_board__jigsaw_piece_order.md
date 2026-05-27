# task_illustrations__image_cutout_board__jigsaw_piece_order

Status: accepted after qwen25vl7b solve-rate calibration.

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

## Answer And Evidence
- `answer_gt.type = string`
- the answer is a space-separated label string, for example `2 1` or `2 1 3`
- `evidence_gt.type = bbox_sequence`
- evidence is the displayed piece-option bboxes in the same order as the answer

Source illustrations are sampled from accepted illustration scene renderers,
excluding `object_field`.

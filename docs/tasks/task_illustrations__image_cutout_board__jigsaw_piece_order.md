# `task_illustrations__image_cutout_board__jigsaw_piece_order`

## Summary
- Domain: `illustrations`
- Scene id: `image_cutout_board`
- Implementation scene package: `image_cutout_board`
- Implementation source: `trace/tasks/illustrations/image_cutout_board/jigsaw_piece_order.py`
- Contract-v0 migration decision: `keep`
- Public mapping: `task_illustrations__image_cutout_board__jigsaw_piece_order` -> `task_illustrations__image_cutout_board__jigsaw_piece_order`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Returns the option-label sequence needed to reconstruct the source image layout.

This public task id is a stable contract-v0 unit: one renderer scene id plus one objective contract. Query ids may vary only narrow operands or parameters inside that same program contract.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `jigsaw_piece_order` | `sequence(order_pieces_by_reconstruction(piece_options, completed_image_layout, anchor_position)); scene=image_cutout_board; scope=jigsaw_piece_order` |

## Program Metadata
- Program signatures: `sequence.reconstruction_order`
- Base program contract: `sequence(order_pieces_by_reconstruction(piece_options, completed_image_layout, anchor_position)); scene=image_cutout_board; scope=jigsaw_piece_order`
- Parameter axes: `fixed_query`
- Arguments:
  - `anchor_position`: semantic_role; allowed `sampled_anchor_position`; source `program_schema_concrete`
  - `completed_image_layout`: semantic_role; allowed `completed_illustration_layout`; source `program_schema_concrete`
  - `piece_options`: semantic_role; allowed `visible_labeled_piece_options`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `jigsaw_piece_order`

## Answer Contract
- Answer schema: `string_label`
- Generator `answer_gt.type`: `string`
- The answer value is the required label string/sequence specified by the task contract.

## Annotation Contract
- Annotation schema: `bbox_sequence`
- Generator `annotation_gt.type`: `bbox_sequence`
- Annotation is an ordered sequence of final-image pixel boxes whose order binds to the answer sequence.
- Annotation and answer must be projected from the same generated scene trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the illustrations prompt bundles, with scene and task/query layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, query operands, and verifier payloads must be explicit in the instance trace.
- Distractor/context text may be rendered only when it is part of the scene grammar and must not be treated as annotation unless it is the queried visual witness.

## Review Artifacts
- Task review artifacts: `review/task-reviews/illustrations/image_cutout_board/task_illustrations__image_cutout_board__jigsaw_piece_order/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.

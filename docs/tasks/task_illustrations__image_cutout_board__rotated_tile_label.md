# `task_illustrations__image_cutout_board__rotated_tile_label`

## Summary
- Domain: `illustrations`
- Scene id: `image_cutout_board`
- Implementation scene package: `image_cutout_board`
- Implementation source: `trace/tasks/illustrations/image_cutout_board/rotated_tile_label.py`
- Contract-v0 migration decision: `keep`
- Public mapping: `task_illustrations__image_cutout_board__rotated_tile_label` -> `task_illustrations__image_cutout_board__rotated_tile_label`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Selects the rotated tile label that satisfies the visual query over the image-cutout board.

This public task id is a stable contract-v0 unit: one renderer scene id plus one objective contract. Query ids may vary only narrow operands or parameters inside that same program contract.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `rotated_tile_label` | `label(select_tile(grid_tiles, tile_rotation_mismatch(tile)=target_rotation)); scene=image_cutout_board; scope=rotated_tile_label` |

## Program Metadata
- Program signatures: `selection.direct_label`
- Base program contract: `label(select_tile(grid_tiles, tile_rotation_mismatch(tile)=target_rotation)); scene=image_cutout_board; scope=rotated_tile_label`
- Parameter axes: `fixed_query`
- Arguments:
  - `grid_tiles`: semantic_role; allowed `visible_labeled_grid_tiles`; source `program_schema_concrete`
  - `target_rotation`: semantic_role; allowed `sampled_rotation_degrees`; source `program_schema_concrete`
  - `tile`: semantic_role; allowed `grid_tile`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `rotated_tile_label`

## Answer Contract
- Answer schema: `option_letter`
- Generator `answer_gt.type`: `option_letter`
- The answer value is the selected visible option letter.

## Annotation Contract
- Annotation schema: `bbox_set`
- Generator `annotation_gt.type`: `bbox_set`
- Annotation is an unordered set of final-image pixel boxes, one per counted/selected visual witness. Do not include labels, numeric annotations, or context-only regions.
- Annotation and answer must be projected from the same generated scene trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the illustrations prompt bundles, with scene and task/query layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, query operands, and verifier payloads must be explicit in the instance trace.
- Distractor/context text may be rendered only when it is part of the scene grammar and must not be treated as annotation unless it is the queried visual witness.

## Review Artifacts
- Task review artifacts: `review/task-reviews/illustrations/image_cutout_board/task_illustrations__image_cutout_board__rotated_tile_label/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.

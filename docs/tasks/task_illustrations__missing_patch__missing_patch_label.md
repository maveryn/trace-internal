# `task_illustrations__missing_patch__missing_patch_label`

## Summary
- Domain: `illustrations`
- Scene id: `missing_patch`
- Implementation task group: `visual`
- Implementation source: `trace/tasks/illustrations/visual/missing_patch_label.py`
- Contract-v0 migration decision: `keep`
- Public mapping: `task_illustrations__missing_patch__missing_patch_label` -> `task_illustrations__missing_patch__missing_patch_label`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Selects the option patch that matches the missing source-image region.

This public task id is a stable contract-v0 unit: one renderer scene id plus one objective contract. Query ids may vary only narrow operands or parameters inside that same program contract.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `irregular_cutout_patch_label` | `label(select_option(candidate_patches, fills_missing_region(candidate_patch, source_image_with_hole, transform_mode))); scene=missing_patch; scope=missing_patch_label; query_branch=irregular_cutout_patch_label` |
| `plain_patch_label` | `label(select_option(candidate_patches, fills_missing_region(candidate_patch, source_image_with_hole, transform_mode))); scene=missing_patch; scope=missing_patch_label; query_branch=plain_patch_label` |
| `transformed_patch_label` | `label(select_option(candidate_patches, fills_missing_region(candidate_patch, source_image_with_hole, transform_mode))); scene=missing_patch; scope=missing_patch_label; query_branch=transformed_patch_label` |

## Program Metadata
- Program signatures: `selection.option_match`
- Base program contract: `label(select_option(candidate_patches, fills_missing_region(candidate_patch, source_image_with_hole, transform_mode))); scene=missing_patch; scope=missing_patch_label`
- Parameter axes: `fixed_query`
- Arguments:
  - `candidate_patch`: semantic_role; allowed `candidate_patch_option`; source `program_schema_concrete`
  - `candidate_patches`: semantic_role; allowed `visible_patch_options`; source `program_schema_concrete`
  - `source_image_with_hole`: semantic_role; allowed `source_image_with_missing_region`; source `program_schema_concrete`
  - `transform_mode`: semantic_role; allowed `irregular_cutout`, `plain_patch`, `transformed_patch`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `irregular_cutout_patch_label`, `plain_patch_label`, `transformed_patch_label`

## Answer Contract
- Answer schema: `option_letter`
- Generator `answer_gt.type`: `option_letter`
- The answer value is the selected visible option letter.

## Annotation Contract
- Annotation schema: `keyed_bbox_map`
- Generator `annotation_gt.type`: `keyed_bbox_map`
- Annotation is keyed because witness roles are distinct; each key maps to the minimal final-image pixel box for that role.
- Annotation and answer must be projected from the same generated scene trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the illustrations prompt bundles, with scene and task/query layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, query operands, and verifier payloads must be explicit in the instance trace.
- Distractor/context text may be rendered only when it is part of the scene grammar and must not be treated as annotation unless it is the queried visual witness.

## Review Artifacts
- Task review artifacts: `review/task-reviews/illustrations/missing_patch/task_illustrations__missing_patch__missing_patch_label/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.

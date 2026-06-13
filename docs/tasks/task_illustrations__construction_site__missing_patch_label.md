# `task_illustrations__construction_site__missing_patch_label`

## Summary
- Domain: `illustrations`
- Scene id: `construction_site`
- Implementation scene: `construction_site`
- Implementation source: `trace/tasks/illustrations/construction_site/missing_patch_label.py`
- Contract-v0 migration decision: `add`
- Public mapping: `task_illustrations__construction_site__missing_patch_label` -> `task_illustrations__construction_site__missing_patch_label`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Renders a construction-site source panel with one missing visual region and four or six same-size lettered patch options. The model selects the option letter that restores the missing region.

This public task id is a stable scene-owned visual-option contract. Query ids vary only whether the correct option is an exact crop or a transformed crop.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `plain_patch_label` | `select_option(match_patch(source_image, missing_region, options, transform=none)); scene=construction_site; scope=missing_patch_label` |
| `transformed_patch_label` | `select_option(match_patch(source_image, missing_region, options, transform=rotation_or_reflection)); scene=construction_site; scope=missing_patch_label` |

## Program Metadata
- Program signatures: `visual.patch_option_match`
- Base program contract: `select_option(match_patch(source_image, missing_region, options)); scene=construction_site; scope=missing_patch_label`
- Parameter axes: `patch_transform_mode`
- Supported query ids: `plain_patch_label`, `transformed_patch_label`

## Answer Contract
- Answer schema: `option_letter`
- Generator `answer_gt.type`: `option_letter`
- The answer value is one of the visible option letters.

## Annotation Contract
- Annotation schema: `keyed_bbox_map`
- Generator `annotation_gt.type`: `keyed_bbox_map`
- Annotation keys are `missing_region` and `selected_option`.
- Annotation boxes are final-image pixel boxes around the missing source region and the selected patch option. Do not include all options, labels, or context-only source objects.

## Prompt And Trace Requirements
- Prompt text must come from the `illustrations_construction_site_v1` scene prompt bundle, with scene/task/output layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, patch mode, option order, crop box, selected transform, and verifier payloads must be explicit in the instance trace.
- Option count is sampled from `4` or `6`; all option bboxes use the same pixel width and height as the missing region.
- Source-zone text labels are suppressed in this reconstruction view so the task is patch matching rather than text matching.
- The selected option bbox, answer label, and missing-region bbox must all come from the same `compose_patch_options` execution trace.

## Review Artifacts
- Task review artifacts: `review/task-reviews/illustrations/construction_site/task_illustrations__construction_site__missing_patch_label/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.

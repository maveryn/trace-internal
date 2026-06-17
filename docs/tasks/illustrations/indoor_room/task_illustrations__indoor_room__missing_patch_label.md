# `task_illustrations__indoor_room__missing_patch_label`

## Summary
- Domain: `illustrations`
- Scene id: `indoor_room`
- Implementation scene package: `indoor_room`
- Implementation source: `trace/tasks/illustrations/indoor_room/missing_patch_label.py`

## Task Contract
Renders an indoor-room source panel with one missing visual region and four or six same-size lettered patch options. The model selects the option letter that exactly restores the missing region.

## Program Contract
`select_option(match_patch(source_image, missing_region, options, transform=none)); scene=indoor_room; scope=missing_patch_label`

## Query Branches

| Query id | Program schema |
| --- | --- |
| `single` | `select_option(match_patch(source_image, missing_region, options, transform=none)); scene=indoor_room; scope=missing_patch_label` |

## Program Metadata
- Program signatures: `selection.option_match`
- Base program contract: `select_option(match_patch(source_image, missing_region, options, transform=none)); scene=indoor_room; scope=missing_patch_label`
- Parameter axes: `theme_id`, `source_object_count`, `option_count`
- Arguments:
  - `source_image`: semantic_role; allowed `indoor_room_source_panel`; source `program_schema_concrete`
  - `missing_region`: semantic_role; allowed `masked_source_region`; source `program_schema_concrete`
  - `options`: semantic_role; allowed `lettered_patch_options`; source `program_schema_concrete`
  - `transform`: operation_parameter; allowed `none`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `single`

## Answer Contract
- Answer schema: `option_letter`
- Generator `answer_gt.type`: `option_letter`
- The answer value is one of the visible option letters.

## Annotation Contract
- Annotation schema: `bbox_map`
- Generator `annotation_gt.type`: `bbox_map`
- Annotation keys are `missing_region` and `selected_option`.
- Annotation boxes are final-image pixel boxes around the missing source region and the selected patch option. Do not include all options, labels, source objects, furniture, or context-only regions.

## Prompt And Trace Requirements
- Prompt text must come from the `illustrations_indoor_room_v0` prompt bundle, with scene/task/output layers selected deterministically and recorded in metadata.
- Render randomness, sampled room theme/style, option order, crop box, and verifier payloads must be explicit in the instance trace.
- Option count is sampled from `4` or `6`; all option bboxes use the same pixel width and height as the missing region.
- The selected option bbox, answer label, and missing-region bbox must all come from the same `compose_patch_options` execution trace.

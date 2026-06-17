# `task_illustrations__park_playground__missing_patch_label`

## Summary
- Domain: `illustrations`
- Scene id: `park_playground`
- Implementation scene package: `park_playground`
- Implementation source: `trace/tasks/illustrations/park_playground/missing_patch_label.py`

## Task Contract
Render a park/playground source panel with one missing visual region and four or six lettered patch options. The model selects the option letter that restores the missing region.

## Program Contract
`select_option(match_patch(source_image, missing_region, options)); scene=park_playground; scope=missing_patch_label`

## Query Branches

| Query id | Program schema |
| --- | --- |
| `single` | `select_option(match_patch(source_image, missing_region, options, transform=none)); scene=park_playground; scope=missing_patch_label` |

## Program Metadata
- Program signatures: `selection.option_match`
- Base program contract: `select_option(match_patch(source_image, missing_region, options)); scene=park_playground; scope=missing_patch_label`
- Parameter axes: `none`
- Arguments:
  - `source_image`: semantic role; allowed `park_playground_source_panel`; source `program_schema_concrete`
  - `missing_region`: semantic role; allowed `masked_source_region`; source `program_schema_concrete`
  - `options`: semantic role; allowed `lettered_patch_options`; source `program_schema_concrete`
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
- Annotation boxes are final-image pixel boxes around the missing source region and the selected patch option. Do not include all options, labels, or context-only source objects.

## Prompt And Trace Requirements
- Prompt text comes from `prompts/illustrations/park_playground/illustrations_park_playground_v0.json`.
- Render randomness, sampled fonts/styles, option order, crop box, and verifier payloads are explicit in the instance trace.
- Option count is sampled from `4` or `6`; option bboxes are keyed by their visible letter in `render_map`.
- The selected option bbox, answer label, and missing-region bbox must all come from the same `compose_patch_options` execution trace.

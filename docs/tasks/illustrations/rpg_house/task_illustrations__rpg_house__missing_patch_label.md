# `task_illustrations__rpg_house__missing_patch_label`

## Summary
- Domain: `illustrations`
- Scene id: `rpg_house`
- Implementation scene package: `rpg_house`
- Implementation source: `trace/tasks/illustrations/rpg_house/missing_patch_label.py`

## Task Contract
Render a top-down RPG house source panel with one missing rectangular region and four or six lettered patch options. The model selects the option letter that restores the missing region.

## Program Contract
`select_option(match_patch(source_image, missing_region, options, transform=none)); scene=rpg_house; scope=missing_patch_label`

## Query Branches

| Query id | Program schema |
| --- | --- |
| `single` | `select_option(match_patch(source_image, missing_region, options, transform=none)); scene=rpg_house; scope=missing_patch_label` |

## Program Metadata
- Program signatures: `selection.option_match`
- Base program contract: `select_option(match_patch(source_image, missing_region, options, transform=none)); scene=rpg_house; scope=missing_patch_label`
- Parameter axes: `source_room_count`, `option_count`, `crop_box`, `canvas_profile`
- Arguments:
  - `source_image`: semantic role; allowed `rpg_house_source_panel`; source `program_schema_concrete`
  - `missing_region`: semantic role; allowed `masked_source_region`; source `program_schema_concrete`
  - `options`: semantic role; allowed `lettered_patch_options`; source `program_schema_concrete`
  - `canvas_profile`: render parameter; allowed `landscape`, `square`, `portrait`; source `trace_metadata`
- Argument metadata status: `curated`
- Supported query ids: `single`

## Answer Contract
- Answer schema: `option_letter`
- Generator `answer_gt.type`: `option_letter`
- The answer value is one of the visible patch option letters.

## Annotation Contract
- Annotation schema: `bbox_map`
- Generator `annotation_gt.type`: `bbox_map`
- Annotation keys are `missing_region` and `selected_option`.
- Annotation boxes are final-image pixel boxes around the missing source region and selected patch option. Do not include all options, option labels, room fixtures, or context-only source objects.

## Prompt And Trace Requirements
- Prompt text must come from `prompts/illustrations/rpg_house/illustrations_rpg_house_v0.json`.
- Render randomness, source room count, sampled label font, option order, crop box, and verifier payloads must be explicit in the instance trace.
- Patch crops are sampled from visible room, door, or fixture regions to avoid blank floor-only ambiguity.
- The selected option bbox, answer label, and missing-region bbox must all come from the same `compose_patch_options` execution trace.

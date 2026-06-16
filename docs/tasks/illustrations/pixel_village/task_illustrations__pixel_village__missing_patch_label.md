# `task_illustrations__pixel_village__missing_patch_label`

## Summary
- Domain: `illustrations`
- Scene id: `pixel_village`
- Implementation scene package: `pixel_village`
- Implementation source: `trace/tasks/illustrations/pixel_village/missing_patch_label.py`

## Task Contract
Renders a pixel-village source panel with one missing visual region and four or six same-size lettered patch options. The model selects the option letter that exactly restores the missing region.

## Program Contract
`select_option(match_patch(source_image, missing_region, options, transform=none)); scene=pixel_village; scope=missing_patch_label`

## Query Branches

| Query id | Program schema |
| --- | --- |
| `single` | `select_option(match_patch(source_image, missing_region, options, transform=none)); scene=pixel_village; scope=missing_patch_label` |

## Program Metadata
- Program signatures: `selection.option_match`
- Base program contract: `select_option(match_patch(source_image, missing_region, options, transform=none)); scene=pixel_village; scope=missing_patch_label`
- Parameter axes: `option_count`, `patch_size`, `source_size`, `canvas_profile`
- Arguments:
  - `source_image`: semantic_role; allowed `pixel_village_source_panel`; source `program_schema_concrete`
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
- Annotation schema: `keyed_bbox_map`
- Generator `annotation_gt.type`: `keyed_bbox_map`
- Annotation keys are `missing_region` and `selected_option`.
- Annotation boxes are final-image pixel boxes around the missing source region and the selected patch option. Do not include all options, option labels, village entities, territories, or context-only regions.

## Prompt And Trace Requirements
- Prompt text must come from `prompts/illustrations/pixel_village/illustrations_pixel_village_v0.json`.
- Runtime query id is the single-query sentinel `single`; option count, patch size, crop box, style, source render modes, and option-label font are trace parameters.
- The composed image uses a frameless functional layout: no source-panel title, decorative outer border, option-card outline, or extra scene background.
- The selected option bbox, answer label, missing-region bbox, and crop boxes must all come from the same `compose_patch_options` execution trace.

# `task_illustrations__pixel_village__jigsaw_arrangement_label`

## Summary
- Domain: `illustrations`
- Scene id: `pixel_village`
- Implementation scene package: `pixel_village`
- Implementation source: `trace/tasks/illustrations/pixel_village/jigsaw_arrangement_label.py`

## Task Contract
Renders a pixel-village source illustration, cuts it into a 2-row by 2-column tile set, and shows four lettered complete arrangements of those tiles. Exactly one option preserves the original row-major tile order. The model selects the option letter for the correct arrangement.

## Program Contract
`select_option(match_jigsaw_arrangement(tile_set, arrangement_options, correct_order=row_major)); scene=pixel_village; scope=jigsaw_arrangement_label`

## Query Branches

| Query id | Program schema |
| --- | --- |
| `single` | `select_option(match_jigsaw_arrangement(tile_set, arrangement_options, correct_order=row_major)); scene=pixel_village; scope=jigsaw_arrangement_label` |

## Program Metadata
- Program signatures: `selection.option_match`
- Base program contract: `select_option(match_jigsaw_arrangement(tile_set, arrangement_options, correct_order=row_major)); scene=pixel_village; scope=jigsaw_arrangement_label`
- Parameter axes: `source_size`
- Arguments:
  - `tile_set`: semantic_role; allowed `pixel_village_2x2_tiles`; source `program_schema_concrete`
  - `arrangement_options`: semantic_role; allowed `A_D_lettered_2x2_tile_arrangements`; source `program_schema_concrete`
  - `correct_order`: operation_parameter; allowed `row_major`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `single`

## Answer Contract
- Answer schema: `option_letter`
- Generator `answer_gt.type`: `option_letter`
- The answer value is one of the visible option letters `A` through `D`.

## Annotation Contract
- Annotation schema: `bbox_set`
- Generator `annotation_gt.type`: `bbox_set`
- Annotation contains exactly one bbox: the final-image pixel box around the selected jigsaw arrangement option image.
- Do not include the option label badge, all options, source-scene objects, territories, or context-only regions.

## Prompt And Trace Requirements
- Prompt text must come from `prompts/illustrations/pixel_village/illustrations_pixel_village_v0.json`.
- Runtime query id is the single-query sentinel `single`; selected option, option permutations, source render modes, source tile boxes, style, and option-label font are trace parameters.
- Source panels are accepted only when every 2x2 tile has enough visual detail to avoid flat-background jigsaw options.
- The option composition uses a frameless functional layout: option labels, tile grid lines, and tight gutters only, with no decorative option-board border or scene background frame.
- The selected option bbox, answer label, option permutations, and source tile boxes must all come from the same `compose_jigsaw_arrangement_options` execution trace.

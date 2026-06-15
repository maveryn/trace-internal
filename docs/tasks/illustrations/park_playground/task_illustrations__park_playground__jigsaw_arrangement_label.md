# `task_illustrations__park_playground__jigsaw_arrangement_label`

## Summary
- Domain: `illustrations`
- Scene id: `park_playground`
- Implementation scene package: `park_playground`
- Implementation source: `trace/tasks/illustrations/park_playground/jigsaw_arrangement_label.py`

## Task Contract
Renders a park/playground source illustration, cuts it into a 2-row by 2-column tile set, and shows four lettered complete arrangements of those tiles. Exactly one option preserves the original row-major tile order. The model selects the option letter for the correct arrangement.

## Program Contract
`select_option(match_jigsaw_arrangement(tile_set, arrangement_options, correct_order=row_major)); scene=park_playground; scope=jigsaw_arrangement_label`

## Query Branches

| Query id | Program schema |
| --- | --- |
| `single` | `select_option(match_jigsaw_arrangement(tile_set, arrangement_options, correct_order=row_major)); scene=park_playground; scope=jigsaw_arrangement_label` |

## Program Metadata
- Program signatures: `selection.option_match`
- Base program contract: `select_option(match_jigsaw_arrangement(tile_set, arrangement_options, correct_order=row_major)); scene=park_playground; scope=jigsaw_arrangement_label`
- Parameter axes: `person_count`, `equipment_count`, `source_size`
- Arguments:
  - `tile_set`: semantic_role; allowed `park_playground_2x2_tiles`; source `program_schema_concrete`
  - `arrangement_options`: semantic_role; allowed `A_D_lettered_2x2_tile_arrangements`; source `program_schema_concrete`
  - `correct_order`: operation_parameter; allowed `row_major`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `single`

## Answer Contract
- Answer schema: `option_letter`
- Generator `answer_gt.type`: `option_letter`
- The answer value is one of the visible option letters `A` through `D`.

## Annotation Contract
- Annotation schema: `keyed_bbox_map`
- Generator `annotation_gt.type`: `keyed_bbox_map`
- Annotation key is `selected_option`.
- Annotation box is the final-image pixel box around the selected jigsaw arrangement option image. Do not include the option label badge, all options, source-scene objects, or context-only regions.

## Prompt And Trace Requirements
- Prompt text must come from `prompts/illustrations/park_playground/illustrations_park_playground_v0.json`.
- Render randomness, sampled park setting/style, source scene counts, option-label font, option permutations, selected option, and verifier payloads must be explicit in the instance trace.
- Source panels are accepted only when every 2x2 tile has enough visual detail to avoid flat-background jigsaw options.
- The selected option bbox, answer label, option permutations, and source tile boxes must all come from the same `compose_jigsaw_arrangement_options` execution trace.

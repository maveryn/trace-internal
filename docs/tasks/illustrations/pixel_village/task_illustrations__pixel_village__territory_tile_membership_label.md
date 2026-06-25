# `task_illustrations__pixel_village__territory_tile_membership_label`

## Summary
- Domain: `illustrations`
- Scene id: `pixel_village`
- Implementation scene package: `pixel_village`
- Implementation source: `trace/tasks/illustrations/pixel_village/territory_tile_membership_label.py`

## Task Contract
Selects the lettered ground tile that is inside a named semantic pixel-village territory.

## Program Contract
`select_label(filter(candidate_ground_tiles, inside_territory(tile, target_territory))); scene=pixel_village; scope=territory_tile_membership_label`

## Query Branches

| Query id | Program schema |
| --- | --- |
| `single` | `select_label(filter(candidate_ground_tiles, inside_territory(tile, target_territory))); scene=pixel_village; scope=territory_tile_membership_label` |

## Program Metadata
- Program signatures: `select.spatial_membership_label`
- Base program contract: `select_label(filter(candidate_ground_tiles, inside_territory(tile, target_territory))); scene=pixel_village; scope=territory_tile_membership_label`
- Parameter axes: `target_territory`, `correct_index`, `canvas_profile`
- Supported operands: `cemetery`, `orchard`
- Argument metadata status: `curated`
- Supported query ids: `single`

## Answer Contract
- Answer schema: `option_letter`
- Generator `answer_gt.type`: `option_letter`
- Exactly one candidate ground tile is inside the named target territory.
- The answer value is the letter for that unique candidate tile.
- Distractor tiles must be empty ground tiles near the target territory but outside it.

## Annotation Contract
- Annotation schema: `bbox`
- Generator `annotation_gt.type`: `bbox`
- Annotation is the final-image pixel box for the selected ground tile, not the option label badge and not the whole territory.
- Candidate label bboxes are recorded only as render diagnostics.

## Prompt And Trace Requirements
- Prompt text must come from the pixel-village prompt bundle.
- Public prompts must name the target territory and ask for a lettered ground tile.
- The relevant territory is forced present by the task, and the scene config keeps cemetery and orchard visible for review diversity.
- Candidate tile coordinates, candidate tile bboxes, label bboxes, membership booleans, target-territory distances, selected tile, target territory bbox, and projected annotation must be recorded in the trace.

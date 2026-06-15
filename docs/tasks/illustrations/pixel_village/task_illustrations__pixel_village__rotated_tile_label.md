# `task_illustrations__pixel_village__rotated_tile_label`

## Summary
- Domain: `illustrations`
- Scene id: `pixel_village`
- Implementation scene package: `pixel_village`
- Implementation source: `trace/tasks/illustrations/pixel_village/rotated_tile_label.py`

## Task Contract
Renders a pixel-village source illustration as a 2-row by 3-column lettered tile grid with exactly one tile rotated. The model selects the letter of the rotated tile.

## Program Contract
`select_label(find_rotated_tile(tile_grid, labels=A_F)); scene=pixel_village; scope=rotated_tile_label`

## Query Branches

| Query id | Program schema |
| --- | --- |
| `single` | `select_label(find_rotated_tile(tile_grid, labels=A_F)); scene=pixel_village; scope=rotated_tile_label` |

## Program Metadata
- Program signatures: `selection.spatial_transform`
- Base program contract: `select_label(find_rotated_tile(tile_grid, labels=A_F)); scene=pixel_village; scope=rotated_tile_label`
- Parameter axes: `rotation_degrees`, `source_size`
- Arguments:
  - `tile_grid`: semantic_role; allowed `pixel_village_2x3_tile_grid`; source `program_schema_concrete`
  - `labels`: semantic_role; allowed `A_F_lettered_tiles`; source `program_schema_concrete`
  - `rotation_degrees`: operation_parameter; allowed `90`, `270`; source `parameter_axes`
- Argument metadata status: `curated`
- Supported query ids: `single`

## Answer Contract
- Answer schema: `option_letter`
- Generator `answer_gt.type`: `option_letter`
- The answer value is one of the visible tile letters `A` through `F`.

## Annotation Contract
- Annotation schema: `bbox_set`
- Generator `annotation_gt.type`: `bbox_set`
- Annotation contains exactly one bbox: the final-image pixel box around the rotated tile.
- Do not include all tiles, the tile label badge, source-scene objects, or context-only regions.

## Prompt And Trace Requirements
- Prompt text must come from `prompts/illustrations/pixel_village/illustrations_pixel_village_v0.json`.
- Runtime query id is the single-query sentinel `single`; rotation angle, usable tile indices, selected tile, source render modes, and label font are trace parameters.
- The composed grid uses the source image full-bleed with functional tile grid lines and option letters only; it must not add decorative outer margins, borders, or background frames.
- The selected tile bbox, answer label, rotation angle, and usable-tile set must all come from the same `compose_rotated_tile_grid` execution trace.

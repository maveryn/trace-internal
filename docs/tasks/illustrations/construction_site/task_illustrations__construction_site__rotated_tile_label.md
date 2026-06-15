# `task_illustrations__construction_site__rotated_tile_label`

## Summary
- Domain: `illustrations`
- Scene id: `construction_site`
- Implementation scene package: `construction_site`
- Implementation source: `trace/tasks/illustrations/construction_site/rotated_tile_label.py`

## Task Contract
Renders a construction-site source illustration as a 2-row by 3-column grid of six lettered tiles, with exactly one tile rotated. The model selects the letter of the rotated tile.

## Program Contract
`select_label(find_rotated_tile(tile_grid, labels=A_F)); scene=construction_site; scope=rotated_tile_label`

## Query Branches

| Query id | Program schema |
| --- | --- |
| `single` | `select_label(find_rotated_tile(tile_grid, labels=A_F)); scene=construction_site; scope=rotated_tile_label` |

## Program Metadata
- Program signatures: `selection.visual_anomaly`
- Base program contract: `select_label(find_rotated_tile(tile_grid, labels=A_F)); scene=construction_site; scope=rotated_tile_label`
- Parameter axes: `source_worker_count`, `source_material_count`, `source_equipment_count`, `rotation_degrees`
- Arguments:
  - `tile_grid`: semantic_role; allowed `lettered_construction_site_tile_grid`; source `program_schema_concrete`
  - `labels`: semantic_role; allowed `A_F`; source `program_schema_concrete`
  - `rotation_degrees`: render_parameter; allowed `90`, `270`; source `trace_metadata`
- Argument metadata status: `curated`
- Supported query ids: `single`

## Answer Contract
- Answer schema: `option_letter`
- Generator `answer_gt.type`: `option_letter`
- The answer value is one of the visible tile letters `A` through `F`.

## Annotation Contract
- Annotation schema: `bbox`
- Generator `annotation_gt.type`: `bbox`
- Annotation contains exactly one final-image pixel box around the rotated tile. Do not include all tile options, tile labels, source-scene objects, or context-only regions.

## Prompt And Trace Requirements
- Prompt text must come from the `illustrations_construction_site_v1` prompt bundle, with scene/task/output layers selected deterministically and recorded in metadata.
- Render randomness, sampled construction-site contents, tile-label font, grid style, selected tile, and verifier payloads must be explicit in the instance trace.
- The selected tile is sampled only from tiles with enough visual detail and rotation difference to make the anomaly visible.
- Quarter-turn rotations require square source cells; for the 2x3 grid, source dimensions must keep `source_width / 3 == source_height / 2`.
- The selected tile bbox, answer label, and rotated tile index must all come from the same `compose_rotated_tile_grid` execution trace.

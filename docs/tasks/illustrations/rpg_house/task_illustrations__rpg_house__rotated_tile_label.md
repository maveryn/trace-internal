# `task_illustrations__rpg_house__rotated_tile_label`

## Summary
- Domain: `illustrations`
- Scene id: `rpg_house`
- Implementation scene package: `rpg_house`
- Implementation source: `trace/tasks/illustrations/rpg_house/rotated_tile_label.py`

## Task Contract
Render a top-down RPG house source illustration as a profile-aware grid of lettered square tiles, with exactly one tile rotated. The model selects the letter of the rotated tile.

## Program Contract
`select_label(find_rotated_tile(tile_grid, labels=visible_letters)); scene=rpg_house; scope=rotated_tile_label`

## Query Branches

| Query id | Program schema |
| --- | --- |
| `single` | `select_label(find_rotated_tile(tile_grid, labels=visible_letters)); scene=rpg_house; scope=rotated_tile_label` |

## Program Metadata
- Program signatures: `selection.visual_anomaly`
- Base program contract: `select_label(find_rotated_tile(tile_grid, labels=visible_letters)); scene=rpg_house; scope=rotated_tile_label`
- Parameter axes: `source_room_count`, `rotation_degrees`, `canvas_profile`
- Arguments:
  - `tile_grid`: semantic role; allowed `lettered_rpg_house_tile_grid`; source `program_schema_concrete`
  - `labels`: semantic role; allowed `A_D_or_A_F`; source `program_schema_concrete`
  - `rotation_degrees`: render parameter; allowed `90`, `270`; source `trace_metadata`
  - `canvas_profile`: render parameter; allowed `landscape`, `square`, `portrait`; source `trace_metadata`
- Argument metadata status: `curated`
- Supported query ids: `single`

## Answer Contract
- Answer schema: `option_letter`
- Generator `answer_gt.type`: `option_letter`
- The answer value is one of the visible tile letters.

## Annotation Contract
- Annotation schema: `bbox`
- Generator `annotation_gt.type`: `bbox`
- Annotation contains exactly one final-image pixel box around the rotated tile. Do not include all tile options, tile labels, room fixtures, or context-only source-scene regions.

## Prompt And Trace Requirements
- Prompt text must come from `prompts/illustrations/rpg_house/illustrations_rpg_house_v0.json`.
- Render randomness, source room count, tile-label font, grid style, selected tile, and verifier payloads must be explicit in the instance trace.
- The selected tile is sampled only from tiles with enough visual detail and rotation difference to make the anomaly visible.
- Quarter-turn rotations require square source cells; the source profile chooses a landscape 2x3, square 2x2, or portrait 3x2 grid.
- The composed grid must be full-bleed over the source image with no decorative outer margin, border, or background frame.
- The selected tile bbox, answer label, and rotated tile index must all come from the same `compose_rotated_tile_grid` execution trace.

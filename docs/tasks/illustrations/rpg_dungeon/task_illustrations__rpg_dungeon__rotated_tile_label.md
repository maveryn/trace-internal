# `task_illustrations__rpg_dungeon__rotated_tile_label`

## Summary
- Domain: `illustrations`
- Scene id: `rpg_dungeon`
- Implementation scene package: `rpg_dungeon`
- Implementation source: `trace/tasks/illustrations/rpg_dungeon/rotated_tile_label.py`

## Task Contract
Shows one top-down RPG dungeon source image split into labeled tiles, with exactly one tile rotated in place. The model must select the letter of the rotated tile.

## Program Contract
`select(tile_label, rotated(tile, rotation_degrees in {90,270}) and unique(tile)); scene=rpg_dungeon; scope=rotated_tile_label`

## Query Branches

| Query id | Program schema |
| --- | --- |
| `single` | `select(tile_label, rotated(tile, rotation_degrees in {90,270}) and unique(tile)); scene=rpg_dungeon; scope=rotated_tile_label` |

## Program Metadata
- Program signatures: `select.visual_tile_rotation`
- Base program contract: `select(tile_label, rotated(tile, rotation_degrees in {90,270}) and unique(tile)); scene=rpg_dungeon; scope=rotated_tile_label`
- Parameter axes: `source_chest_count`, `source_reachable_chest_count`, `source_monster_count`, `rotation_degrees`, `canvas_profile`, `grid_shape`, `correct_index`
- Arguments:
  - `tile`: labeled image tile; allowed visible source-image grid cells; source `render_map.tile_bboxes_px_by_label`
  - `tile_label`: visible tile letter; allowed generated option labels for the chosen grid shape; source `render_map.tile_bboxes_px_by_label`
  - `rotation_degrees`: integer; allowed `90|270`; source `parameter_axes`
  - `correct_index`: integer tile index selected from visually usable tile candidates; source `parameter_axes`
- Argument metadata status: `curated`
- Supported query ids: `single`

## Answer Contract
- Answer schema: `option_letter`
- Generator `answer_gt.type`: `option_letter`
- The answer is the visible letter of the only tile rotated relative to the rest of the dungeon image.

## Annotation Contract
- Annotation schema: `bbox`
- Generator `annotation_gt.type`: `bbox`
- Annotation contains one bounding box around the selected rotated tile in the final rendered image.
- Annotation excludes all non-rotated tiles, grid lines, labels, option text, and background.

## Prompt And Trace Requirements
- Prompt text must come from `prompts/illustrations/rpg_dungeon/illustrations_rpg_dungeon_v0.json`.
- Public prompts must ask for the lettered rotated tile, not for a numeric tile index.
- Render-only attributes such as palette, monster type, source chest count, layout orientation, rotation angle, grid shape, label font, and canvas profile must not be query ids.
- Source scene trace, tile bboxes by label, rotated tile bbox, selected tile index, grid shape, projected scalar bbox annotation, and prompt-template metadata must be recorded in the trace.

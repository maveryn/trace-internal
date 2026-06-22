# `task_illustrations__rpg_dungeon__swapped_tile_pair_label`

## Summary
- Domain: `illustrations`
- Scene id: `rpg_dungeon`
- Implementation scene package: `rpg_dungeon`
- Implementation source: `trace/tasks/illustrations/rpg_dungeon/swapped_tile_pair_label.py`

## Task Contract
Shows a numbered 3x3 top-down RPG dungeon grid where exactly two source tiles have exchanged positions. Four visual/text options name candidate numbered-cell pairs. The model must select the option letter naming the swapped pair.

## Program Contract
`select(option_letter, option.names_pair(swapped(tile_i, tile_j)) and unique(option)); scene=rpg_dungeon; scope=swapped_tile_pair_label`

## Query Branches

| Query id | Program schema |
| --- | --- |
| `single` | `select(option_letter, option.names_pair(swapped(tile_i, tile_j)) and unique(option)); scene=rpg_dungeon; scope=swapped_tile_pair_label` |

## Program Metadata
- Program signatures: `select.swapped_tile_pair_option`
- Base program contract: `select(option_letter, option.names_pair(swapped(tile_i, tile_j)) and unique(option)); scene=rpg_dungeon; scope=swapped_tile_pair_label`
- Parameter axes: `source_chest_count`, `source_reachable_chest_count`, `source_monster_count`, `swapped_pair_indices`, `correct_index`, `candidate_pair_count`, `canvas_profile`
- Arguments:
  - `tile_i`, `tile_j`: two numbered 3x3 source-grid cells; allowed visually usable tile-pair candidates; source `render_map.tile_bboxes_px_by_number`
  - `option_letter`: visible option label; allowed `A|B|C|D`; source `render_map.option_pairs_by_label`
  - `swapped_pair_indices`: zero-based source tile indices for the actual swapped cells; source `parameter_axes`
- Argument metadata status: `curated`
- Supported query ids: `single`

## Answer Contract
- Answer schema: `option_letter`
- Generator `answer_gt.type`: `option_letter`
- The answer is the option letter whose pair text names the two numbered tiles that were swapped.

## Annotation Contract
- Annotation schema: `bbox_set`
- Generator `annotation_gt.type`: `bbox_set`
- Annotation contains exactly two bounding boxes, one around each swapped numbered tile in the final rendered image.
- Annotation excludes distractor option cards, non-swapped tiles, grid lines, labels, and background.

## Prompt And Trace Requirements
- Prompt text must come from `prompts/illustrations/rpg_dungeon/illustrations_rpg_dungeon_v0.json`.
- Public prompts must make clear that exactly two numbered tiles were swapped and the answer is an option letter.
- Render-only attributes such as palette, monster type, source chest count, layout orientation, candidate-pair count, label font, and canvas profile must not be query ids.
- Source scene trace, tile bboxes by number, option bboxes by label, option-pair mapping, swapped tile bboxes, projected bbox-set annotation, and prompt-template metadata must be recorded in the trace.

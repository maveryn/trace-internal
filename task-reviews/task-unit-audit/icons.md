# Icons Task-Unit Audit

Task-unit audit for `domain=icons` using `docs/workflows/TASK_UNIT_AUDIT.md`.

## Domain summary
1. The icons domain is mostly healthy and visually rich; almost every task has strong within-task perceptual variation from placement, icon identity, color, rotation, and clutter.
2. Most icons tasks are good task units because they keep one stable panel/cell scaffold and one stable witness semantics.
3. The main task-unit pressure point is `task_icons_pattern_structured_violation`, which currently mixes a numbered row-sequence scaffold with numbered-grid rule grids.
4. Recommended domain outcome:
   - `Keep`: `9`
   - `Split`: `1`
   - `Merge`: `0`
   - `Retire`: `0`

## Task findings

### `task_icons_counting_reference_match_count`
- Outcome: `Keep`
- Why: one coherent two-panel reference-vs-scene matching family, even though the predicate changes across type, color, orientation, and joint binding.
- Scene variety: high; the same reference/scatter scaffold supports substantial icon-level visual variation.
- Query variety: strong (`match_type|match_color|match_orientation|match_attribute_binding`) but still within one stable “find scene matches to the reference” family.
- Grounding necessity: strong; the model must inspect the reference icon and compare the right visual attributes in the scene.
- Evidence fit: good; scene match boxes are the natural witness across all variants.
- Follow-up: none required now.

### `task_icons_counting_singleton_type`
- Outcome: `Keep`
- Why: one coherent scene-internal frequency-counting family.
- Scene variety: moderate to high; one cluttered single-panel scene with varied type multiplicities, colors, and rotations.
- Query variety: narrow but appropriate (`singleton_type_count`).
- Grounding necessity: strong; the model must group icons by type under nuisance variation.
- Evidence fit: good; singleton icon boxes are the natural witness.
- Follow-up: none required now.

### `task_icons_counting_size_relation`
- Outcome: `Keep`
- Why: one coherent reference-vs-scene comparative-size family.
- Scene variety: moderate to high; stable two-panel scaffold with size-based positives and negatives under varied placement/clutter.
- Query variety: modest but coherent (`size_smaller|size_larger`).
- Grounding necessity: strong; the solver must compare nominal icon size relative to the visible reference.
- Evidence fit: good; qualifying scene icon boxes are the right witness.
- Follow-up: none required now.

### `task_icons_pattern_structured_violation`
- Outcome: `Split`
- Why: this task currently mixes two different structured-grounding families:
  - numbered sequence-row violation (`row_rotation_violation`)
  - numbered grid-rule violation (`grid_rotation_violation|grid_size_violation`)
- Scene variety: high, but too mixed for one task unit.
- Query variety: moderate, but spread across row and grid scaffolds with different visual search patterns.
- Grounding necessity: strong in both halves, but the operative perceptual job differs:
  - continuing/checking a 1D ordered row rule,
  - checking a 2D grid rule over rows and columns.
- Evidence fit: technically consistent (one violating box), but the witness semantics sit inside two different scene grammars.
- Follow-up:
  1. Keep `grid_rotation_violation|grid_size_violation` together as a numbered-grid structured-violation task.
  2. Move `row_rotation_violation` into its own row-sequence violation task, especially if more row-rule variants are added later.

### `task_icons_relation_between_two_anchors_count`
- Outcome: `Keep`
- Why: one coherent two-anchor strip-membership family over a single scene.
- Scene variety: moderate; stable free-placement scene with strong anchor geometry variation.
- Query variety: modest but coherent (`inside_vertical_strip|inside_horizontal_strip`).
- Grounding necessity: strong; the model must reason about icon centers relative to the two marked anchors.
- Evidence fit: good; qualifying scene icon boxes are the natural witness.
- Follow-up: none required now.

### `task_icons_relation_mirror_symmetry`
- Outcome: `Keep`
- Why: one coherent whole-cell mirror-signature matching family over a reference cell and labeled scene cells.
- Scene variety: moderate; the cell-grid scaffold is stable while the supported symmetry signatures vary.
- Query variety: strong (`mirror_vertical|mirror_horizontal|mirror_diagonal_main|mirror_diagonal_anti|mirror_both_axes`) but still one stable “match the reference symmetry signature” family.
- Grounding necessity: strong; the model must inspect whole-cell arrangement symmetry rather than any single icon.
- Evidence fit: good; cell labels are the correct witness level.
- Follow-up: none required now.

### `task_icons_relation_occlusion_order`
- Outcome: `Keep`
- Why: one coherent overlap-cell front/back-order family.
- Scene variety: moderate; stable reference-plus-grid scaffold with varied overlap ratios, colors, and subtle noise.
- Query variety: narrow but appropriate (`same_front_to_back_order`).
- Grounding necessity: strong; the solver must determine which icon is visually on top in each cell.
- Evidence fit: good; matching cell labels are the natural witness.
- Follow-up: none required now.

### `task_icons_relation_relative_position_type`
- Outcome: `Keep`
- Why: one coherent reference-type + anchor-relative-position family.
- Scene variety: moderate to high; stable two-panel scaffold with anchor placement and clutter variation.
- Query variety: moderate (`left_of_anchor|right_of_anchor|above_anchor|below_anchor`) within one stable grounding family.
- Grounding necessity: strong; the solver must jointly match icon type and spatial side relative to the anchor.
- Evidence fit: good; qualifying scene boxes are the natural witness.
- Follow-up: none required now.

### `task_icons_sequence_missing_count`
- Outcome: `Keep`
- Why: one coherent missing-cell arithmetic-sequence family over a row of icon-count boxes.
- Scene variety: moderate; stable row scaffold with varying row length, missing position, and count progression.
- Query variety: narrow but appropriate (`arithmetic_progression`).
- Grounding necessity: strong; the model must read the visible counts in the row and infer the hidden count.
- Evidence fit: good; the missing box is the right witness for this task.
- Follow-up: none required now.

### `task_icons_transformation_pair_count`
- Outcome: `Keep`
- Why: one coherent reference-transform matching family over labeled pair cells.
- Scene variety: moderate; stable reference-plus-grid pair scaffold with varied icon choices and transforms.
- Query variety: narrow but appropriate (`same_pair_transform` under multiple realized transforms).
- Grounding necessity: strong; the model must compare the transformation shown in the reference pair against every scene pair.
- Evidence fit: good; matching cell labels are the natural witness.
- Follow-up: none required now.

## Recommended next action
1. Leave the other icons tasks unchanged for now.
2. Treat `task_icons_pattern_structured_violation` as the first concrete icons split candidate when rebalancing benchmark units.
3. Keep the rest of icons as an example of a domain with strong within-task perceptual variety even when the overall scene grammar is intentionally synthetic.

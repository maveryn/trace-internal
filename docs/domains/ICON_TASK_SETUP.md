# Icons Task Setup

This document captures the active `icons` domain contract.

For cross-domain coverage rollups, use `docs/project/STATUS.md` and `docs/domains/TASK_FAMILY_VARIANTS.md` instead of repeating those inventories elsewhere.

## 1) Domain scope
1. `domain=icons` is for synthetic icon-scene reasoning over the curated icon bundle under `assets/icons/`.
2. Icon tasks should test grounded visual comparison, spatial relation, sequence, pattern, transformation, or frequency reasoning over visible icon instances.
3. Prompt-facing evidence should stay on the semantic visual unit:
   - icon instances use `bbox_set`,
   - labeled cells/pairs use `label_set`,
   - missing or violating slots use one local `bbox_set`.

## 2) Asset policy
1. TRACE uses the curated icon bundle under `assets/icons/`.
2. Resolve manifests only through `trace/tasks/icons/shared/icon_assets.py`.
3. Current manifests:
   - `all_icons.txt`: full icon pool,
   - `non_symmetry.txt`: asymmetric icons for orientation-sensitive tasks,
   - `symmetry.txt`: symmetric icons when symmetry itself is useful.
4. Use `non_symmetry.txt` when a predicate can collapse under icon symmetry:
   - orientation / rotation matching,
   - mirror symmetry,
   - transformation identity,
   - multi-attribute binding that includes orientation.
5. Use `all_icons.txt` when symmetry is not part of the predicate:
   - type,
   - color,
   - size,
   - pure spatial relation,
   - sequence counts,
   - occlusion order.

## 3) Active families
### `counting`
1. `task_icons_counting_reference_match_count`
   - scaffold: two-panel `Reference` + `Scene`
   - query variants: `match_type|match_color|match_orientation|match_attribute_binding`
   - answer type: `integer`
   - evidence: scene-only `bbox_set` over matching icon instances
2. `task_icons_counting_size_relation`
   - scaffold: two-panel `Reference` + `Scene`
   - query variants: count scene icons `smaller` or `larger` than the reference icon
   - answer type: `integer`
   - evidence: scene-only `bbox_set` over size-qualified icon instances
3. `task_icons_counting_singleton_type`
   - scaffold: single-panel free-placed icon scene
   - query: count icons whose `icon_id` appears exactly once
   - answer type: `integer`
   - evidence: scene-only `bbox_set` over singleton-type icon instances

### `relation`
1. `task_icons_relation_relative_position_type`
   - scaffold: two-panel `Reference` + `Scene` with one marked `Anchor`
   - query variants: `left_of_anchor|right_of_anchor|above_anchor|below_anchor`
   - answer type: `integer`
   - evidence: scene-only `bbox_set` over matching icon instances
2. `task_icons_relation_between_two_anchors_count`
   - scaffold: single-panel scene with anchors `A` and `B`
   - query variants: `inside_vertical_strip|inside_horizontal_strip`
   - answer type: `integer`
   - evidence: scene-only `bbox_set` over matching icon instances
3. `task_icons_relation_mirror_symmetry`
   - scaffold: `Reference` cell + labeled `Scene` grid of icon-arrangement cells
   - query variants: `mirror_vertical|mirror_horizontal|mirror_diagonal_main|mirror_diagonal_anti|mirror_both_axes`
   - answer type: `integer`
   - evidence: sorted `label_set` of matching scene-cell labels
4. `task_icons_relation_occlusion_order`
   - scaffold: `Reference` cell + labeled `Scene` grid of overlapping icon-pair cells
   - query: count cells with the same front-to-back order as the reference
   - answer type: `integer`
   - evidence: sorted `label_set` of matching scene-cell labels

### `transformation`
1. `task_icons_transformation_pair_count`
   - scaffold: `Reference` pair + labeled `Scene` grid of icon pairs
   - query: count cells applying the same transformation as the reference pair
   - transform vocabulary: `rot90|rot180|rot270|flip_h|flip_v|flip_diag_main|flip_diag_anti`
   - answer type: `integer`
   - evidence: sorted `label_set` of matching scene-cell labels

### `sequence`
1. `task_icons_sequence_missing_count`
   - scaffold: one row of boxed icon-count sequence cells with one missing cell
   - query: count how many icons should appear in the missing box
   - answer type: `integer`
   - evidence: one-box `bbox_set` over the missing cell

### `pattern`
1. `task_icons_pattern_structured_violation`
   - scaffold: numbered sequence row or numbered `3 x 3` grid
   - query variants: `row_rotation_violation|grid_rotation_violation|grid_size_violation`
   - answer type: integer numbered-box index
   - evidence: one-box `bbox_set` over the violating numbered box

## 4) Evidence policy
1. Use `bbox_set` when the witness is one or more visible icon instances.
2. Use `label_set` when the witness is one or more labeled scene cells/pairs.
3. Use a single local `bbox_set` when the witness is a missing or violating slot.
4. Keep hidden asset ids, sampled transforms, nominal sizes, and ambiguity checks in trace metadata; prompt-facing evidence should stay visual and compact.

## 5) Ambiguity policy
1. Use explicit target/distractor sampling rather than hoping random placement realizes the target count.
2. Enforce minimum size gaps for size-relation tasks.
3. For anchored relation tasks, mix distractor types so the task cannot be solved by occupancy alone.
4. For mirror-symmetry tasks, use square cells, exact rendered-image signatures, even icon counts, and the asymmetric icon pool where needed.
5. For pattern-violation tasks, reject any instance where another supported rule hypothesis would make a different violating cell plausible.
6. For singleton-type tasks, define grouping over `icon_id` only; colors and rotations may vary independently.

## 6) Shared helper placement
1. Icon asset loading belongs in `trace/tasks/icons/shared/icon_assets.py`.
2. Shared icon scene/rendering helpers belong under `trace/tasks/icons/shared/`.
3. Reuse the existing grid, sequence, pair-grid, overlap-grid, transform, style, and anchor-marking helpers before adding task-local layout/rendering utilities.

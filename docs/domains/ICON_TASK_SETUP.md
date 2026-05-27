# Icons Task Setup

This document captures the active `icons` domain contract.

For cross-domain coverage rollups, use `docs/project/STATUS.md` and `docs/domains/SCENE_TASK_QUERY_GUIDE.md` instead of repeating those inventories elsewhere.

## 1) Domain scope
1. `domain=icons` is for synthetic icon-scene reasoning over curated SVG icons
   under `assets/icons/` and TRACE-owned procedural named glyphs.
2. Icon tasks should test grounded visual comparison, spatial relation, sequence, pattern, transformation, or frequency reasoning over visible icon instances.
3. Prompt-facing evidence should stay on the semantic visual unit:
   - icon instances use `bbox_set`,
   - labeled cells/pairs use `bbox_set` over the cell,
   - missing or violating slots use one local `bbox_set`.
4. Active icons tasks expose one public sampling unit per `task_id` and put the
   meaningful branch in `query_id`. Legacy/internal `query_id` params may
   still be accepted as targeted-generation aliases, but prompt-facing and
   review-facing branch identity should use `query_id`.

## 2) Asset policy
1. TRACE uses the curated icon bundle under `assets/icons/` for broad
   reference/icon-match tasks and procedural named glyphs for direct
   prompt-named shape recognition tasks.
2. Resolve curated SVG manifests only through
   `trace/tasks/icons/shared/icon_assets.py`.
3. Current manifests:
   - `all_icons.txt`: full icon pool,
   - `non_symmetry.txt`: asymmetric icons for orientation-sensitive tasks,
   - `symmetry.txt`: symmetric icons when symmetry itself is useful.
   Generation code should resolve one of these full manifests only.
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
6. Use `trace/tasks/icons/shared/procedural_named_icons.py` for named
   procedural glyphs. The current vocabulary contains 100 prompt-facing shapes:
   circle, ring, square, triangle, pentagon, hexagon, octagon, star, heart,
   crescent, check mark, arrow, sun, lightning bolt, cloud, flower, leaf,
   shield, flag, crown, house, capsule, teardrop, hourglass, key, bell, ladder,
   kite, mushroom, fish, butterfly, umbrella, anchor, car, boat, rocket,
   envelope, book, pencil, camera, lock, magnifying glass, trophy, cup,
   music note, battery, clock, gift, shoe, shirt, glasses, snowman, tree, bird,
   apple, balloon, shuriken, gear, puzzle piece, lightbulb, lantern, candle,
   bottle, bucket, shovel, fork, spoon, pizza slice, egg, dice,
   microphone, headphones, chair, tent, phone, television, laptop, watch, bus,
   train, bicycle, bed, lamp, door, window, mailbox, toothbrush, broom, trash
   can, teapot, knife, soccer ball, rugby ball, dumbbell,
   calculator, plug, broccoli, cactus, guitar, and acorn.

## 3) Active families
### `counting`
1. `task_icons__icon_field__type_frequency_count`
   - scaffold: single-panel free-placed icon scene
   - query_id: `singleton_type_count|most_frequent_type_count`
   - answer type: `integer`
   - evidence: scene-only `bbox_set` over icon instances satisfying the selected frequency predicate
2. `task_icons__reference_canvas__attribute_match_count`
   - scaffold: two-panel `Reference` + `Scene`
   - query_id: `match_type|match_color|match_rotation|match_type_color_rotation`
   - answer type: `integer`
   - evidence: scene-only `bbox_set` over matching icon instances
3. `task_icons__reference_canvas__size_relation_count`
   - scaffold: two-panel `Reference` + `Scene`
   - query_id: `size_smaller|size_larger`
   - internal axis: `size_relation=smaller|larger`
   - answer type: `integer`
   - evidence: scene-only `bbox_set` over size-qualified icon instances
4. `task_icons__named_field__shape_count`
   - scene_id: `named_field`
   - scaffold: single-panel field of procedural named shape icons with grid,
     scatter, cluster, and stack arrangement modes
   - query_id: `named_shape_count`
   - answer type: `integer`
   - evidence: scene-only `bbox_set` over icons whose `shape_id` matches the prompt-named shape
   - target support: all procedural named glyphs listed in the asset policy
   - target answer support: layout-dependent, with non-stack layouts capped at
     lower counts and stack layouts capped at moderate row/column counts
5. `task_icons__named_field__shape_attribute_boolean_count`
   - scene_id: `named_field`
   - scaffold: single-panel field of procedural named shape icons with
     semantic shared named colors and semantic fill styles
   - query_id: one of `shape_and_color_count`, `shape_or_color_count`,
     `shape_and_not_color_count`, `color_and_not_shape_count`,
     `neither_shape_nor_color_count`, or `exactly_one_shape_or_color_count`
   - secondary attribute axis: color with probability 0.5, fill style with
     probability 0.5; queryable fill styles are `striped`, `dotted`, and
     `half_filled`
   - answer type: `integer`
   - evidence: scene-only `bbox_set` over icons satisfying the Boolean
     shape/attribute condition
   - target answer support: `1..5`, weighted toward lower counts
   - arrangement support: non-stack named-icon layouts only
6. `task_icons__named_field__shape_pair_total_count`
   - scene_id: `named_field`
   - scaffold: single-panel field of procedural named shape icons with
     semantic shared named colors and non-semantic fill-style variation
   - query_id: `two_shape_total_count|two_bound_color_total_count`
   - answer type: `integer`
   - evidence: scene-only `bbox_set` over every icon in either operand group
   - total answer support: `2..10`
   - arrangement support: non-stack named-icon layouts only
7. `task_icons__named_field__shape_pair_difference_count`
   - scene_id: `named_field`
   - scaffold: single-panel field of procedural named shape icons with
     semantic shared named colors and non-semantic fill-style variation
   - query_id: `two_shape_difference_count|two_bound_color_difference_count`
   - answer type: `integer`
   - evidence: scene-only `bbox_set` over every icon in either operand group
   - absolute-difference answer support: `0..5`
   - arrangement support: non-stack named-icon layouts only
8. `task_icons__named_field__closer_to_reference_count`
   - scene_id: `named_field`
   - scaffold: single-panel field with two labeled reference icons `A` and
     `B`, plus repeated icons of one prompt-named target shape
   - query_id: one of `closer_to_reference_a_count` or
     `closer_to_reference_b_count`
   - answer type: `integer`
   - evidence: scene-only `bbox_set` over target-shape icons closer to the
     queried reference
   - target answer support: `0..4`
   - target icon count support: `4..8`; no unrelated distractor icon types
9. `task_icons__named_field__region_shape_count`
   - scene_id: `named_field`
   - scaffold: single-panel field of procedural named shape icons with a
     visible marked rectangle/ellipse, band, quadrant, or shelf
   - query_id: one of `inside_shape_count`, `outside_shape_count`,
     `inside_band_count`, `outside_band_count`, `inside_quadrant_count`, or
     `inside_shelf_count`
   - answer type: `integer`
   - evidence: scene-only `bbox_set` over target-shape icons satisfying the
     active region predicate
   - target answer support: `1..5`, weighted toward lower counts
   - fill style is non-semantic visual variation
10. `task_icons__venn_field__venn_region_shape_count`
   - scene_id: `venn_field`
   - scaffold: single-panel field of procedural named shape icons with two
     overlapping marked circles
   - query_id: one of `inside_both_circles_count`,
     `inside_either_circle_count`, `inside_exactly_one_circle_count`, or
     `outside_both_circles_count`
   - target attribute mode: shape-only, color+shape, or fill-style+shape
   - answer type: `integer`
   - evidence: scene-only `bbox_set` over target icons whose centers satisfy
     the active Venn predicate
   - target answer support: `1..5`, weighted toward lower counts
   - target descriptions quote the named icon, e.g. `"bell"` icons
11. `task_icons__named_field__shape_counterfactual_count`
   - scene_id: `named_field`
   - scaffold: single-panel field of procedural named shape icons
   - query_id: one of `target_count_after_shape_replacement`,
     `total_count_after_shape_removal`, or
     `target_count_after_remove_and_replace`
   - answer type: `integer`
   - evidence: scene-only `bbox_set` over visible icons counted after the
     hypothetical edit
   - target answer support: `1..8`
   - fill style is non-semantic visual variation
12. `task_icons__paired_canvas__panel_exact_match_count`
   - scene_id: `paired_canvas`
   - scaffold: two large panels labeled `Left` and `Right`
   - query_id: `right_exact_match_count`
   - answer type: `integer`
   - evidence: Right-panel `bbox_set` over icons exactly matching a Left-panel icon by type, color, size, and rotation
13. `task_icons__paired_canvas__panel_difference_count`
   - scene_id: `paired_canvas`
   - scaffold: two large panels labeled `Left` and `Right`
   - query_id: `added_in_right_count|missing_from_right_count`
   - answer type: `integer`
   - evidence: Right-panel boxes for added icons, Left-panel boxes for missing icons

### `relation`
1. `task_icons__reference_canvas__anchor_position_count`
   - scene_id: `reference_canvas`
   - scaffold: two-panel `Reference` + `Scene` with one marked `Anchor`
   - query_id: `left_of_anchor|right_of_anchor|above_anchor|below_anchor`
   - internal axis: `direction=left|right|above|below`
   - answer type: `integer`
   - evidence: scene-only `bbox_set` over matching icon instances
2. `task_icons__two_anchor__between_anchors_count`
   - scene_id: `two_anchor`
   - scaffold: single-panel scene with anchors `A` and `B`
   - query_id: `inside_vertical_strip|inside_horizontal_strip`
   - internal axis: `strip_axis=vertical|horizontal`
   - answer type: `integer`
   - evidence: scene-only `bbox_set` over matching icon instances
3. `task_icons__mirror_grid__mirror_symmetry_count`
   - scene_id: `mirror_grid`
   - scaffold: `Reference` cell + labeled `Scene` grid of icon-arrangement cells
   - query_id: `mirror_vertical|mirror_horizontal|mirror_diagonal_main|mirror_diagonal_anti|mirror_both_axes`
   - answer type: `integer`
   - evidence: `bbox_set` around matching Scene cells
4. `task_icons__mirror_grid__reflection_match_label`
   - scene_id: `mirror_grid`
   - scaffold: `Reference` cell + labeled 5-option `Scene` grid
   - query_id: `vertical_reflection_match|horizontal_reflection_match|diagonal_main_reflection_match|diagonal_anti_reflection_match`
   - answer type: `option_letter`
   - evidence: one-box `bbox_set` around the matching Scene cell
5. `task_icons__named_field__reference_distance_rank_label`
   - scene_id: `named_field`
   - scaffold: single-panel scene with one unique named reference icon, six labeled candidate icons `A`..`F`, and `4..8` unlabeled distractors
   - query_id: `closest_to_named_reference_label|second_closest_to_named_reference_label|farthest_from_named_reference_label`
   - answer type: `option_letter`
   - evidence: two-box `bbox_set` around the named reference and selected labeled candidate
6. `task_icons__paired_canvas__original_attribute_label`
   - scene_id: `paired_canvas`
   - scaffold: two open panels labeled `Original` and `Right`; Right has six labeled tracked icons plus `4..8` unlabeled distractors
   - query_id: `original_shape_label|original_color_shape_label|original_fill_shape_label`
   - answer type: `option_letter`
   - evidence: two-box `bbox_set` around the original icon and its corresponding labeled Right-panel icon
7. `task_icons__overlap_grid__occlusion_order_count`
   - scene_id: `overlap_grid`
   - scaffold: `Reference` cell + labeled `Scene` grid of overlapping icon-pair cells
   - query_id: `same_front_to_back_order`
   - answer type: `integer`
   - evidence: `bbox_set` around matching Scene cells
8. `task_icons__paired_canvas__panel_movement_direction_count`
   - scene_id: `paired_canvas`
   - scaffold: two large panels labeled `Left` and `Right` with the same icons moved between panels
   - query_id: `moved_left_count|moved_right_count|moved_up_count|moved_down_count`
   - answer type: `integer`
   - evidence: Right-panel destination `bbox_set` over icons moved in the queried direction

### `transformation`
1. `task_icons__pair_grid__pair_attribute_rule_count`
   - scaffold: `Reference` pair + labeled `Scene` grid of icon pairs
   - query_id: `color_only_change|size_only_change|color_and_size_change`
   - answer type: `integer`
   - evidence: `bbox_set` around matching Scene cells
   - rule vocabulary: non-geometric color/size attribute edits only
2. `task_icons__pair_grid__pair_geometric_transform_count`
   - scaffold: `Reference` pair + labeled `Scene` grid of icon pairs
   - query_id: `same_pair_transform`
   - transform vocabulary: `rot90|rot180|rot270|flip_h|flip_v|flip_diag_main|flip_diag_anti`
   - answer type: `integer`
   - evidence: `bbox_set` around matching Scene cells
3. `task_icons__paired_canvas__panel_attribute_change_count`
   - scene_id: `paired_canvas`
   - scaffold: two large panels labeled `Left` and `Right` with corresponding icons at matching positions
   - query_id: `color_changed_count|size_changed_count|rotation_changed_count`
   - answer type: `integer`
   - evidence: Right-panel `bbox_set` over icons whose queried attribute changed

### `sequence`
1. `task_icons__sequence_strip__missing_count_value`
   - scaffold: one row of boxed icon-count sequence cells with one missing cell
   - query_id: `arithmetic_progression`
   - answer type: `integer`
   - evidence: one-box `bbox_set` over the missing cell

### `pattern`
1. `task_icons__pattern_grid__color_pattern_violation_index`
   - scene_id: `pattern_grid`
   - scaffold: numbered `3 x 3` grid
   - query_id: `grid_color_violation`
   - answer type: integer numbered-box index
   - evidence: one-box `bbox_set` over the violating numbered box
   - rule vocabulary: discrete hue ladder with row/column color-level offsets
2. `task_icons__sequence_strip__rotation_sequence_violation_index`
   - scene_id: `sequence_strip`
   - scaffold: numbered 10-cell sequence row
   - query_id: `row_rotation_violation`
   - answer type: integer numbered-box index
   - evidence: one-box `bbox_set` over the violating numbered box
3. `task_icons__pattern_grid__size_pattern_violation_index`
   - scene_id: `pattern_grid`
   - scaffold: numbered `3 x 3` grid
   - query_id: `grid_size_violation`
   - answer type: integer numbered-box index
   - evidence: one-box `bbox_set` over the violating numbered box
   - calibrated public mix uses a minimum two-level size violation and no icon-level noise so the size rule remains legible

## 4) Evidence policy
1. Use `bbox_set` when the witness is one or more visible icon instances.
2. Use `bbox_set` around the full cell when the witness is one or more labeled scene cells/pairs; keep labels only in private trace metadata.
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

# Icons Task Setup

This document captures the active `icons` domain contract.

For cross-domain coverage rollups, use `docs/project/STATUS.md` and `docs/domains/SCENE_TASK_QUERY_GUIDE.md` instead of repeating those inventories elsewhere.

## 1) Domain scope
1. `domain=icons` is for synthetic icon-scene reasoning over curated SVG icons
   under `assets/icons/` and TRACE-owned procedural named glyphs.
2. Icon tasks should test grounded visual comparison, spatial relation, sequence, pattern, transformation, or frequency reasoning over visible icon instances.
3. Prompt-facing annotation should stay on the semantic visual unit:
   - icon instances use `bbox_set`,
   - labeled cells/pairs use `bbox_set` over the cell,
   - missing or violating slots use one local `bbox_set`,
   - role-bound witnesses use `keyed_bbox_map` with global keyed annotation
     names rather than unordered two-box sets.
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
7. `named` is an internal implementation/taxonomy term for the procedural
   glyph vocabulary. Generated prompts should describe visible objects as
   `icons`, not `named icons`; target shape names should appear as quoted
   icon names such as `"bell"` icons.

## 3) Rendering and style policy
1. Icon scenes use the shared icon canvas-style adapter in
   `trace/tasks/icons/shared/scene_style.py`, backed by the cross-domain
   panel-style renderer.
2. The default treatment pool is restricted to light, low-saturation styles:
   `bare_canvas`, `plain_sheet`, `matte_sheet`, `thin_frame`, `soft_panel`,
   `margin_sheet`, `dot_sheet`, `worksheet_panel`, `index_card`, and
   `printout_panel`.
3. Dark, game-table, corkboard, and other high-contrast/heavy treatments are
   excluded by default because icon color, fill style, labels, rows, columns,
   regions, and paths can be answer-bearing.
4. Canvas style is non-semantic render metadata. It must not change task ids,
   query ids, answers, or annotation; annotation remains projected from the final
   composed image.
5. Task-local chrome overrides are allowed for concrete readability reasons;
   otherwise use the domain-level `icon_canvas_*` defaults from
   `configs/domains/icons/base.yaml`.

## 4) Active families
### `counting`
1. `task_icons__icon_field__type_frequency_count`
   - scene_id: `icon_field`
   - query_id: `singleton_type_count|most_frequent_type_count`
   - answer/annotation: `integer` / `bbox_set` over counted icons
2. `task_icons__reference_canvas__reference_attribute_match_count`
   - scene_id: `reference_canvas`
   - query_id: `match_type|match_color|match_rotation|match_type_color_rotation`
   - answer/annotation: `integer` / Scene-icon `bbox_set`
3. `task_icons__reference_canvas__reference_metric_relation_count`
   - scene_id: `reference_canvas`
   - query_id: `size_smaller|size_larger`
   - answer/annotation: `integer` / Scene-icon `bbox_set`
4. `task_icons__paired_canvas__panel_set_relation_count`
   - scene_id: `paired_canvas`
   - query_id: `right_exact_match_count|added_in_right_count|missing_from_right_count`
   - answer/annotation: `integer` / counted icon `bbox_set` in the relevant panel
5. `task_icons__named_field__single_attribute_membership_count`
   - scene_id: `named_field`
   - query_id: `named_shape_count`
   - answer/annotation: `integer` / target-shape icon `bbox_set`
   - arrangement support includes non-stack layouts and shape-stack layouts
6. `task_icons__named_field__multi_attribute_and_count`
   - scene_id: `named_field`
   - query_id: `shape_and_color_count`
   - answer/annotation: `integer` / qualifying icon `bbox_set`
7. `task_icons__named_field__multi_attribute_or_count`
   - scene_id: `named_field`
   - query_id: `shape_or_color_count`
   - answer/annotation: `integer` / qualifying icon `bbox_set`
8. `task_icons__named_field__multi_attribute_exclusion_count`
   - scene_id: `named_field`
   - query_id: `shape_and_not_color_count|color_and_not_shape_count`
   - answer/annotation: `integer` / qualifying icon `bbox_set`
9. `task_icons__named_field__multi_attribute_complement_count`
   - scene_id: `named_field`
   - query_id: `neither_shape_nor_color_count`
   - answer/annotation: `integer` / qualifying icon `bbox_set`
10. `task_icons__named_field__multi_attribute_xor_count`
    - scene_id: `named_field`
    - query_id: `exactly_one_shape_or_color_count`
    - answer/annotation: `integer` / qualifying icon `bbox_set`
11. `task_icons__named_field__count_arithmetic`
    - scene_id: `named_field`
    - query_id: `two_shape_total_count|two_bound_color_total_count|two_shape_difference_count|two_bound_color_difference_count`
    - answer/annotation: `integer` / `keyed_bbox_set_map` with `left_operand` and `right_operand` bbox lists
12. `task_icons__named_field__closer_to_reference_count`
    - scene_id: `named_field`
    - query_id: `closer_to_reference_a_count|closer_to_reference_b_count`
    - answer/annotation: `integer` / target-shape icon `bbox_set`
13. `task_icons__named_field__counterfactual_attribute_count`
    - scene_id: `named_field`
    - query_id: `target_count_after_shape_replacement|target_count_after_remove_and_replace`
    - answer/annotation: `integer` / visible icons counted after the hypothetical edit
14. `task_icons__named_field__counterfactual_total_count`
    - scene_id: `named_field`
    - query_id: `total_count_after_shape_removal`
    - answer/annotation: `integer` / visible icons counted after the hypothetical edit
15. `task_icons__named_field__scoped_attribute_count`
    - scene_id: `named_field`
    - query_id: `inside_shape_count|outside_shape_count|inside_band_count|outside_band_count|inside_quadrant_count|inside_shelf_count`
    - answer/annotation: `integer` / scoped target icon `bbox_set`
16. `task_icons__named_grid__scoped_attribute_count`
    - scene_id: `named_grid`
    - query_id: `row_shape_count|column_shape_count`
    - answer/annotation: `integer` / target icons in the addressed row or column
17. `task_icons__named_grid__row_column_shape_extreme_number`
    - scene_id: `named_grid`
    - query_id: `row_most_shape_number|row_fewest_shape_number|column_most_shape_number|column_fewest_shape_number`
    - answer/annotation: selected row/column number / target icons in the selected line
18. `task_icons__named_grid__group_predicate_count`
    - scene_id: `named_grid`
    - query_id: `row_at_least_shape_count|column_at_least_shape_count|row_exactly_shape_count|column_exactly_shape_count|row_no_shape_count|column_no_shape_count`
    - answer/annotation: `integer` / qualifying row or column region boxes
19. `task_icons__named_ring__scoped_attribute_count`
    - scene_id: `named_ring`
    - query_id: `clockwise_arc_shape_count|counterclockwise_arc_shape_count`
    - answer/annotation: `integer` / counted target icons along the selected arc
20. `task_icons__venn_field__scoped_attribute_count`
    - scene_id: `venn_field`
    - query_id: `inside_both_circles_count|inside_either_circle_count|inside_exactly_one_circle_count|outside_both_circles_count`
    - answer/annotation: `integer` / target icons whose centers satisfy the Venn predicate

### `relation`
1. `task_icons__reference_canvas__anchor_position_count`
   - scene_id: `reference_canvas`
   - scaffold: two-panel `Reference` + `Scene` with one marked `Anchor`
   - query_id: `left_of_anchor|right_of_anchor|above_anchor|below_anchor`
   - internal axis: `direction=left|right|above|below`
   - answer type: `integer`
   - annotation: scene-only `bbox_set` over matching icon instances
2. `task_icons__two_anchor__between_anchors_count`
   - scene_id: `two_anchor`
   - scaffold: single-panel scene with anchors `A` and `B`
   - query_id: `inside_vertical_strip|inside_horizontal_strip`
   - internal axis: `strip_axis=vertical|horizontal`
   - answer type: `integer`
   - annotation: scene-only `bbox_set` over matching icon instances
3. `task_icons__mirror_grid__mirror_symmetry_count`
   - scene_id: `mirror_grid`
   - scaffold: `Reference` cell + labeled `Scene` grid of icon-arrangement cells; grid labels are fixed row-major `A`..`F`
   - query_id: `mirror_vertical|mirror_horizontal|mirror_diagonal_main|mirror_diagonal_anti|mirror_both_axes`
   - answer type: `integer`
   - annotation: `bbox_set` around matching Scene cells
4. `task_icons__icon_cutout__partial_match_label`
   - scene_id: `icon_cutout`
   - scaffold: left partial icon fragment plus six labeled full-icon options
     `A`..`F`
   - query_id: `partial_icon_match_label`
   - answer type: `option_letter`
   - annotation: `keyed_bbox_map` with `source_fragment` and
     `selected_option`
   - visual variants: rectangular, rounded, and elliptical fragment windows;
     these are render metadata rather than separate query ids
5. `task_icons__named_field__reference_distance_rank_label`
   - scene_id: `named_field`
   - scaffold: single-panel scene with one unique prompt-named reference icon, six option icons labeled `A`..`F`, and `4..8` other icons
   - query_id: `closest_to_named_reference_label|second_closest_to_named_reference_label|farthest_from_named_reference_label`
   - answer type: `option_letter`
   - annotation: `keyed_bbox_map` with `reference_icon` and `selected_candidate`
6. `task_icons__named_path__path_neighbor_label`
   - scene_id: `named_path`
   - scaffold: single-panel scene with a continuous path from `START` to
     `END`, procedural named icons on path stops, six labeled option icons
     `A`..`F`, and `4..8` other non-target stops
   - query_id:
     `after_first_shape_label|before_first_shape_label|after_last_shape_label|before_last_shape_label|after_second_shape_label|before_second_shape_label`
   - answer type: `option_letter`
   - annotation: `keyed_bbox_map` with `queried_icon` and `selected_neighbor`
   - target support: all procedural named glyphs listed in the asset policy;
     target names are quoted in prompts
7. `task_icons__paired_canvas__original_attribute_label`
   - scene_id: `paired_canvas`
   - scaffold: two open panels labeled `Original` and `Right`; Right has six tracked option icons labeled `A`..`F` plus `4..8` other icons
   - query_id: `original_shape_label|original_color_shape_label|original_fill_shape_label`
   - answer type: `option_letter`
   - annotation: `keyed_bbox_map` with `original_icon` and `right_icon`
8. `task_icons__overlap_grid__occlusion_order_count`
   - scene_id: `overlap_grid`
   - scaffold: `Reference` cell + labeled `Scene` grid of overlapping icon-pair cells; grid labels are fixed row-major `A`..`F`
   - query_id: `same_front_to_back_order`
   - answer type: `integer`
   - annotation: `bbox_set` around matching Scene cells
9. `task_icons__paired_canvas__panel_movement_direction_count`
   - scene_id: `paired_canvas`
   - scaffold: two large panels labeled `Left` and `Right` with the same icons moved between panels
   - query_id: `moved_left_count|moved_right_count|moved_up_count|moved_down_count`
   - answer type: `integer`
   - annotation: Right-panel destination `bbox_set` over icons moved in the queried direction

### `transformation`
1. `task_icons__pair_grid__attribute_delta_pair_count`
   - scene_id: `pair_grid`
   - query_id: `color_only_change|size_only_change|color_and_size_change`
   - answer/annotation: `integer` / matching Scene-cell `bbox_set`
   - rule vocabulary: color/size attribute edits
2. `task_icons__pair_grid__reference_transform_match_count`
   - scene_id: `pair_grid`
   - query_id: `same_pair_transform`
   - answer/annotation: `integer` / matching Scene-cell `bbox_set`
   - rule vocabulary: geometric before-to-after transforms
3. `task_icons__single_transform_options__geometric_transform_result_label`
   - scene_id: `single_transform_options`
   - scaffold: one Reference icon with a visible transform cue plus six labeled option icons `A`..`F`
   - query_id: `rotate_90_clockwise_result_label|rotate_90_counterclockwise_result_label|rotate_180_result_label|flip_horizontal_result_label|flip_vertical_result_label`
   - answer/annotation: `option_letter` / `keyed_bbox_map` with `reference_icon` and `selected_option`
   - rule vocabulary: geometric result selection over non-symmetric curated icons
4. `task_icons__paired_canvas__panel_attribute_change_count`
   - scene_id: `paired_canvas`
   - scaffold: two large panels labeled `Left` and `Right` with corresponding icons at matching positions
   - query_id: `color_changed_count|size_changed_count|rotation_changed_count`
   - answer/annotation: `integer` / Right-panel `bbox_set` over icons whose queried attribute changed

### `sequence`
1. `task_icons__sequence_strip__missing_count_value`
   - scaffold: one row of boxed icon-count sequence cells with one missing cell
   - query_id: `arithmetic_progression`
   - answer type: `integer`
   - annotation: one-box `bbox_set` over the missing cell
2. `task_icons__named_strip__shape_run_length`
   - scaffold: one horizontal row of boxed named icons
   - query_id: `longest_shape_run_length|shortest_shape_run_length`
   - answer type: `integer`
   - annotation: `bbox_set` over the icons in the selected target-shape run
   - answer support: longest `2..6`, shortest `1..5`
   - target support: all procedural named glyphs listed in the asset policy;
     target names are quoted in prompts

### `pattern`
1. `task_icons__pattern_grid__attribute_pattern_violation_index`
   - scene_id: `pattern_grid`
   - scaffold: numbered `3 x 3` grid
   - query_id: `grid_color_violation|grid_size_violation`
   - answer type: integer numbered-box index
   - annotation: one-box `bbox_set` over the violating numbered box
   - rule vocabulary: discrete hue ladder or icon-size ladder with row/column offsets
2. `task_icons__sequence_strip__rotation_sequence_violation_index`
   - scene_id: `sequence_strip`
   - scaffold: numbered 10-cell sequence row
   - query_id: `row_rotation_violation`
   - answer type: integer numbered-box index
   - annotation: one-box `bbox_set` over the violating numbered box
3. `task_icons__wallpaper_panels__motif_violation_label`
   - scene_id: `wallpaper_panels`
   - scaffold: six labeled wallpaper panels; five share the same continuous repeated icon-motif wallpaper pattern and one uses a different wallpaper pattern; no internal tile/grid lines are drawn
   - query_id: `wallpaper_motif_violation_label`
   - answer type: `option_letter`
   - annotation: one `bbox_set` over the selected odd wallpaper panel
   - rule vocabulary: visually distinct subset of standard wallpaper groups (`p1`, `p2`, `pm`, `pg`, `cm`, `pmm`, `p4`, `p3`)
   - asset policy: curated asymmetric icons from `assets/icons/non_symmetry.txt`; panels use different sampled icons while sharing tint and size, so icon identity is non-semantic and the answer depends on arrangement
   - render policy: quiet canvas treatments only; no ruled, worksheet, dot-sheet, or grid-like chrome inside motif panel areas
4. `task_icons__wallpaper_panels__same_pattern_as_reference_label`
   - scene_id: `wallpaper_panels`
   - scaffold: one Reference wallpaper panel plus six labeled wallpaper panels; exactly one candidate shares the Reference wallpaper group and the other candidates use distinct other groups
   - query_id: `same_pattern_as_reference_label`
   - answer type: `option_letter`
   - annotation: `keyed_bbox_map` with `reference_panel` and `selected_panel`
   - asset policy: curated asymmetric icons from `assets/icons/non_symmetry.txt`; all panels use different sampled icons while sharing tint and size, so the answer depends on arrangement
   - render policy: quiet canvas treatments only; no ruled, worksheet, dot-sheet, or grid-like chrome inside motif panel areas
5. `task_icons__wallpaper_panels__reference_pattern_match_count`
   - scene_id: `wallpaper_panels`
   - scaffold: one Reference wallpaper panel plus six labeled wallpaper panels; one to five candidates share the Reference wallpaper group and the other candidates use distinct other groups
   - query_id: `reference_pattern_match_count`
   - answer type: integer count
   - annotation: `keyed_bbox_set_map` with `reference_panel` and `matching_candidate_panels`
   - asset policy: curated asymmetric icons from `assets/icons/non_symmetry.txt`; all panels use different sampled icons while sharing tint and size, so the answer depends on arrangement
   - render policy: quiet canvas treatments only; no ruled, worksheet, dot-sheet, or grid-like chrome inside motif panel areas
## 5) Annotation policy
1. Use `bbox_set` when the witness is one or more visible icon instances.
2. Use `bbox_set` around the full cell when the witness is one or more labeled scene cells/pairs; keep labels only in private trace metadata.
3. Use a single local `bbox_set` when the witness is a missing or violating slot.
4. Use `keyed_bbox_map` when distinct witness roles must be verified, such as
   reference versus selected candidate, queried icon versus selected neighbor,
   original versus right-panel icon, or left versus right arithmetic operands.
5. Keep hidden asset ids, sampled transforms, nominal sizes, and ambiguity checks in trace metadata; prompt-facing annotation should stay visual and compact.

## 6) Ambiguity policy
1. Use explicit target/distractor sampling rather than hoping random placement realizes the target count.
2. Enforce minimum size gaps for size-relation tasks.
3. For anchored relation tasks, mix distractor types so the task cannot be solved by occupancy alone.
4. For mirror-symmetry tasks, use square cells, exact rendered-image signatures, even icon counts, and the asymmetric icon pool where needed.
5. For geometric result-option tasks, use `non_symmetry.txt` and exact transform signatures so identity, rotations, and flips are visually distinct before accepting an instance.
6. For pattern-violation tasks, reject any instance where another supported rule hypothesis would make a different violating cell plausible.
7. For singleton-type tasks, define grouping over `icon_id` only; colors and rotations may vary independently.

## 7) Shared helper placement
1. Icon asset loading belongs in `trace/tasks/icons/shared/icon_assets.py`.
2. Shared icon scene/rendering helpers belong under `trace/tasks/icons/shared/`.
3. Reuse the existing grid, sequence, pair-grid, overlap-grid, transform, style, and anchor-marking helpers before adding task-local layout/rendering utilities.

# Icons Coverage Extension

## Scope

This note tracks icon-domain coverage gaps found from external benchmark
failure analysis and records what remains worth adding after the recent
`named_field_canvas` expansion.

Current conclusion: `icons` now has strong controlled-glyph coverage for
single-panel counting, named-shape recognition, shape/color Boolean filtering,
two-group count arithmetic, single-region and Venn-region filtered counts,
relative-distance counts against two references, counterfactual
removal/replacement counts, paired-panel changes, spatial anchors,
reflection/mirror matching, occlusion-order matching, sequence counts, and
simple pattern violations.

The remaining worthwhile additions are not more variants of plain count
filtering. They are new capabilities: extra metadata-backed visual attributes,
distance/rank spatial relations, direct correspondence label outputs, direct
layer/contact queries, and controlled icon-matrix/analogy patterns.

## Boundary Rule

- Use `icons` when the source of truth is a synthetic glyph instance, its
  controlled visual attributes, image-plane position, draw order, or symbolic
  relation to another glyph or panel.
- Use `illustrations` when the object is a recognizable real-world thing with
  semantic parts, affordance, material, pose, or scene context.
- Use `pages` when the icon is part of a UI, form, toolbar, infographic,
  document, or command-target grounding problem.
- Use `puzzles` when icon-like marks are cells in a hidden-rule puzzle, Raven
  matrix, jigsaw, tiling problem, or logic-grid state.
- Use `three_d` when viewpoint, depth, lighting, camera distance, or true 3D
  geometry is the verifier source of truth.
- Use `charts` for pictogram charts where repeated icons encode quantitative
  values; use `icons` only when the task is about the glyph scene itself.

## Implemented Coverage

### Core Icon Tasks

Existing active task families already cover:

- Single- and multi-attribute reference matching:
  `proposal:icons/counting/single_attribute_match_count`,
  `proposal:icons/counting/multi_attribute_match_count`,
  `proposal:icons/counting/size_relation`.
- Frequency/count structure:
  `proposal:icons/counting/most_frequent_type_count`,
  `proposal:icons/counting/singleton_type`.
- Paired-panel count/change reasoning:
  `proposal:icons/counting/panel_exact_match_count`,
  `proposal:icons/counting/panel_added_removed_count`,
  `proposal:icons/relation/panel_movement_direction_count`,
  `proposal:icons/transformation/panel_attribute_change_count`.
- Pair transformations:
  `proposal:icons/transformation/pair_count`,
  `proposal:icons/transformation/pair_attribute_rule_count`.
- Spatial and layering relations:
  `proposal:icons/relation/relative_position_type`,
  `proposal:icons/relation/between_two_anchors_count`,
  `proposal:icons/relation/occlusion_order`.
- Reflection/mirror matching:
  `proposal:icons/relation/mirror_symmetry`,
  `proposal:icons/relation/reflection_match_label`.
- Sequence and pattern tasks:
  `proposal:icons/sequence/missing_count`,
  `proposal:icons/pattern/grid_color_violation`,
  `proposal:icons/pattern/grid_size_violation`,
  `proposal:icons/pattern/sequence_rotation_violation`.

### Named Icon Field Expansion

The initial dense-symbol/semantic-shape gap has been addressed inside
`named_field_canvas` rather than by adding a separate
`dense_icon_field_canvas` scene. The shared procedural vocabulary now has 100
named shapes:

circle, ring, square, triangle, pentagon, hexagon, octagon, star, heart,
crescent, check mark, arrow, sun, lightning bolt, cloud, flower, leaf, shield,
flag, crown, house, capsule, teardrop, hourglass, key, bell, ladder, kite,
mushroom, fish, butterfly, umbrella, anchor, car, boat, rocket, envelope,
book, pencil, camera, lock, magnifying glass, trophy, cup, music note,
battery, clock, gift, shoe, shirt, glasses, snowman, tree, bird, apple,
balloon, shuriken, gear, puzzle piece, lightbulb, lantern, candle, bottle,
bucket, shovel, fork, spoon, pizza slice, egg, dice, microphone,
headphones, chair, tent, phone, television, laptop, watch, bus, train, bicycle,
bed, lamp, door, window, mailbox, toothbrush, broom, trash can, teapot, knife,
soccer ball, rugby ball, dumbbell, calculator, plug, broccoli,
cactus, guitar, and acorn.

Implemented tasks:

- `proposal:icons/counting/named_shape_count`
  - Counts prompt-named procedural shapes.
  - Includes grid, shelf, scatter, and compact target-stack layouts.
  - Fill style is non-semantic visual variation for this task.
  - Accepted after range tuning: qwen25vl7b hard `0.110`, easy `0.070`,
    mean `0.278`.
- `proposal:icons/counting/named_shape_color_boolean_count`
  - Counts Boolean predicates over named shape plus a secondary visual
    attribute. The secondary attribute is color with probability `0.5` and
    fill style with probability `0.5`.
  - Supported fill styles are solid, striped, dotted, and half-filled; only
    striped, dotted, and half-filled are queried directly.
  - Query branches:
    `shape_and_color_count`, `shape_or_color_count`,
    `shape_and_not_color_count`, `color_and_not_shape_count`,
    `neither_shape_nor_color_count`, and
    `exactly_one_shape_or_color_count`.
  - Accepted: qwen25vl7b hard `0.180`, easy `0.080`, mean `0.325`.
- `proposal:icons/counting/named_shape_region_count`
  - Counts named shapes inside/outside marked shapes, bands, quadrants, and
    shelves.
  - Uses bbox-clearance placement for queried target-shape icons so targets do
    not touch/cross the queried boundary.
  - Fill style is non-semantic visual variation for this task.
  - Accepted: qwen25vl7b hard `0.160`, easy `0.040`, mean `0.306`.
- `proposal:icons/counting/named_shape_venn_region_count`
  - Adds the `named_icon_venn_canvas` scene with two visible overlapping
    marked circles.
  - Query branches count target icons inside both circles, inside either
    circle, inside exactly one circle, or outside both circles.
  - Target modes are shape-only, color+shape, and fill-style+shape; the prompt
    quotes the named shape, e.g. `"bell"`.
  - Evidence contains only counted target-icon boxes. Icons are sampled with
    bbox clearance from circle boundaries so queried targets do not touch or
    cross the Venn boundary.
  - Calibration status: review workbook and scene review generated;
    distribution gate passed on cumulative `400`-sample validation. qwen25vl7b
    solve-rate is pending.
- `proposal:icons/counting/named_shape_counterfactual_count`
  - Counts after hypothetical visible-evidence edits:
    target count after shape replacement, total count after shape removal, and
    target count after removal plus replacement.
  - Current answer support is `1..8`; distractors are `2..8`.
  - Fill style is non-semantic visual variation for this task.
  - Accepted: qwen25vl7b hard `0.180`, easy `0.150`, mean `0.292`.
- `proposal:icons/counting/named_shape_pair_arithmetic_count`
  - Counts over two independently named operand groups.
  - Query branches ask for total count or absolute difference over two shapes
    or two color-bound shape groups.
  - Difference answers include `0`; operand evidence contains every visible
    icon in either group.
  - Fill style is non-semantic visual variation for this task.
  - Accepted: qwen25vl7b hard `0.130`, easy `0.080`, mean `0.279`.
- `proposal:icons/counting/named_shape_closer_to_reference_count`
  - Counts repeated target-shape icons closer to reference `A` or `B`.
  - Uses only three object types: reference `A`, reference `B`, and the target
    shape. There are no unrelated distractor icon types.
  - Evidence contains counted target icons only; references remain in trace.
  - Accepted: qwen25vl7b hard `0.130`, easy `0.020`, mean `0.250`.
- `proposal:icons/relation/named_original_attribute_label`
  - Adds the first paired `paired_named_icon_canvas` scene.
  - The Right panel has six labeled tracked icons plus `4..8` unlabeled
    distractors; the Original panel shows their original named-icon state.
  - Query branches ask which Right-panel label was originally a named shape,
    color+shape, or fill-style+shape. Three-attribute bindings are intentionally
    excluded.
  - Accepted: qwen25vl7b hard `0.100`, easy `0.050`, mean `0.291`.

These implemented tasks cover the earlier proposals for dense named shape
counting, shape/color-or-style Boolean logic, region membership counts, and
counterfactual removal/replacement counts, plus overlapping set/Venn
membership, the two-group count-arithmetic contract, and a two-reference
relative-distance count contract. They should no longer be treated as open
icon-domain gaps.

## Remaining Genuinely New Capabilities

### M1. Controlled Visual Attribute Expansion

Status: `mostly addressed / selectively scoped`

Current icon attributes cover icon id/type, named procedural shape, color,
rotation, size, panel membership, position, and draw order. Benchmarks still
include visual-attribute reasoning that is not naturally represented by these
axes.

Implemented and accepted scope:

- fill style: solid, striped, dotted, half-filled
- semantic fill-style binding in
  `proposal:icons/counting/named_shape_color_boolean_count`
- non-semantic fill-style visual variation in the other
  `named_field_canvas` tasks

Explicitly deferred or avoided:

- checker/crosshatch fill patterns: too close to dotted/striped under noise
- thin/thick outline: small stroke-width differences are fragile under
  downsampling, blur, JPEG, and icon-size variation
- dashed/double outline: visually ambiguous at small icon sizes and likely to
  conflict with global noise
- standalone `proposal:icons/counting/named_shape_visual_attribute_count`: current
  Boolean task already supports shape plus color/fill-style binding; a
  standalone fill-style count would be a thin duplicate right now

Possible future metadata-backed attributes, only if a review pass shows they
remain visually robust:

- small badge marker: dot, ring, slash, corner mark
- background shape behind glyph: circle, square, rounded tile

Possible future tasks:

- `proposal:icons/transformation/panel_visual_attribute_change_count`, if we want a
  paired-panel task over fill-style changes specifically
- `proposal:icons/counting/badge_marker_count`, if badge markers are added as a
  distinct visual axis
- `proposal:icons/counting/background_tile_shape_count`, if tile backgrounds are
  added as a distinct visual axis

Do not add material, reflectance, pose, brand/logo, species, or real-world
function here; those belong in `illustrations`, `three_d`, or `pages`.

### M2. Distance And Rank Spatial Relations

Status: `partially addressed`

Current icon spatial tasks cover side-of-anchor, between two anchors, and
region membership. They do not ask for image-plane nearest/farthest or distance
rank.

Implemented:

- `proposal:icons/relation/named_reference_distance_rank_label`
  - Uses a unique prompt-named reference icon instead of a generic anchor.
  - Renders six labeled candidates `A`..`F`, `4..8` unlabeled distractors,
    and one single reference icon.
  - Query ids: `closest_to_named_reference_label`,
    `second_closest_to_named_reference_label`, and
    `farthest_from_named_reference_label`.
  - Accepted: qwen25vl7b hard `0.060`, easy `0.000`, mean `0.225`.

Still possible, but lower priority unless benchmarks show a clear gap:

- `proposal:icons/counting/within_radius_count`
- paired-panel distance-rank variants over transformed layouts
- richer multi-target closer-to-reference variants with distractor object
  types, if the simple three-type version is too easy after calibration

Preferred answer type is a label for a uniquely marked candidate icon, with
`bbox_set` evidence for the selected icon and reference icon. Physical near/far
or camera-distance reasoning stays in `three_d`.

### M3. Multi-Panel Correspondence Label Outputs

Status: `partially addressed`

Current paired-panel tasks count exact matches, additions/removals, movement
directions, and attribute changes. They do not usually ask which labeled target
corresponds to a marked source icon after a controlled transformation.

Candidate tasks:

- `proposal:icons/relation/named_original_attribute_label` (implemented first pass)
- `proposal:icons/relation/panel_corresponding_icon_label`
- `proposal:icons/relation/transformed_match_label`
- `proposal:icons/relation/moved_icon_destination_label`

The task should use labeled candidate icons or cells and enforce exactly one
correspondence by construction. This is meaningfully different from the current
count outputs.

### M4. Direct Layering, Contact, And Partial-Occlusion Queries

Status: `missing`

Current icon occlusion coverage is mostly option-style occlusion-order
matching. Direct 2D draw-order and contact questions remain useful if they stay
explicitly image-plane based.

Candidate tasks:

- `proposal:icons/relation/front_icon_label`
- `proposal:icons/relation/back_icon_label`
- `proposal:icons/counting/partly_occluded_count`
- `proposal:icons/counting/touching_pair_count`
- `proposal:icons/relation/same_layering_match_label`

The prompt must state that front/back means visible draw order, not 3D depth.
Semantic part occlusion belongs in `illustrations`; true depth/camera
occlusion belongs in `three_d`.

### M5. Icon Matrix And Analogy Patterns

Status: `boundary-sensitive / missing`

Current icon pattern tasks cover single violations and count sequences. BLINK
and MathVision-style failures include matrix completion and analogy patterns,
but broad Raven/IQ reasoning is primarily a `puzzles` concern.

Icon-owned versions are useful only when:

- all units are controlled icon glyphs,
- the rule is over explicit icon attributes,
- the answer is a candidate label or cell label,
- no free-form rule explanation is required.

Candidate tasks:

- `proposal:icons/pattern/attribute_matrix_completion_label`
- `proposal:icons/pattern/transform_analogy_label`
- `proposal:icons/pattern/rule_matching_count`

### M6. Optional Label-Output Grounding Over Icon Fields

Status: `low-priority / boundary-sensitive`

Icon evidence already contains bboxes, and ScreenSpotPro-style GUI grounding
belongs in `pages`. A small icon-owned grounding task can still be useful if
the scene labels icons or cells and asks for the label of the unique glyph
matching a condition.

Candidate tasks:

- `proposal:icons/relation/named_field_target_label`
- `proposal:icons/counting/unique_condition_icon_label`

Use label outputs, not raw point/bbox answers, unless there is a separate
project-wide reason to add point-output icon tasks.

## Lower-Priority Or Avoid

### Plain Count Arithmetic

Status: `addressed`

Plain `A or B`, `A but not B`, and complement-style questions are covered by
`proposal:icons/counting/named_shape_color_boolean_count`. Hypothetical remaining
counts are covered by `proposal:icons/counting/named_shape_counterfactual_count`.
The genuinely different two-operand arithmetic contract is now represented by
`proposal:icons/counting/named_shape_pair_arithmetic_count`, which asks for
`count(A) + count(B)` or `abs(count(A) - count(B))` over independently named
visible groups.

### More Dense Rendering Modes

Status: `rendering/style backlog`

`proposal:icons/counting/named_shape_count` now covers compact stacks and denser
single-panel named icon fields. More wall/tile/table-like arrangements may be
useful for visual diversity, but they are not a new reasoning capability unless
paired with a genuinely new task contract.

### Neighboring-Domain Gaps

Do not solve these inside `icons`:

- GUI icon command grounding: `pages`.
- Natural object counting and scene context: `illustrations`.
- Semantic part correspondence and affordance: `illustrations`.
- Reflectance, camera/light changes, true depth, and viewpoint: `three_d`.
- Broad Raven/IQ puzzle rules: `puzzles`.
- Pictogram charts where repeated icons encode values: `charts`.

## Suggested Next Wave

1. Add one multi-panel correspondence label task.
2. Add a paired-panel fill-style-change task only if we specifically want to
   extend the accepted fill-style axis beyond the current Boolean task.
3. Add direct layer/contact queries if benchmark failures continue to show
   image-plane occlusion/contact patterns.
4. Add within-radius counting only if distance/rank failures continue after
   `proposal:icons/relation/named_reference_distance_rank_label`.
5. Defer icon-matrix/analogy patterns until we decide the exact boundary with
   `puzzles`.

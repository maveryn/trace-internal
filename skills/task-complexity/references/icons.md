# Icons Complexity

## Domain policy
Use icon-specific criteria. Do not reuse generic counting formulas once a task has richer structure than "more objects = harder".

## Recommended criteria vocabulary
- `visual_scan`
  - how many icons or cells must be checked
- `predicate_complexity`
  - how many independent attributes or conditions define a match
- `spatial_reasoning`
  - anchors, sides, strips, or center-based spatial membership
- `transform_reasoning`
  - rotation, reflection, or transform-rule application
- `sequence_reasoning`
  - missing-step or progression inference
- `ambiguity`
  - near-miss distractors, hard partial matches, or boundary-adjacent cases
- `clutter`
  - overlap, icon size, noise, and cell density

## Domain fallback weights
Use these when a new icon task group appears and no family override exists yet:

```yaml
visual_scan: 0.20
predicate_complexity: 0.20
spatial_reasoning: 0.15
transform_reasoning: 0.15
sequence_reasoning: 0.10
ambiguity: 0.10
clutter: 0.10
```

## Task-group overrides

### `counting`
```yaml
visual_scan: 0.30
predicate_complexity: 0.30
ambiguity: 0.25
clutter: 0.15
spatial_reasoning: 0.00
transform_reasoning: 0.00
sequence_reasoning: 0.00
```

Use for:
- `task_icons_counting_type`
- `task_icons_counting_color`
- `task_icons_counting_orientation`
- `task_icons_counting_size_relation`
- `task_icons_counting_attribute_binding`

What to measure:
- icon count / cell count,
- overlap and icon-size readability,
- hard-distractor share,
- number of queried attributes.

Specific notes:
- `type` / `color` / `orientation` should keep `predicate_complexity` low.
- `attribute_binding` should push `predicate_complexity` and `ambiguity` high based on `2-of-3` / `1-of-3` distractor mix.
- `size_relation` should raise `ambiguity` when the minimum size gap is small and clutter rises.

### `relation`
```yaml
visual_scan: 0.20
predicate_complexity: 0.10
spatial_reasoning: 0.35
ambiguity: 0.25
clutter: 0.10
transform_reasoning: 0.00
sequence_reasoning: 0.00
```

Use for:
- `task_icons_relation_relative_position_type`
- `task_icons_relation_between_two_anchors_count`
- `task_icons_relation_occlusion_order`
- `task_icons_relation_mirror_symmetry`

Task-specific notes:
- `relative_position_type`
  - measure same-type wrong-side distractors,
  - different-type queried-side distractors,
  - anchor-boundary clearance,
  - queried-side crowding.
- `between_two_anchors_count`
  - measure strip width, boundary margin, and candidate crowding inside/outside the strip.
- `occlusion_order`
  - treat pair-level front/back distinction as high `predicate_complexity` or fold it into `ambiguity`.
- `mirror_symmetry`
  - shift weight from `spatial_reasoning` into `transform_reasoning` if needed;
  - diagonal and both-axis variants should score harder than plain vertical/horizontal;
  - exact-other-signature distractors should raise `ambiguity`.

### `transformation`
```yaml
visual_scan: 0.20
transform_reasoning: 0.45
ambiguity: 0.20
clutter: 0.15
predicate_complexity: 0.00
spatial_reasoning: 0.00
sequence_reasoning: 0.00
```

Use for:
- `task_icons_transformation_pair_count`

What to measure:
- transform family difficulty,
- candidate-cell count,
- distractor transform similarity,
- within-cell readability.

### `sequence`
```yaml
visual_scan: 0.25
sequence_reasoning: 0.45
ambiguity: 0.20
clutter: 0.10
predicate_complexity: 0.00
spatial_reasoning: 0.00
transform_reasoning: 0.00
```

Use for:
- `task_icons_sequence_missing_count`

What to measure:
- row length,
- total visible icons across cells,
- missing-position difficulty (interior > end),
- step-size difficulty (`1` harder than `3`),
- per-cell clutter.

## Practical normalization hints
- `visual_scan`
  - normalize from visible icon count or cell count under the task's configured support.
- `predicate_complexity`
  - normalize from number of independent queried attributes or conjunction depth.
- `ambiguity`
  - normalize from the proportion of hard distractors / boundary-near distractors.
- `clutter`
  - normalize from overlap fraction, icon size band, and noise intensity.

## Anti-pattern
- Do not reuse `counting_complexity_score(object_count, target_count)` as the final icon complexity formula once a task has meaningful distractor hardness, transform load, or sequence reasoning.

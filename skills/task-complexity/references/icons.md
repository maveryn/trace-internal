# Icons Complexity

## Domain policy
Use icon-specific criteria. Do not reuse generic counting formulas once a task has richer structure than "more objects = harder".

## Domain-level base criteria
These should be applicable to **all** icon tasks:
- `visual_scan`
  - how much of the scene/cell inventory must be inspected
- `ambiguity`
  - how hard it is to separate positives from distractors or reject near-misses
- `clutter`
  - overlap, icon size, noise, and density effects that reduce readability

## Domain fallback weights
Use these as the broad baseline. Task groups can add specialized criteria on top:

```yaml
visual_scan: 0.40
ambiguity: 0.35
clutter: 0.25
```

## Task-group overrides

### `counting`
```yaml
semantic_match: 0.35
visual_scan: 0.30
ambiguity: 0.20
clutter: 0.15
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
- `type` / `color` / `orientation` should keep `semantic_match` low-to-medium.
- `attribute_binding` should push `semantic_match` and `ambiguity` high based on `2-of-3` / `1-of-3` distractor mix.
- `size_relation` should raise `ambiguity` when the minimum size gap is small and clutter rises.

### `relation`
```yaml
spatial_reasoning: 0.40
visual_scan: 0.20
ambiguity: 0.25
clutter: 0.15
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
  - treat pair-level front/back distinction as high ambiguity or as a rare task override if needed.
- `mirror_symmetry`
  - may need a rare task-level shift from `spatial_reasoning` toward transform-style reasoning;
  - diagonal and both-axis variants should score harder than plain vertical/horizontal;
  - exact-other-signature distractors should raise `ambiguity`.

### `transformation`
```yaml
rule_inference: 0.45
visual_scan: 0.20
ambiguity: 0.20
clutter: 0.15
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
rule_inference: 0.45
visual_scan: 0.25
ambiguity: 0.20
clutter: 0.10
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
- `semantic_match`
  - normalize from number of independent queried attributes or conjunction depth.
- `spatial_reasoning`
  - normalize from anchor complexity, region inference, and boundary sensitivity.
- `rule_inference`
  - normalize from transform-rule or sequence-rule depth.
- `ambiguity`
  - normalize from the proportion of hard distractors / boundary-near distractors.
- `clutter`
  - normalize from overlap fraction, icon size band, and noise intensity.

## Anti-pattern
- Do not reuse `counting_complexity_score(object_count, target_count)` as the final icon complexity formula once a task has meaningful distractor hardness, transform load, or sequence reasoning.

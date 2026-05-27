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
- `task_icons__reference_canvas__attribute_match_count`
- `task_icons__reference_canvas__size_relation_count`
- `task_icons__icon_field__type_frequency_count`
- named-field counting tasks on `named_field`
- paired-panel counting tasks on `paired_canvas`

What to measure:
- icon count / cell count,
- overlap and icon-size readability,
- hard-distractor share,
- number of queried attributes.

Specific notes:
- `task_icons__reference_canvas__attribute_match_count`
  - `match_type|match_color|match_rotation` should keep `semantic_match` low-to-medium.
  - bound type+color+rotation matching should push `semantic_match` and `ambiguity` high based on near-match distractor mix.
- `size_relation` should raise `ambiguity` when the minimum size gap is small and clutter rises.
- `type_frequency_count` should raise `ambiguity` with more distinct scene types and more repeated groups while keeping `semantic_match` low because the predicate still groups on icon identity alone.

### `relation`
```yaml
spatial_reasoning: 0.40
visual_scan: 0.20
ambiguity: 0.25
clutter: 0.15
```

Use for:
- `task_icons__reference_canvas__anchor_position_count`
- `task_icons__two_anchor__between_anchors_count`
- `task_icons__overlap_grid__occlusion_order_count`
- `task_icons__mirror_grid__mirror_symmetry_count`
- `task_icons__mirror_grid__reflection_match_label`
- `task_icons__named_field__reference_distance_rank_label`
- `task_icons__paired_canvas__original_attribute_label`

Task-specific notes:
- `anchor_position_count`
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
- `task_icons__pair_grid__pair_geometric_transform_count`
- `task_icons__pair_grid__pair_attribute_rule_count`
- `task_icons__paired_canvas__panel_attribute_change_count`
- `task_icons__paired_canvas__panel_movement_direction_count`

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
- `task_icons__sequence_strip__missing_count_value`

What to measure:
- row length,
- total visible icons across cells,
- missing-position difficulty (interior > end),
- step-size difficulty (`1` harder than `3`),
- per-cell clutter.

### `pattern`
```yaml
rule_inference: 0.45
visual_scan: 0.25
ambiguity: 0.20
clutter: 0.10
```

Use for:
- `task_icons__pattern_grid__color_pattern_violation_index`
- `task_icons__pattern_grid__size_pattern_violation_index`
- `task_icons__sequence_strip__rotation_sequence_violation_index`

What to measure:
- grid size / visible cell inventory,
- rule richness (for example how many distinct rotations or size levels appear and whether both row/column axes matter),
- violating-cell ambiguity,
- per-cell readability.

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

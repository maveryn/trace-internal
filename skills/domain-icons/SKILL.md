---
name: domain-icons
description: Use when designing, implementing, or reviewing TRACE icon-domain tasks, especially for curated Prism icon pool selection, reference-vs-scene layout choices, evidence typing, and icon-specific ambiguity checks.
---

# Icon Domain

Use this whenever the task lives under `domain=icons`.

## Read first
1. `docs/project/STATUS.md`
2. `docs/domains/TASK_FAMILY_VARIANTS.md`
3. `docs/workflows/TASK_AUTHORING.md`
4. `docs/workflows/CODE_REVIEW_GUIDELINES.md`
5. `docs/workflows/SHARED_UTILITIES.md`

## Icon-domain asset policy
- TRACE uses the curated Prism icon bundle under `assets/icons/`.
- Current manifests:
  - `all_icons.txt` = `3000` total icons
  - `non_symmetry.txt` = `2000` asymmetric icons
  - `symmetry.txt` = `1000` symmetric icons
- Resolve manifests only through `trace/tasks/icons/shared/icon_assets.py`.

## Manifest selection rules
- Use `non_symmetry.txt` when the task depends on any property that can collapse under symmetry:
  - orientation / rotation matching,
  - mirror symmetry,
  - transformation identity,
  - multi-attribute binding that includes orientation.
- Use `all_icons.txt` when symmetry is not part of the queried predicate:
  - type,
  - color,
  - size,
  - pure spatial relation,
  - sequence counts,
  - occlusion order.
- If unsure, bias toward `non_symmetry.txt`; a weaker pool is better than a visually ambiguous task.

## Current icon coverage
- `counting`
  - `task_icons_counting_type`
  - `task_icons_counting_color`
  - `task_icons_counting_orientation`
  - `task_icons_counting_size_relation`
  - `task_icons_counting_attribute_binding`
  - `task_icons_counting_singleton_type`
- `relation`
  - `task_icons_relation_relative_position_type`
  - `task_icons_relation_between_two_anchors_count`
  - `task_icons_relation_occlusion_order`
  - `task_icons_relation_mirror_symmetry`
- `pattern`
  - `task_icons_pattern_grid_rotation_violation`
  - `task_icons_pattern_grid_size_violation`
- `transformation`
  - `task_icons_transformation_pair_count`
- `sequence`
  - `task_icons_sequence_missing_count`
  - `task_icons_sequence_rotation_violation`

## Layout and evidence heuristics
- Free-placed scene-icon tasks usually want:
  - `Reference` + `Scene` or single-panel scene,
  - answer = `integer`,
  - evidence = `bbox_set`.
- Grid/cell tasks usually want:
  - `Reference` cell + labeled Scene cells,
  - answer = `integer`,
  - evidence = `label_set`.
- Remove the reference panel if it does not change the semantic predicate.
- Keep evidence scoped to the semantic unit:
  - icon instances -> `bbox_set`
  - cells/pairs -> `label_set`
  - missing slot -> one-box `bbox_set`

## Learned task-design rules
- Use per-icon subtle noise before compositing; record those edits in trace.
- Prefer explicit target/distractor sampling over hoping random rendering realizes the count.
- For anchored relation tasks, mix distractor types so the task cannot be solved by occupancy alone.
- For size-relation tasks, record nominal sizes and enforce a minimum size gap.
- For mirror-symmetry tasks:
  - use square Reference/Scene cells,
  - use even icon counts in all cells,
  - treat each symmetry type as an exact rendered-image signature,
  - reject accidental extra-axis symmetries.
- For row/cell sequence tasks, derive the canvas from sampled cell geometry rather than stretching cells into one fixed canvas.
- For rotation-bearing icon sequence tasks, use `non_symmetry.txt`, label visible cells directly in the row, and keep user-facing evidence on the violating/missing cell bbox rather than adding a separate option strip.
- For 2D icon pattern-violation tasks, keep the semantic target on the violating cell bbox, use one numbered grid rather than an option strip, and reject any instance where another supported rule hypothesis would make a different violating cell plausible.
- For 2D icon size-pattern tasks, define the rule over symbolic size levels first and only map those levels to pixel sizes after sampled cell geometry is known; this keeps ambiguity checks independent of the final rendered cell size.
- For scene-internal icon frequency tasks, define grouping over `icon_id` only and let color/rotation vary independently; otherwise the task collapses into appearance matching instead of true type-frequency reasoning.

## Shared helpers to prefer
- `trace/tasks/icons/shared/icon_assets.py`
- `trace/tasks/icons/shared/icon_scene.py`
- `trace/tasks/icons/shared/icon_task_rendering.py`
- `trace/tasks/icons/shared/icon_style.py`
- `trace/tasks/icons/shared/icon_transform.py`
- `trace/tasks/icons/shared/icon_grid_scene.py`
- `trace/tasks/icons/shared/icon_sequence_scene.py`
- `trace/tasks/icons/shared/icon_single_panel_labeled_grid_scene.py`
- `trace/tasks/icons/shared/icon_pair_grid_scene.py`
- `trace/tasks/icons/shared/icon_overlap_grid_scene.py`
- `trace/tasks/icons/shared/icon_labeled_grid_scene.py`
- `trace/tasks/icons/shared/anchor_marking.py`

## Pair with
- `skills/task-design/SKILL.md`
- `skills/task-complexity/SKILL.md`
- `skills/task-implementation/SKILL.md`
- `skills/verification-review/SKILL.md`

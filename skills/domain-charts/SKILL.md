---
name: domain-charts
description: Use when designing, implementing, or reviewing TRACE chart-domain tasks, especially for scene_variant usage, chart-family fit, evidence contracts, and chart-specific readability/balancing rules.
---

# Charts Domain

Use this whenever the task lives under `domain=charts`.

## Read first
1. `docs/domains/CHART_DOMAIN_PLAN.md`
2. `docs/domains/CHART_TASK_SETUP.md`
3. `docs/project/STATUS.md`
4. `docs/workflows/TASK_AUTHORING.md`
5. `docs/workflows/SHARED_UTILITIES.md`

## Chart-domain rules
- Keep `task_group` aligned to reasoning family, not chart type.
- Keep `task_variant` for the semantic/query axis and `scene_variant` for the chart-type axis.
- One chart per image is still the default unless a task is explicitly multiseries or distribution-specific.
- Do not force every chart type onto every task. Add scene support only where the task semantics still make sense.
- Single-series chart helpers belong under `trace/tasks/charts/shared/labeled_chart_common.py`.
- Multiseries chart helpers belong under `trace/tasks/charts/shared/multiseries_chart_common.py`.
- Distribution-family chart helpers belong under `trace/tasks/charts/shared/distribution_chart_common.py`.
- Composition-family chart helpers belong under `trace/tasks/charts/shared/composition_chart_common.py`.

## Evidence rules
- Keep the prompt-facing evidence contract chart-native and simple.
- Use `label_set` when the witness is a set of labels or categories.
- Use `integer_list` only when evidence is an ordered numeric readout and the order is defined by prompt query order.
- If prompt-facing evidence is symbolic rather than geometric, still emit matching pixel-space witness projections so review overlays can highlight the supporting marks.
- For chart tasks with label answers, prefer the smallest supporting evidence that still grounds the answer cleanly.

## Design heuristics
- Treat `scene_variant` as a first-class chart axis. Chart-type variety should usually expand inside a task, not by creating near-duplicate tasks.
- Keep chart tasks compact at the task level and push sub-question diversity into `task_variant`.
- If a chart type changes the structural semantics, split the shared helper path instead of overloading the first helper module with branching logic.
- Use target-first or compatibility-aware internal sampling when chart/task combinations have uneven answer support.
- Favor explicit visible labels and printed values over requiring pixel-only estimation from geometry.
- For chart complexity, keep the criterion vocabulary broad (`visual_scan`, `reasoning_load`, `scene_variant_load` works well), but keep `scene_variant_load` task-local rather than reusing one global chart-type difficulty table.

## Chart-type lessons learned
- `pie` and `donut` are composition-style scenes, not generic drop-ins for every chart task.
- For `pie` and `donut`, use positive integer percentages summing to `100`, distinct slice colors, and a right-side legend with strong framed swatches.
- Legend text for pie/donut/stacked scenes should sit clearly to the right of the swatch, not centered over it.
- `histogram` only counts as a real separate chart type when it uses ordered numeric-bin semantics with touching bars. Do not treat it as a spaced categorical bar alias.
- `radar` should only be enabled on tasks whose semantics still make sense on a cyclic spoke layout, and it needs a tighter label-count cap.
- Stacked composition scenes should print segment values directly and avoid redundant numeric axis labels when they create clutter.

## Family-specific guidance
- `statistics`: use where the question asks for a numeric summary value or winning label derived from displayed values.
- `counting`: use for threshold/interval counts over labeled marks or categories.
- `readout`: use for direct arithmetic over queried labels with ordered numeric evidence.
- `multiseries`: use when the reasoning depends on comparing named series within shared categories.
- `distribution`: use when the chart semantics are bins, quartiles, whiskers, modes, or density shape, not ordinary point/bar values.
- `composition`: use when the chart semantics are parts of a whole or stack segments.
- `trend`: use when the chart is treated as an ordered sequence and the task depends on peaks, troughs, or monotone runs.

## Readability rules
- Tighten effective mark-count caps for visually dense chart types instead of pretending one global cap works for all chart scenes.
- Increase canvas size or spacing before reducing semantic complexity when legends, labels, or groups become unreadable.
- For multiseries grouped charts, leave enough whitespace between category groups so pairwise comparisons are visually obvious.
- Prefer visible point markers on `line` and `area` scenes whenever tasks reason about discrete labeled points.

## Coverage reference
For current chart coverage and active task families, use:
- `docs/project/STATUS.md`
- `docs/domains/TASK_FAMILY_VARIANTS.md`

## Pair with
- `skills/task-design/SKILL.md`
- `skills/task-complexity/SKILL.md`
- `skills/task-implementation/SKILL.md`
- `skills/verification-review/SKILL.md`

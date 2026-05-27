---
name: domain-charts
description: Use when designing, implementing, or reviewing TRACE chart-domain tasks, especially for scene_variant usage, chart-family fit, evidence contracts, and chart-specific readability/balancing rules.
---

# Charts Domain

Use this whenever the task lives under `domain=charts`.

## Read first
1. `docs/domains/CHART_TASK_SETUP.md`
2. `docs/ACTIVE_TASK_INVENTORY.md` for the generated active scene/task list.
3. `docs/domains/CHART_DOMAIN_PLAN.md` only when working on future chart-type expansion
4. `docs/project/STATUS.md`
5. `docs/workflows/TASK_AUTHORING.md`
6. `docs/workflows/SHARED_UTILITIES.md`

## Active-contract reminders
- Keep `task_group` aligned to reasoning family, not chart type.
- Put the semantic branch in `query_id`; use `scene_variant` for chart-type or rendering axes.
- One chart per image is still the default unless a family is explicitly multiseries or distribution-specific.
- Do not force every chart type onto every task; add scene support only where the task semantics still make sense.
- Treat `table` as a chart scene for table-like data displays.
- `docs/domains/CHART_TASK_SETUP.md` owns the active chart contract. If it differs from the long-term plan doc, the setup doc wins.

## Helper placement
- Single-series chart helpers belong under `trace/tasks/charts/shared/labeled_chart_common.py`.
- Multiseries chart helpers belong under `trace/tasks/charts/shared/multiseries_chart_common.py`.
- Distribution-family chart helpers belong under `trace/tasks/charts/shared/distribution_chart_common.py`.

## Practical review checklist
- Keep the prompt-facing evidence contract chart-native and simple; follow the active evidence rules in `docs/domains/CHART_TASK_SETUP.md`.
- Prefer widening `scene_variant` support inside a task before creating a near-duplicate task id.
- If a chart type changes the underlying scene grammar, split the shared helper path before widening the task surface.
- Favor explicit visible labels and printed values over geometry-only estimation.
- For `table`, keep row, column, cell, year, filter, rank, and interval references explicit enough that supporting bbox evidence is unambiguous.
- For `table`, prefer readable tables over schema complexity: short labels, moderate row/column counts, and style variation through borders, shading, and framing.
- Tighten mark-count/readability limits before shrinking semantic variety.

## Coverage reference
For current chart coverage and active task families, use:
- `docs/project/STATUS.md`
- `docs/domains/SCENE_TASK_QUERY_GUIDE.md`

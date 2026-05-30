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
7. `review/docs/CALIBRATION_GUIDE.md` and `docs/workflows/TASK_REVIEW_WEB_APP.md`
   before any scene review or solve-rate work
8. `docs/workflows/INFORMATION_SCENE_RENDERING_UPGRADE.md` before renderer/style changes
9. `docs/workflows/SHARED_FONT_ASSETS.md` before touching text rendering
10. `docs/workflows/SHARED_CONTEXT_TEXT_ASSETS.md` before adding distractor/context text

## Active-contract reminders
- Keep `task_group` aligned to reasoning family, not chart type.
- Put the semantic branch in `query_id`; use `scene_variant` for chart-type or rendering axes.
- One chart per image is still the default unless a family is explicitly multiseries or distribution-specific.
- Do not force every chart type onto every task; add scene support only where the task semantics still make sense.
- Treat `table` as a chart scene for table-like data displays.
- `docs/domains/CHART_TASK_SETUP.md` owns the active chart contract. If it differs from the long-term plan doc, the setup doc wins.
- Style, font, context, jitter, and renderer-variant choices are non-semantic axes. Record them in `render_spec`; never let them depend on answer value, correct option, query id, or difficulty bucket.
- Chart scene visual audits are reviewer-gated. Report proposed visual changes first, then implement only explicitly approved edits.

## Helper placement
- Single-series chart helpers belong under `trace/tasks/charts/shared/labeled_chart_common.py`.
- Multiseries chart helpers belong under `trace/tasks/charts/shared/multiseries_chart_common.py`.
- Distribution-family chart helpers belong under `trace/tasks/charts/shared/distribution_chart_common.py`.

## Practical review checklist
- Use `docs/domains/CHART_TASK_SETUP.md` for active chart contracts, scene/query fit, evidence expectations, and table-specific rules.
- Use `docs/workflows/INFORMATION_SCENE_RENDERING_UPGRADE.md` for chart visual audits, style/background/palette/context rules, and scene-review handoff.
- Use `docs/workflows/SHARED_FONT_ASSETS.md` and `docs/workflows/SHARED_CONTEXT_TEXT_ASSETS.md` for text/font/context implementation details.

## Scene visual audit handoff
- Follow `docs/workflows/INFORMATION_SCENE_RENDERING_UPGRADE.md` and `review/docs/CALIBRATION_GUIDE.md`.
- Use the browser review app as the default inspection surface; Excel exports are optional static artifacts.

## Coverage reference
For current chart coverage and active task families, use:
- `docs/project/STATUS.md`
- `docs/domains/SCENE_TASK_QUERY_GUIDE.md`

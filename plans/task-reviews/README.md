# Planned Task Reviews

This folder mirrors the domain-scoped layout of `task-reviews/`, but it is used
for calibration-stage review artifacts tied to exact probe sets under `plans/`.

Layout:

- `plans/task-reviews/<domain>/<task_id>/`

Typical contents for one task:

- one workbook for the exact probe set, for example `..._level0_200.xlsx`
- `manifest.json` pointing back to the source parquet and dataset root
- `images/` and `data/` sidecars for the workbook rows

These artifacts are for task-difficulty calibration and should not replace the
canonical task-review workflow outputs under `task-reviews/`.

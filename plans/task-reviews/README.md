# Planned Task Reviews

This folder mirrors the domain-scoped layout of `task-reviews/`, but it is used
for calibration-stage review artifacts tied to exact probe sets under `plans/`.

Layout:

- `plans/task-reviews/<domain>/<task_id>/`

Typical contents for one task:

- one workbook for each exact calibration probe version, for example `<task_id>_v0.xlsx`
- `manifest.json` pointing back to the source parquet and dataset root
- `images/` and `data/` sidecars for the workbook rows

Version labels:

- `v0`: starting/current config before manual calibration changes
- `v1`, `v2`, ...: later manually tuned config versions

Every generated `100`-sample calibration parquet should have a matching workbook
saved here before model evaluation.

These artifacts are for task-difficulty calibration and should not replace the
canonical task-review workflow outputs under `task-reviews/`.

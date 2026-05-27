# Active Task Reviews

This is the live manual-review artifact root for the current default-enabled
TRACE task surface. It is used for calibration-stage review workbooks tied to
exact active task ids.

Layout:

- `plans/task-reviews/<public_domain>/<scene_id>/<task_id>/`
- `plans/task-reviews/<public_domain>/<scene_id>/scene_review.xlsx`
- `plans/task-reviews/<public_domain>/<scene_id>/scene_review_manifest.json`

Typical contents for one task:

- current inspection workbook, `<task_id>.xlsx`
- `manifest.json` pointing back to the source parquet and dataset root
- `random_review_100.json` and `distribution_review.json` when generated
- `images/` and `data/` sidecars for the workbook rows

Calibration baseline:

- The current active baseline is `v0`, as defined in
  `plans/CALIBRATION_PLAN.md`.
- Review manifests and solve-rate stats used for current acceptance must carry
  `calibration_baseline: "v0"`.
- Non-current extra workbooks and solve-rate files should be removed from this
  live review tree before fresh calibration artifacts are generated.
- The canonical inspection workbook remains `<task_id>.xlsx`.

Every active task should have a current workbook here before model evaluation.
Every generated `100`-sample calibration parquet should also have a matching
workbook saved here before solve-rate probing.

Scene-level workbooks combine all current task review rows for one scene into a
single Excel file with one sheet per task. `scripts/run_task_review.py` refreshes
the touched scene workbooks automatically after `--mode full` or
`--mode inspection`. To rebuild scene workbooks from existing task sidecars:

```bash
PYTHONPATH=. python scripts/build_scene_task_review_workbooks.py --out-root plans/task-reviews
```

These artifacts are the active manual calibration reviews. The root-level
`task-reviews/` artifact tree is not used as the active audit source.

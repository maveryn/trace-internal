# Task Reviews

Review artifacts live under `task-reviews/<domain>/<task_id>/`.

Each reviewed task directory may contain:
- `random_review_100.json`
- `distribution_review.json`
- `<task_id>.xlsx`

Use the standardized workflow from `docs/workflows/TASK_AUTHORING.md`:

```bash
PYTHONPATH=. python scripts/run_task_review.py --tasks <task_id> --mode full
```

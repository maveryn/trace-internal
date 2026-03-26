# Task Reviews

`task-reviews/` stores repeatable per-task validation runs and human-review artifacts.

## Standard review workflow
For each task, run these steps in order:
1. Generate **100 random samples** and report task-variant distribution (skip variant distribution if the task has no variants).
2. Generate **100 samples per task variant** and report answer-distribution checks plus any discovered sampling-axis distributions.
3. Generate **25 samples per task variant** for manual review in one Excel workbook per task.

When a task has no variants, distribution review uses a single 100-sample run.

Hard distribution gates:
- `unique_answers >= 5`
- `max_answer_frequency < 25%`

Numeric reviews also include a 5-bin summary (`five_bin_numeric`, `max_five_bin_frequency`) for inspection, but that bin summary is informational unless a task family defines a stricter rule.

## Review statuses
Use `task-reviews/REVIEW_STATUS.md` to track each task as:
- `alright_for_now`
- `needs_update`

## Commands
Run full review:
```bash
PYTHONPATH=. python scripts/run_task_review.py --tasks <task_id> --mode full
```

Run distribution-only review:
```bash
PYTHONPATH=. python scripts/run_task_review.py --tasks <task_id> --mode distribution
```

Run inspection-only review (skip distribution analysis):
```bash
PYTHONPATH=. python scripts/run_task_review.py --tasks <task_id> --mode inspection
```

## Output layout
Each task review writes under `task-reviews/<task_id>/`:
- `random_review_100.json`
- `distribution_review.json`
- `<task_id>.xlsx` (one sheet per task variant)
- `manifest.json` (`workbook_sheets` maps variant -> sheet name)
- `images/<variant>/...`
- `data/<variant>/...`

Summary report:
- `task-reviews/review_summary.json`

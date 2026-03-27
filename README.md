# TRACE

TRACE is a grounded visual reasoning task environment for RLVR.

## Docs

Start with [docs/README.md](docs/README.md).  
Current implementation snapshot is in [docs/project/STATUS.md](docs/project/STATUS.md).
Contribution workflow/checklists are in [CONTRIBUTING.md](CONTRIBUTING.md).

## Skills

Repo-local workflow/domain skills live under `skills/`. They are thin execution guides layered on top of the canonical docs in `docs/`.

## Setup

```bash
pip install -r requirements.txt
```

## Build Dataset

```bash
PYTHONPATH=. python scripts/build_dataset.py --config configs/examples/minimal_build.yaml
```

## Task Reviews

Use task-review workflow outputs under `task-reviews/`.

```bash
PYTHONPATH=. python scripts/run_task_review.py --tasks task_geometry_measurement_angle --mode full
```

This writes:
- `task-reviews/<task_id>/random_review_100.json`
- `task-reviews/<task_id>/distribution_review.json`
- `task-reviews/<task_id>/<task_id>.xlsx` (one sheet per task variant)
- `task-reviews/<task_id>/manifest.json`
- `task-reviews/review_summary.json`

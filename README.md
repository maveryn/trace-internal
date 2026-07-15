# Trace

Trace is a grounded visual reasoning task environment for RLVR.

## Docs

Start with [docs/README.md](docs/README.md).  
Current active task inventory is in [docs/ACTIVE_TASK_INVENTORY.md](docs/ACTIVE_TASK_INVENTORY.md).
Contribution workflow/checklists are in [CONTRIBUTING.md](CONTRIBUTING.md).

## Skills

Repo-local workflow skills live under `skills/`. They are thin execution
guides layered on top of the canonical docs in `docs/`.

## Setup

```bash
pip install -r requirements.txt
```

For an editable package install with review-app and test tooling:

```bash
pip install -e ".[test,review]"
```

## Build Dataset

```bash
PYTHONPATH=. python scripts/build_dataset.py --config configs/examples/minimal_build.yaml
```

## Task Reviews

Use task-review workflow outputs under `review/task-reviews/` and inspect them
with the browser review app.

```bash
PYTHONPATH=. python scripts/run_task_review.py --tasks task_geometry__graph_paper__angle_value --mode full --out-root review/task-reviews
PYTHONPATH=. python scripts/run_review_app.py --host 127.0.0.1 --port 7860
```

The review-app launcher defaults browser-facing links to `/proxy/{port}` so
Jupyter Server Proxy URLs keep CSS, JavaScript, media, and form actions working
after restarts.

The required current artifacts are the JSON sidecars, images, manifests, and
distribution reports under:

- `review/task-reviews/<domain>/<scene_id>/<task_id>/`
- `review/task-reviews/<domain>/<scene_id>/scene_review_manifest.json`

Excel workbooks may still be emitted for archival/download use, but browser
inspection and saved sample feedback are the normal review path. See
`docs/workflows/TASK_REVIEW_WEB_APP.md`.

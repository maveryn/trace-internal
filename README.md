# TRACE

TRACE is a grounded visual reasoning task environment for RLVR.

## Docs

Start with [docs/README.md](docs/README.md).  
Current implementation snapshot is in [docs/STATUS.md](docs/STATUS.md).
Contribution workflow/checklists are in [CONTRIBUTING.md](CONTRIBUTING.md).

## Setup

```bash
pip install -r requirements.txt
```

## Build Dataset

```bash
PYTHONPATH=. python scripts/build_dataset.py --config configs/examples/minimal_build.yaml
```

## Generate Task Samples

Use the sample generator to export review artifacts for tasks under `samples/`.
Treat this folder as the persistent verification store during task development.

```bash
PYTHONPATH=. python scripts/generate_task_samples.py --tasks tile_shortest_path --clean
```

Default behavior:
- generates `50` samples per task,
- writes image artifacts under `samples/<domain>/<task_group>/<task>/images/`,
- writes per-sample JSON data under `samples/<domain>/<task_group>/<task>/data/`,
- writes per-task summary files (`summary.json`),
- writes a combined Excel file at `samples/combined_samples.xlsx`.

Useful options:
- `--tasks geometry_angle_value_query,tile_shortest_path`
- `--count 50`
- `--seed 123`
- `--params '{"canvas_size":640}'`
- `--task-params '{"geometry_angle_value_query":{"candidate_count":9}}'`
- `--clean` (safe mode: only allowed with `--tasks`; removes those task folders before regeneration)
- `--clean-all` (explicit full wipe of `samples/`, use sparingly)

## Sample Regeneration Policy

Whenever a task is newly implemented or a change affects task logic or visualization,
rerun `scripts/generate_task_samples.py` for that task to refresh the review artifacts.

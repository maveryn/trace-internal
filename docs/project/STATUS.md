# TRACE Status

Date: 2026-06-07

## Active Inventory
The generated source of truth for active public domains, scenes, and tasks is
`docs/ACTIVE_TASK_INVENTORY.md`.

Do not duplicate exhaustive task or scene inventories in this file. Regenerate
the inventory with:

```bash
PYTHONPATH=. python scripts/generate_active_task_inventory.py
```

Current generated summary:

| Metric | Value |
| --- | ---: |
| Default tasks | 968 |
| Registered tasks | 968 |
| Public domains | 11 |
| Public scenes | 291 |
| Missing taxonomy mappings | 0 |
| Invalid default task id shapes | 0 |

Current generated domain counts:

| Domain | Scenes | Tasks |
| --- | ---: | ---: |
| charts | 44 | 188 |
| games | 50 | 161 |
| geometry | 46 | 192 |
| graph | 10 | 61 |
| icons | 18 | 40 |
| illustrations | 11 | 26 |
| misc | 14 | 42 |
| pages | 28 | 92 |
| physics | 36 | 53 |
| puzzles | 28 | 80 |
| three_d | 6 | 33 |

## Active Contracts
1. Public taxonomy is `domain -> scene_id -> task_id`.
2. `task_id` is the default sampling unit.
3. `query_id` records task-internal semantic branches.
4. Branch identity is recorded in `query_id`; `query_id` is internal replay metadata.
5. Table-style data-display tasks are public `charts` tasks under scene `table`.
6. Structured forms, diagrams, controls, schedules, timelines, and page-like layouts are represented under `pages`.
7. Cell-board tasks are public `puzzles` tasks under scene `cell_board`.
8. Image-reconstruction/jigsaw-style tasks belong under `illustrations`.
9. Synthetic perspective 3D tasks belong under `three_d`.

## Validation
Use these checks after task, taxonomy, or docs inventory changes:

```bash
PYTHONPATH=. python scripts/generate_active_task_inventory.py --check
PYTHONPATH=. python scripts/audit_active_domain_surfaces.py
PYTHONPATH=. python scripts/check_active_inventory_integrity.py --include-local-cache
PYTHONPATH=. python scripts/check_skill_consistency.py
PYTHONPATH=. python scripts/audit_active_tasks.py --skip-smoke
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_docs_consistency.py
git diff --check -- docs skills scripts tests trace configs prompts review assets AGENTS.md README.md
```

The active registry currently has no blocking taxonomy/domain-surface issues.
Calibration and task-review artifact coverage gaps are tracked by
`scripts/audit_active_tasks.py`.

## Maintenance Rule
Keep this file as a compact status pointer. If a change needs a full active
task list, update the task registry/taxonomy and regenerate
`docs/ACTIVE_TASK_INVENTORY.md` instead of editing task lists by hand.

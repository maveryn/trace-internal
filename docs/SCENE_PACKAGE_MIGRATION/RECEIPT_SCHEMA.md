# Migration Receipt Schema

Receipts are written only after the human reviewer accepts the scene in the
browser review app.

Receipts do not make a scene review-ready. They record acceptance after source
review, tests, task-review artifacts, and app review have already passed.

## Path

```text
review/task-reviews/<domain>/<scene_id>/migration_receipt.json
```

## Required Fields

```json
{
  "domain": "games",
  "scene_id": "2048",
  "task_ids": [
    "task_games__2048__max_tile_value"
  ],
  "public_task_files": [
    "trace/tasks/games/2048/max_tile_value.py"
  ],
  "shared_files": [
    "trace/tasks/games/2048/shared/state.py"
  ],
  "config_files": [
    "configs/domains/games/2048.yaml"
  ],
  "prompt_files": [
    "prompts/games/2048.json"
  ],
  "validation_commands": [
    "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_scene_package_migration_contracts.py"
  ],
  "notes": "Accepted in review app after source audit and regenerated artifacts."
}
```

All paths are repo-relative.

## Before Writing A Receipt

Confirm:

- the reviewer accepted the scene in the app
- every active task id is listed
- retired task ids and stale review folders are gone
- public task files own answer and annotation contracts
- shared code is identity-free
- prompt prose is externalized
- config has no query/task routing in shared sections
- taxonomy review status exists and passed
- manual code audit status exists and passed
- migration test status exists and passed
- fresh task-review artifacts exist under `review/task-reviews`
- the reviewer checked the task-level taxonomy review gate for every active task
- open reviewer issues for the scene are fixed and re-reviewed

If any item is false, do not write the receipt.

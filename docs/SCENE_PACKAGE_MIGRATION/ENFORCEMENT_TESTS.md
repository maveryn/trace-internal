# Scene-Package Enforcement Tests

The migration tests live in:

```text
tests/test_scene_package_migration_contracts.py
tests/test_scene_package_review_candidate_contracts.py
```

They apply to scenes listed in `SCENE_PACKAGE_REVIEW_CANDIDATE_SCENES`.
For scene handoff, scope them to the assigned scene with
`TRACE_SCENE_PACKAGE_REVIEW_SCENE=<domain>/<scene_id>`.

## Purpose

The tests catch known migration shortcuts. They are not a completion signal.
Passing means the scene cleared automated guardrails. Failing means the scene is
not review-ready.

The fix for a failure is source redesign, not test editing.

## Gates

Review-candidate scenes are checked for:

- one public Python file per active public task id
- no sibling public-task imports
- no wrapper-only task files
- no shared `generate()` pipelines
- no scene-shared `TaskOutput` construction for public tasks
- no task/query/objective identity routing inside `shared/`
- no public query-id constants or routing tables inside `shared/`
- no task-named shared runtime files
- no copy-split duplicate code
- no query routing or public task routing in shared config
- no repo-wide scalar difficulty helper files or domain-local
  `fixed_query_task.py` adapters
- no migrated games-scene imports of legacy `resolve_games_query_id`
- large functions documented with a concise role/invariant note
- enrolled review-candidate scenes use Black-style 88-character source lines
- smoke coverage for every public task and supported local query branch

Approved private lifecycle files are allowed only for neutral scene plumbing.
They must not register tasks or route objective behavior by public identity.

The source-formatting gate is intentionally enrolled scene by scene during the
rollout. `puzzles/arithmetic_panel` is the first enforced scene. Add more scenes
only after their source has been formatted; the long-term target is every
migrated/review-candidate scene.

## Required Command

Before task-review generation for one migrated scene, run the scene-scoped
gate:

```bash
TRACE_SCENE_PACKAGE_REVIEW_SCENE=<domain>/<scene_id> \
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q \
  tests/test_review_app.py \
  tests/test_run_task_review.py \
  tests/test_scene_package_migration_contracts.py \
  tests/test_scene_package_review_candidate_contracts.py
```

Run scene-specific tests as needed.

After that command passes, record:

```text
review/task-reviews/<domain>/<scene_id>/migration_test_status.json
```

The status must have `passed: true` and list at least these test files:

- `tests/test_review_app.py`
- `tests/test_run_task_review.py`
- `tests/test_scene_package_migration_contracts.py`
- `tests/test_scene_package_review_candidate_contracts.py`

`scripts/run_task_review.py --out-root review/task-reviews` refuses artifacts
for registered review-candidate scenes unless these scene-level files all
exist and pass:

- `manual_code_audit_status.json`
- `taxonomy_review_status.json`
- `migration_test_status.json`

The taxonomy status must include the requested task ids, and each listed task
must have a concrete `## Program Contract` in
`docs/tasks/<domain>/<scene_id>/<task_id>.md`.
It must also include `checklist.scalar_annotation_checked: true`; stale
taxonomy status files from before scalar annotation review are not enough.

Do not block one scene's review artifacts on unrelated review-candidate scenes.
Unscoped migration tests are for later global audit, not per-scene handoff.
The task registry and review runner must preserve this boundary: with
`TRACE_SCENE_PACKAGE_REVIEW_SCENE` set, migration gates should import only that
scene's public task modules. Registry-wide operations such as full inventory
builds and all-task review generation may still import every task and fail on
unrelated broken scenes.

Global runtime-record ABI checks live separately in:

```text
tests/test_scene_package_global_runtime_contracts.py
```

Those checks are not part of the per-scene handoff gate. They should be run and
fixed during global migration cleanup, not used to block review artifacts for a
single scene that passed its scoped migration checks.

## Do Not

Do not fix failures by:

- deleting or weakening tests
- editing policy/registry files during scene work
- moving a dispatcher to a different shared file
- hiding public ids behind renamed strings
- adding wrapper task files
- copying the same task body into multiple files
- forging manual audit or migration status JSON
- generating review artifacts for a scene that fails gates

If a test blocks a legitimate design, stop and ask for a contract decision.

# TRACE New Task Quickstart

This is the shortest safe path for adding a task.

## 1) Create and register the task
1. Add `trace/tasks/<domain>/<task_group>/<task_name>.py`.
2. Register with `@register_task`.
3. Import task module in `trace/tasks/__init__.py` so it is registered at runtime.

## 2) Use shared contracts (no hardcoded prompt text)
1. Return `TaskOutput` with typed `answer_gt` + typed `evidence_gt`.
2. Build prompt via shared prompt renderer (`trace/core/prompts/*` or task helper wrappers).
3. Store active prompt in `prompt` and both modes in `prompt_variants`:
   - `answer_only`
   - `answer_and_evidence`
4. Emit trace payload with:
   - `scene_ir`
   - `query_spec` (including prompt metadata)
   - `render_spec`
   - `render_map`
   - `execution_trace`
   - `witness_symbolic`
   - `projected_evidence`

## 3) Configure defaults
1. Domain defaults (optional): `configs/domains/<domain>.yaml`
2. Task-group defaults: `configs/task_groups/<domain>/<task_group>.yaml`
3. Keep precedence: `domain -> task_group -> task/params`

## 4) Add prompt bundle
1. Add `prompts/<domain>/<task_group>/<bundle_id>.json`
2. Include:
   - `task_type_templates` (at least 10 variants)
   - `query_type_templates` (at least 10 variants per key)
   - `answer_or_evidence_templates` (at least 10 variants per mode)
   - `required_slots_by_key`

## 5) Add tests
Minimum checks:
1. deterministic generation for fixed seed,
2. answer/evidence consistency with execution trace,
3. prompt metadata presence/consistency,
4. build integration smoke.

Run:
```bash
PYTHONPATH=. pytest -q
```

## 6) Add task doc
1. Copy `docs/tasks/TASK_DOC_TEMPLATE.md` to `docs/tasks/<task_id>.md`
2. Fill prompt bundle keys, slot schema, constraints, complexity, and tests.

## 7) Generate review samples
```bash
PYTHONPATH=. python scripts/generate_task_samples.py --tasks <task_id> --count 50 --clean
```

For new/distribution-changing tasks:
```bash
PYTHONPATH=. python scripts/generate_task_samples.py --tasks <task_id> --count-per-query 100 --clean
```
Review `distribution_report.json` and resolve obvious skew before sign-off.

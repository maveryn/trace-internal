# TRACE Task Authoring Guide

Use this as the implementation checklist for new or modified tasks.

## 1) Before coding
1. Confirm taxonomy: `domain`, `task_group`, `task_id`.
2. Task-id format is required: `task_<domain>_<task_group>_<task_name>` (lowercase snake_case).
3. Task module filename is required: `<task_name>.py` under `trace/tasks/<domain>/<task_group>/`.
4. Confirm family/variant fit using `docs/TASK_FAMILY_VARIANTS.md` before introducing a new task group.
5. Define task contracts:
   - scene,
   - query types,
   - answer type,
   - evidence type(s),
   - constraints/rejection policy.
6. Check shared helpers first:
   - `trace/core`
   - `trace/tasks/shared`
   - `trace/tasks/<domain>/shared`
   - existing task-group shared modules (for example `trace/tasks/<domain>/<task_group>/*_base.py`)
7. Keep helper placement at the narrowest reusable layer.

## 2) Required implementation behavior
1. Add the task module at `trace/tasks/<domain>/<task_group>/<task_name>.py`.
2. Register task with `@register_task`.
3. Import the task module in `trace/tasks/__init__.py` so registration executes at runtime.
4. Keep prompt text in external bundles only.
5. Emit `TaskOutput` with:
   - typed `answer_gt`,
   - typed `evidence_gt`,
   - `trace_payload`,
   - `task_versions`,
   - active `prompt`,
   - `prompt_variants` (both modes when supported).
6. Keep `trace_payload` complete with:
   - `scene_ir`,
   - `query_spec` (with prompt metadata),
   - `render_spec`,
   - `render_map`,
   - `execution_trace`,
   - `witness_symbolic`,
   - `projected_evidence`.
7. Ensure answer/evidence/witness come from the same execution trace.
8. Enforce unique final answer by construction.
9. Use bounded resampling; never auto-relax semantic constraints.
10. Emit complexity (`complexity_score`, `complexity_components`).

## 3) Prompt rules
1. Bundle path: `prompts/<domain>/<task_group>/<bundle>.json`.
2. Required template layers:
   - task type,
   - query type,
   - output mode (`answer_only`, `answer_and_evidence`).
3. Deterministic variant selection only.
4. Record prompt metadata in trace payload.
5. Keep variant cardinality at least 10 per required template list.
6. If a prompt slot value is static for a task (for example a fixed question stem), store it in prompt config/template data rather than task-module constants.

## 4) Config/defaults rules
1. Precedence: `domain -> task_group -> task/params`.
2. Use shared defaults helpers; avoid local parsing duplicates.
3. In task-group files, separate shared keys (`shared`) from task-specific keys (`task_overrides.<task_id>`) for `generation`/`rendering`/`prompt`/`sampling`; default to `shared` and use `task_overrides` only for task-specific deltas (legacy flat section keys are unsupported).
4. Keep broadly shared domain visual policy in `configs/domains/<domain>/base.yaml`; use task-group visual only for group-specific overrides.
5. Query-weight fallback is: build task `query_weights` -> task-group `sampling.task_overrides` -> task-group `sampling.shared` -> uniform.
6. Visual defaults/noise should route through shared visual modules.
7. Geometry measurement tasks should keep graph-paper/anchor alignment policy consistent.
8. For sibling variants of one objective family (for example area/perimeter), keep shared generation/prompt/trace flow in one task-group shared base helper and keep task modules thin.
9. Required prompt/config slots should be enforced with fail-fast shared helpers (no hardcoded fallback prompt literals in task code).
10. If the same fallback constants are used by multiple sibling tasks, move them to a task-group shared defaults module.

## 5) Sampling rules
1. Global sampling unit is `task`.
2. Query sampling occurs inside each task.
3. Default `P(query|task)` is uniform unless overridden.
4. For each query type, sample feasible answers near-uniform unless curriculum explicitly overrides.
5. For geometry placement with lattice offsets, compute anchor bounds from the selected candidate (not global worst-case margins).
6. Avoid tiny fixed structure banks; randomize both structural and visual factors whenever constraints allow.
7. For tasks with both source categories and answer targets, sample both distributions explicitly and verify realized distributions.
8. For deterministic balance over generated prefixes, use builder `_sampling_index` (not hashed `instance_seed`) when cycling categories/answers.
9. When changing answer/evidence/query contracts, remove deprecated helper paths and stale trace fields in the same patch.

## 6) Minimal test checklist
1. Determinism for fixed seed.
2. Answer/evidence consistency with execution trace.
3. Prompt metadata and placeholder validity.
4. Build integration smoke.
5. Constraint-specific tests (for example non-overlap, uniqueness).
6. Feasibility sanity at max candidate count under default render ranges (for geometry/layout-heavy tasks).
7. Prefer extending shared family contract tests instead of duplicating full contract checks in every task file.

Run:
```bash
PYTHONPATH=. pytest -q
```

## 7) Required docs updates (same change)
1. `docs/tasks/<task_id>.md`
2. `docs/tasks/README.md` (task links must match active task set)
3. `docs/STATUS.md` (if behavior changed)
4. `docs/SHARED_UTILITIES.md` (if shared helpers moved/added)
5. `docs/BUILD_VALIDATION.md` or `docs/VALIDATION_ERROR_CODES.md` (if validation behavior changed)
6. `docs/CODE_REVIEW_GUIDELINES.md` for reusable findings.

## 8) Reuse anti-patterns
Use `docs/CODE_REVIEW_GUIDELINES.md` Section 2 as the canonical anti-pattern list.

## 9) Sample generation review
For quick visual sanity checks:
```bash
PYTHONPATH=. python scripts/generate_task_samples.py --tasks <task_id> --count 50 --clean
```

For new tasks or distribution-changing changes:
```bash
PYTHONPATH=. python scripts/generate_task_samples.py --tasks <task_id> --count-per-query 100 --clean
```

Review `distribution_report.json` and resolve obvious skew before sign-off.

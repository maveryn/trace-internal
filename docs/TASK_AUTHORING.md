# TRACE Task Authoring Guide

Use this as the implementation checklist for new or modified tasks.

## 1) Before coding
1. Confirm taxonomy: `domain`, `task_group`, `task_id`.
2. Define task contracts:
   - scene,
   - query types,
   - answer type,
   - evidence type(s),
   - constraints/rejection policy.
3. Check shared helpers first:
   - `trace/core`
   - `trace/tasks/shared`
   - `trace/tasks/<domain>/shared`
4. Keep helper placement at the narrowest reusable layer.

## 2) Required implementation behavior
1. Register task with `@register_task`.
2. Keep prompt text in external bundles only.
3. Emit `TaskOutput` with:
   - typed `answer_gt`,
   - typed `evidence_gt`,
   - `trace_payload`,
   - `task_versions`,
   - active `prompt`,
   - `prompt_variants` (both modes when supported).
4. Ensure answer/evidence/witness come from the same execution trace.
5. Enforce unique final answer by construction.
6. Use bounded resampling; never auto-relax semantic constraints.
7. Emit complexity (`complexity_score`, `complexity_components`).

## 3) Prompt rules
1. Bundle path: `prompts/<domain>/<task_group>/<bundle>.json`.
2. Required template layers:
   - task type,
   - query type,
   - output mode (`answer_only`, `answer_and_evidence`).
3. Deterministic variant selection only.
4. Record prompt metadata in trace payload.
5. Keep variant cardinality at least 10 per required template list.

## 4) Config/defaults rules
1. Precedence: `domain -> task_group -> task/params`.
2. Use shared defaults helpers; avoid local parsing duplicates.
3. In task-group files, separate shared keys (`shared`) from task-specific keys (`task_overrides.<task_id>`) for `generation`/`rendering`/`prompt`/`sampling`; default to `shared` and use `task_overrides` only for task-specific deltas (legacy flat section keys are unsupported).
4. Keep broadly shared domain visual policy in `configs/domains/<domain>/base.yaml`; use task-group visual only for group-specific overrides.
5. Query-weight fallback is: build task `query_weights` -> task-group `sampling.task_overrides` -> task-group `sampling.shared` -> uniform.
6. Visual defaults/noise should route through shared visual modules.
7. Geometry measurement tasks should keep graph-paper/anchor alignment policy consistent.

## 5) Sampling rules
1. Global sampling unit is `task`.
2. Query sampling occurs inside each task.
3. Default `P(query|task)` is uniform unless overridden.
4. For each query type, sample final answers near feasible-uniform unless curriculum says otherwise.

## 6) Minimal test checklist
1. Determinism for fixed seed.
2. Answer/evidence consistency with execution trace.
3. Prompt metadata and placeholder validity.
4. Build integration smoke.
5. Constraint-specific tests (for example non-overlap, uniqueness).

Run:
```bash
PYTHONPATH=. pytest -q
```

## 7) Required docs updates (same change)
1. `docs/tasks/<task_id>.md`
2. `docs/STATUS.md` (if behavior changed)
3. `docs/SHARED_UTILITIES.md` (if shared helpers moved/added)
4. `docs/BUILD_VALIDATION.md` or `docs/VALIDATION_ERROR_CODES.md` (if validation behavior changed)
5. `docs/CODE_REVIEW_GUIDELINES.md` and `docs/LESSONS_LEARNED.md` for reusable findings.

## 8) Reuse anti-patterns to avoid
1. Hardcoded prompt strings in task modules.
2. Wrapper modules that only re-export or pass through.
3. Public helper exports with no consumers.
4. Duplicate deterministic utilities across files.
5. Task outputs containing fields unused by build/validation.
6. Leaving helper/type names public after refactors when they are only module-internal.
7. Duplicating local geometric type aliases instead of importing shared canonical aliases.

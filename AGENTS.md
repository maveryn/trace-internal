# TRACE AGENTS

## Project goal
TRACE is a grounded visual reasoning task environment for RLVR.
Each generated instance should include:
- prompt
- typed answer
- image(s)
- metadata-grounded verifier payload

## Source-of-truth docs
- Docs index and reading order: `docs/README.md`
- New-task one-page quickstart: `docs/QUICKSTART_NEW_TASK.md`
- Architecture and ABI contracts: `docs/BLUEPRINT.md`
- Prompt system and template composition: `docs/PROMPT_SYSTEM.md`
- System module/lifecycle architecture: `docs/SYSTEM_ARCHITECTURE.md`
- Current implementation snapshot: `docs/STATUS.md`
- Task creation procedure: `docs/TASK_AUTHORING.md`
- Code documentation guidelines: `docs/CODE_DOCUMENTATION.md`
- Code review guidelines/checklist: `docs/CODE_REVIEW_GUIDELINES.md`
- Shared reusable helpers and anti-duplication policy: `docs/SHARED_UTILITIES.md`
- Build/validation/CI policy: `docs/BUILD_VALIDATION.md`
- Validation error catalog: `docs/VALIDATION_ERROR_CODES.md`
- Reusable pitfalls and fixes: `docs/LESSONS_LEARNED.md`
- Active backlog and priorities: `docs/TODO.md`
- Python dependencies: `requirements.txt`
- Domain/task-group defaults (generation/rendering/visual): `configs/domains/<domain>/base.yaml` and `configs/domains/<domain>/<task_group>.yaml`

## Scope and boundaries
- Work in this repository unless the user explicitly asks otherwise.
- Prefer additive, reusable infrastructure over one-off task code.
- If behavior/contracts change, update the relevant source-of-truth docs above.

## Core engineering rules
- Use taxonomy consistently: `domain -> task_group -> task`.
- Keep `task_group` broad by reasoning style; for geometry value-style tasks use `task_group=measurement` and keep variants in `query_type`.
- Sampling policy is task-level globally (equal task weights by default); domain/task_group probabilities are derived by aggregation, and query sampling happens inside each task (uniform by default unless task-config override).
- Domain/task-group defaults (generation/rendering/visual variation) should follow precedence `domain -> task_group -> task/params`: shared domain defaults under `configs/domains/<domain>/base.yaml`, group overrides under `configs/domains/<domain>/<task_group>.yaml`, then optional task-level overrides.
- Do not hardcode user-facing prompt text in task modules; prompts must come from external template assets.
- Prompt composition must be reusable: one task-type layer and one query-type layer, each with deterministic variant selection.
- Keep prompt templates versioned and recorded in trace metadata (`prompt_bundle_id`, keys, variant indices).
- Keep generation factorized into explicit specs (`SceneSpec`, `QuerySpec`, `RenderSpec`, `PromptSpec`, `VerifierSpec`, `SamplerSpec`, `InstanceRecordSpec`).
- Generators must be deterministic given seeds/specs/versions.
- No hidden randomness: all random sources must be explicit and recorded.
- Verifiers must rely on metadata contracts and projections, not pixels as source of truth.
- Answers and evidence must come from the same execution trace.
- Task instances must have unique final answers by construction.
- Never auto-relax semantic constraints to force acceptance.
- Sidecar trace export is mandatory; each `TrainInstance` must include `trace_ref`.

## Reuse and code organization
- Before adding new logic, search for reusable helpers and extend shared modules when possible.
- Do not duplicate utilities across tasks/domains unless there is a strong reason.
- If a helper is missing, add it once in a shared place and reuse it.
- Follow `docs/SHARED_UTILITIES.md` strictly when deciding helper placement and reuse.
- Before introducing or moving helpers, review `docs/LESSONS_LEARNED.md` for prior placement mistakes (for example task-named modules containing non-task-specific helpers).
- When implementing any task, review existing helpers across layers first (`trace/core`, `trace/tasks/shared`, `trace/tasks/<domain>/shared`, then task-local modules) before writing new logic.
- For every new helper/function, explicitly choose the narrowest reusable layer that fits and place it there:
  - cross-domain infrastructure -> `trace/core` or `trace/tasks/shared`,
  - domain-wide/task-family logic -> `trace/tasks/<domain>/shared`,
  - truly task-specific logic -> task module.
- If a function starts task-local but is reusable for 2+ tasks, promote it to the appropriate shared layer in the same change (or immediately when adding the second consumer).
- If the same deterministic utility appears in more than one module, consolidate it into a shared helper immediately (do not keep parallel copies).

## Code documentation standards
- Add concise docstrings for new modules, classes, and non-trivial functions.
- Document assumptions, invariants, and non-obvious canonicalization behavior where implemented.
- Prefer comments that explain *why* a decision exists.
- Follow `docs/CODE_DOCUMENTATION.md` for the canonical checklist and doc-update triggers.

## Testing and validation expectations
- Add/maintain tests for schema validity, answer/evidence/verifier consistency, and determinism.
- Follow `docs/BUILD_VALIDATION.md` for pre-finalize validation, failure handling, cleanup, and CI strict-repro rules.
- Ensure validation errors map to cataloged codes in `docs/VALIDATION_ERROR_CODES.md`.

## Documentation discipline
- Keep `docs/BLUEPRINT.md` aligned with architecture/contract decisions.
- Keep `docs/PROMPT_SYSTEM.md` aligned with prompt-template architecture and implementation status.
- Keep `docs/SYSTEM_ARCHITECTURE.md` aligned with module boundaries, data flow, and lifecycle behavior.
- Keep `docs/TASK_AUTHORING.md` aligned with reusable task authoring guidance.
- Keep `docs/SHARED_UTILITIES.md` aligned with shared helper inventory and anti-duplication guidance.
- Keep `docs/CODE_REVIEW_GUIDELINES.md` aligned with reusable review checks and newly discovered review findings.
- Keep `docs/BUILD_VALIDATION.md` aligned with build/validation/CI behavior.
- Keep `docs/LESSONS_LEARNED.md` updated when new cross-task pitfalls are discovered.
- Keep `docs/TODO.md` updated so active, next, and deferred work stays explicit.
- After any change to architecture, module boundaries, shared utilities, or helper placement, update the relevant docs above in the same change.
- After each substantial review/refactor pass, add at least one reusable guideline to `docs/CODE_REVIEW_GUIDELINES.md` based on what was discovered.

## Workflow guidelines
- After any code edit, ask whether to commit before creating a commit.
- Avoid destructive git/file operations unless explicitly requested.
- Prefer clear, versioned contracts over implicit behavior.

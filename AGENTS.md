# TRACE AGENTS

## Project goal
TRACE is a grounded visual reasoning task environment for RLVR.
Each generated instance should include:
- prompt
- typed answer
- image(s)
- metadata-grounded verifier payload

## Source-of-truth docs
- Architecture and ABI contracts: `docs/DSL_BLUEPRINT.md`
- System module/lifecycle architecture: `docs/SYSTEM_ARCHITECTURE.md`
- Task creation procedure: `docs/TASK_AUTHORING.md`
- Shared reusable helpers and anti-duplication policy: `docs/SHARED_UTILITIES.md`
- Build/validation/CI policy: `docs/BUILD_VALIDATION.md`
- Validation error catalog: `docs/VALIDATION_ERROR_CODES.md`
- Reusable pitfalls and fixes: `docs/LESSONS_LEARNED.md`
- Python dependencies: `requirements.txt`

## Scope and boundaries
- Work in this repository unless the user explicitly asks otherwise.
- Prefer additive, reusable infrastructure over one-off task code.
- If behavior/contracts change, update the relevant source-of-truth docs above.

## Core engineering rules
- Use taxonomy consistently: `domain -> task_group -> task`.
- Sampling policy is task-level globally (equal task weights by default); domain/task_group probabilities are derived by aggregation, and query sampling happens inside each task (uniform by default unless task-config override).
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

## Code documentation standards
- Add concise docstrings for new modules, classes, and non-trivial functions.
- Document assumptions, invariants, and non-obvious canonicalization behavior where implemented.
- Prefer comments that explain *why* a decision exists.

## Testing and validation expectations
- Add/maintain tests for schema validity, answer/evidence/verifier consistency, and determinism.
- Follow `docs/BUILD_VALIDATION.md` for pre-finalize validation, failure handling, cleanup, and CI strict-repro rules.
- Ensure validation errors map to cataloged codes in `docs/VALIDATION_ERROR_CODES.md`.

## Documentation discipline
- Keep `docs/DSL_BLUEPRINT.md` aligned with architecture/contract decisions.
- Keep `docs/SYSTEM_ARCHITECTURE.md` aligned with module boundaries, data flow, and lifecycle behavior.
- Keep `docs/TASK_AUTHORING.md` aligned with reusable task authoring guidance.
- Keep `docs/SHARED_UTILITIES.md` aligned with shared helper inventory and anti-duplication guidance.
- Keep `docs/BUILD_VALIDATION.md` aligned with build/validation/CI behavior.
- Keep `docs/LESSONS_LEARNED.md` updated when new cross-task pitfalls are discovered.
- After any change to architecture, module boundaries, shared utilities, or helper placement, update the relevant docs above in the same change.

## Workflow guidelines
- After any code edit, ask whether to commit before creating a commit.
- Avoid destructive git/file operations unless explicitly requested.
- Prefer clear, versioned contracts over implicit behavior.

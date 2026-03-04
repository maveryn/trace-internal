# TRACE Code Documentation Guidelines

## Purpose
Define the expected standard for documenting TRACE code and related contracts.
Use this together with:
1. `docs/BLUEPRINT.md` for ABI/contract truth,
2. `docs/SYSTEM_ARCHITECTURE.md` for module boundaries and lifecycle,
3. `docs/TASK_AUTHORING.md` for task implementation workflow.

## Code-level documentation rules
1. Add concise docstrings for:
- new modules,
- new classes,
- non-trivial functions.
2. Document assumptions, invariants, and edge conditions where behavior is not obvious.
3. Call out canonicalization/determinism behavior when it affects identity, hashing, or replay.
4. Prefer comments that explain **why** a decision exists (not line-by-line restatements).
5. Keep wording precise and contract-oriented; avoid ambiguous prose.
6. In markdown/docs, use repo-scoped relative paths (for example `docs/README.md`), not absolute filesystem paths.

## What to include in docstrings
1. Responsibility: what the unit owns.
2. Inputs/outputs: key parameters and return shape.
3. Determinism notes: seed namespaces, ordering, or reproducibility constraints (if relevant).
4. Failure behavior: key exceptions/rejection conditions for non-obvious cases.

## Documentation update triggers (same change)
When behavior changes, update the relevant source-of-truth docs in the same PR:
1. ABI/schema/contract changes -> `docs/BLUEPRINT.md`
2. Module/dataflow/lifecycle changes -> `docs/SYSTEM_ARCHITECTURE.md`
3. Prompt asset/composition rules -> `docs/PROMPT_SYSTEM.md`
4. Shared helper placement or API changes -> `docs/SHARED_UTILITIES.md`
5. Build/validation/error handling changes -> `docs/BUILD_VALIDATION.md`, `docs/VALIDATION_ERROR_CODES.md`
6. Task behavior/policies -> `docs/tasks/<task_id>.md`, `docs/TASK_AUTHORING.md`, `docs/STATUS.md`, `docs/TODO.md`

## Minimal PR checklist
1. New/changed non-trivial code has appropriate docstrings/comments.
2. Determinism/canonicalization assumptions are documented where needed.
3. Source-of-truth docs are updated for any contract or architecture change.
4. Task docs are updated when task behavior/prompt/render policy changes.

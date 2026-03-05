# TRACE Code Documentation Guidelines

## Core rules
1. Add docstrings for new modules, classes, and non-trivial functions.
2. Document assumptions/invariants, especially around determinism and canonicalization.
3. Prefer comments that explain *why*, not line-by-line *what*.
4. Use repo-relative paths in docs (no absolute filesystem paths).

## Docstring minimum
1. Responsibility and ownership.
2. Key inputs/outputs.
3. Determinism notes (if seed/order dependent).
4. Failure/rejection behavior for non-obvious paths.

## Update triggers (same change)
1. ABI/contract changes -> `docs/BLUEPRINT.md`
2. Architecture/module flow changes -> `docs/SYSTEM_ARCHITECTURE.md`
3. Prompt-system changes -> `docs/PROMPT_SYSTEM.md`
4. Shared-helper placement/API changes -> `docs/SHARED_UTILITIES.md`
5. Validation/build behavior changes -> `docs/BUILD_VALIDATION.md`, `docs/VALIDATION_ERROR_CODES.md`
6. Task behavior changes -> `docs/tasks/<task_id>.md`, `docs/TASK_AUTHORING.md`, `docs/STATUS.md`

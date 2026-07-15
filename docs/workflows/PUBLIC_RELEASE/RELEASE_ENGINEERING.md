# Agent Brief: Public Release Engineering

## Objective

Make the public Trace repository safe, installable, testable, and releaseable
without changing reviewed task behavior. Treat clean packaging and security as
release gates, not cosmetic cleanup.

## Read First

- `AGENTS.md`
- `docs/README.md`
- `docs/workflows/PUBLIC_RELEASE/README.md`
- `docs/contracts/SOURCE_LAYOUT.md`
- `docs/workflows/BUILD_VALIDATION.md`
- `docs/workflows/CODE_REVIEW_GUIDELINES.md`
- Current `pyproject.toml`, `.gitignore`, `LICENSE`, and `CONTRIBUTING.md`

## Ownership

Own root packaging configuration, `.gitignore`, license/notice integration,
release scripts, and general CI. Do not edit `README.md`, public documentation
prose, `paper/**`, canonical result files, or task behavior.

## Required Work

1. Audit the intended public branch, not merely the current private worktree.
2. Remove or exclude private/internal artifacts: credentials, local notebooks,
   logs, caches, review databases, generated review artifacts, calibration
   state, temporary reports, checkpoints, and machine-specific paths.
3. Run a secret scan over tracked files and relevant public history. Never
   print, copy, inspect, or commit the contents of local token files.
4. Audit third-party assets, licenses, and notices.
5. Build wheel and source distributions and install each in a clean virtual
   environment.
6. Verify that package data includes required configs, prompt assets, fonts,
   and runtime resources.
7. Add CI for clean installation, focused core tests, deterministic generation
   and replay, verifier smoke, and package build.
8. Define a release checklist, version/tag procedure, and artifact inventory.

## Package Naming Decision

The current project name and import package may conflict with Python's standard
library `trace` module. Audit the real behavior in clean environments and
propose a stable public distribution/import contract. Do not perform a
repository-wide import rename until the user explicitly approves the proposal.
Once approved, coordinate the final contract with the API and docs agents.

## Release Gates

- No tracked credential or secret findings.
- Clean wheel and sdist installation succeeds.
- A generated instance can load all required package resources after install.
- Deterministic replay returns the same task record from the same seed/spec.
- A candidate answer can be scored using the public verifier path.
- Tests do not depend on the source checkout being on `PYTHONPATH`.
- The public branch contains no internal-only launch or review state.

Do not publish, push, upload, or tag without explicit user instruction. Use the
shared handoff format in `README.md` and include exact clean-install commands.


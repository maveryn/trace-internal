# TRACE Docs

This folder is the source of truth for contracts, architecture, workflows, and active task/domain specs.

Repo-local skills live under `skills/`, but skills are operational overlays. Canonical policy and contracts remain in `docs/`.

## Layout
- `docs/core/README.md` — ABI/contracts, prompt system, and runtime architecture.
- `docs/workflows/README.md` — authoring, shared-utility, validation, review, and documentation workflows.
- `docs/domains/README.md` — domain-specific setup notes and porting inventories.
- `docs/project/README.md` — current implementation snapshot and backlog.
- `docs/tasks/README.md` — task-level docs and template.

## Suggested read order
1. `docs/core/BLUEPRINT.md` — normative ABI/contracts.
2. `docs/core/SYSTEM_ARCHITECTURE.md` — code layout and runtime flow.
3. `docs/workflows/TASK_AUTHORING.md` — consolidated task authoring + quickstart checklist.
4. `docs/domains/TASK_FAMILY_VARIANTS.md` — family/variant taxonomy and planned task variants.
5. `docs/domains/TILE_TASK_SETUP.md` — concrete v1 setup for single-board coordinate-grounded tile tasks.
6. `docs/core/PROMPT_SYSTEM.md` — prompt bundles, variants, and metadata.
7. `docs/workflows/SHARED_UTILITIES.md` — helper placement and reuse rules.
8. `docs/workflows/BUILD_VALIDATION.md` + `docs/workflows/VALIDATION_ERROR_CODES.md` — pre-finalize checks and error taxonomy.
9. `docs/workflows/CODE_DOCUMENTATION.md` + `docs/workflows/CODE_REVIEW_GUIDELINES.md` — quality/process guidance.
10. `docs/project/STATUS.md` + `docs/project/TODO.md` — current snapshot and backlog.
11. `../task-reviews/README.md` — task-by-task review workflow and artifacts.

## Task docs
- Rules: `docs/tasks/README.md`
- Template: `docs/tasks/TASK_DOC_TEMPLATE.md`
- Task contracts: `docs/tasks/*.md`

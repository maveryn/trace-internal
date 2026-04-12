# TRACE Docs

This folder is the source of truth for contracts, architecture, workflows, and active task/domain specs.

Repo-local skills live under `skills/`, but skills are operational overlays. Canonical policy and contracts remain in `docs/`.

## Layout
- `docs/core/README.md` — ABI/contracts, prompt system, and runtime architecture.
- `docs/workflows/README.md` — authoring, shared-utility, validation, review, and documentation workflows.
- `docs/domains/README.md` — domain-specific setup notes and porting inventories.
- `docs/project/README.md` — current implementation snapshot, backlog, and cleanup planning.
- `docs/tasks/README.md` — task-level docs and template.

## Suggested read order
1. Foundation: `docs/core/BLUEPRINT.md`, `docs/core/SYSTEM_ARCHITECTURE.md`, and `docs/workflows/TASK_AUTHORING.md`.
2. Taxonomy: `docs/domains/TASK_FAMILY_VARIANTS.md`, then the relevant active domain setup doc listed in `docs/domains/README.md`.
3. Contracts: `docs/core/TASK_UNIT_POLICY.md`, `docs/core/RLVR_REWARD_CONTRACTS.md`, and `docs/core/PROMPT_SYSTEM.md`.
4. Export/eval: RLVR-specific export and validation docs live under `../rlvr/docs/README.md`.
5. Review workflow: `docs/workflows/SHARED_UTILITIES.md`, `docs/workflows/BUILD_VALIDATION.md`, `docs/workflows/VALIDATION_ERROR_CODES.md`, `docs/workflows/DOMAIN_AUDIT_REVIEW.md`, and `docs/workflows/TASK_UNIT_AUDIT.md`.
6. Quality/process: `docs/workflows/CODE_DOCUMENTATION.md` and `docs/workflows/CODE_REVIEW_GUIDELINES.md`.
7. Project state: `docs/project/STATUS.md`, `docs/project/TODO.md`, and `docs/project/DECLUTTER_PLAN.md`.
8. Task reviews: `../task-reviews/README.md`.

## Task docs
- Rules: `docs/tasks/README.md`
- Template: `docs/tasks/TASK_DOC_TEMPLATE.md`
- Task contracts: `docs/tasks/*.md`

# TRACE Docs

This folder is the source of truth for contracts, architecture, workflows, and active task/domain specs.

Repo-local skills live under `skills/`, but skills are operational overlays. Canonical policy and contracts remain in `docs/`. Skill-folder maintenance rules live in `../skills/README.md`.

## Layout
- `docs/core/README.md` — ABI/contracts, prompt system, and runtime architecture.
- `docs/workflows/README.md` — authoring, shared-utility, validation, review, and documentation workflows.
- `docs/domains/README.md` — domain-specific setup notes and porting inventories.
- `docs/project/README.md` — current implementation snapshot and cleanup planning.
- `docs/tasks/README.md` — task-level docs and template.
- `docs/ACTIVE_TASK_INVENTORY.md` — generated active public task inventory by domain and scene.

## Suggested read order
1. Foundation: `docs/core/BLUEPRINT.md`, `docs/core/SYSTEM_ARCHITECTURE.md`, and `docs/workflows/TASK_AUTHORING.md`.
2. Taxonomy: `docs/core/TAXONOMY.md` and `docs/core/TRACE_TAXONOMY_DESIGN.md`, then the relevant active domain setup doc listed in `docs/domains/README.md`. For approved contract-v0 domain migrations, also use `docs/workflows/TAXONOMY_V0_DOMAIN_MIGRATION.md`. For scene-package migrations that retire legacy `task_group` routing, use `docs/workflows/SCENE_PACKAGE_MIGRATION/README.md`.
3. Contracts: `docs/core/TASK_UNIT_POLICY.md`, `docs/core/RLVR_REWARD_CONTRACTS.md`, and `docs/core/PROMPT_SYSTEM.md`.
4. Export/eval:
   - active Vero-derived RLVR port lives under `../rlvr/README.md`
   - active task-review and calibration workspace lives under `../review/docs/README.md`
   - sampled external benchmark failure analysis lives in
     `docs/workflows/EXTERNAL_BENCHMARK_EVAL.md`
   - current task-calibration gates and vLLM serving commands live in
     `../review/docs/CALIBRATION_GUIDE.md`
5. Review workflow: `docs/workflows/SHARED_UTILITIES.md`, `docs/workflows/SHARED_LABEL_ASSETS.md`, `docs/workflows/SHARED_CONTEXT_TEXT_ASSETS.md`, `docs/workflows/SHARED_FONT_ASSETS.md`, `docs/workflows/BUILD_VALIDATION.md`, `docs/workflows/VALIDATION_ERROR_CODES.md`, `docs/workflows/DOMAIN_AUDIT_REVIEW.md`, `docs/workflows/TAXONOMY_V0_DOMAIN_MIGRATION.md`, `docs/workflows/TASK_REVIEW_WEB_APP.md`, `docs/workflows/BENCHMARK_REVIEW_WEB_APP.md`, `docs/workflows/TASK_UNIT_AUDIT.md`, and `docs/workflows/DOCS_AND_SKILLS_MAINTENANCE.md`.
   For repo-wide breaking output-contract renames, use
   `docs/workflows/ANNOTATION_CONTRACT_MIGRATION.md`.
   For implementation-layout migrations from task-group packages to
   scene packages, use `docs/workflows/SCENE_PACKAGE_MIGRATION/README.md`.
   For optional metadata-generated rationale targets, use
   `docs/workflows/TEMPLATED_RATIONALE_TARGETS.md`.
   For repeated-unit puzzle/game rendering upgrades, also use
   `docs/workflows/PUZZLE_GAME_RENDERING_UPGRADE.md`.
   For geometry/physics technical-diagram rendering upgrades, also use
   `docs/workflows/TECHNICAL_DIAGRAM_RENDERING_UPGRADE.md`.
6. Quality/process: `docs/workflows/CODE_DOCUMENTATION.md` and `docs/workflows/CODE_REVIEW_GUIDELINES.md`.
7. Project state: `docs/project/STATUS.md` and `docs/TODO.md`.
8. Task reviews: `../review/task-reviews/README.md`; the browser app in
   `docs/workflows/TASK_REVIEW_WEB_APP.md` is the default task inspection
   surface. External benchmark model-response inspection uses
   `docs/workflows/BENCHMARK_REVIEW_WEB_APP.md`.

## Task docs
- Rules: `docs/tasks/README.md`
- Template: `docs/tasks/TASK_DOC_TEMPLATE.md`
- Task contracts: `docs/tasks/*.md`

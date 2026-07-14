# TRACE Docs

This folder is the source of truth for contracts, architecture, workflows, and active task/domain specs.

Repo-local skills live under `skills/`, but skills are operational overlays. Canonical policy and contracts remain in `docs/`. Skill-folder maintenance rules live in `../skills/README.md`.

## Layout
- `docs/contracts/README.md` — repo-wide ABI, taxonomy, annotation/reward,
  prompt, validation, and runtime contracts.
- `docs/workflows/README.md` — authoring, build, review, benchmark, and
  documentation-maintenance procedures. Documentation placement rules live in
  `docs/workflows/DOC_STRUCTURE.md`.
- `docs/resources/README.md` — shared fonts, labels, context text, and
  rationale-target resources.
- `docs/domains/README.md` — domain-specific contract docs.
- `docs/review/README.md` — reviewer-facing task, scene, and domain audit
  procedures.
- `docs/tasks/README.md` — task-level docs and template.
- `docs/ACTIVE_TASK_INVENTORY.md` — generated active public task inventory by domain and scene.

## Suggested read order
1. Foundation: `docs/contracts/BLUEPRINT.md`,
   `docs/contracts/SYSTEM_ARCHITECTURE.md`,
   `docs/contracts/SOURCE_LAYOUT.md`, and
   `docs/workflows/TASK_AUTHORING.md`.
2. Taxonomy: `docs/contracts/TAXONOMY.md`, `docs/contracts/TASK_UNIT_POLICY.md`,
   and `docs/contracts/PROGRAM_SCHEMA_CATALOG.md`, then the relevant active domain
   setup doc listed in `docs/domains/README.md`.
3. Contracts: `docs/contracts/ANNOTATION_AND_REWARD_CONTRACTS.md` and `docs/contracts/PROMPT_SYSTEM.md`.
4. Export/eval:
   - active Vero-derived RLVR port lives under `../rlvr/README.md`
   - tentative TRACE RLVR training strategy lives in
     `docs/RLVR_TRAINING_STRATEGY.md`
   - task-conditioned answer/annotation selection policy lives in
     `docs/workflows/RLVR_TASK_SUPERVISION_POLICY.md`
   - retained legacy split-v1 training commands live in
     `docs/workflows/RLVR_TRAINING_RUNBOOK.md`
   - current EasyR1 all1000 global and task-conditioned commands live in
     `docs/workflows/TRACE_ANNOTATION_ABLATION_RUNBOOK.md`
   - frozen TRACE RLVR train/test task split lives in
     `docs/RLVR_TASK_SPLIT_PLAN.md`
   - generated task-review artifacts live under `../review/task-reviews/`
   - sampled external benchmark failure analysis lives in
     `docs/workflows/EXTERNAL_BENCHMARK_EVAL.md`
   - current task-calibration gates and vLLM serving commands live in
     `docs/workflows/CALIBRATION_GUIDE.md`
5. Resources: `docs/resources/SHARED_LABEL_ASSETS.md`,
   `docs/resources/SHARED_CONTEXT_TEXT_ASSETS.md`,
   `docs/resources/SHARED_FONT_ASSETS.md`, and
   `docs/resources/TEMPLATED_RATIONALE_TARGETS.md`.
6. Review workflow: `docs/workflows/BUILD_VALIDATION.md`,
   `docs/contracts/VALIDATION_ERROR_CODES.md`,
   `docs/review/ANNOTATION_REVIEW.md`,
   `docs/review/PROMPT_REVIEW.md`,
   `docs/review/RENDERER_REVIEW.md`,
   `docs/review/DOMAIN_RELEASE_READINESS.md`,
   `docs/workflows/TASK_REVIEW_WEB_APP.md`,
   `docs/workflows/BENCHMARK_REVIEW_WEB_APP.md`, and
   `docs/workflows/DOCS_AND_SKILLS_MAINTENANCE.md`.
   Domain-specific rendering and shared-code rules live in the matching
   `docs/domains/*.md`
   contract.
7. Quality/process: `docs/workflows/DOC_STRUCTURE.md`,
   `docs/workflows/DOCS_AND_SKILLS_MAINTENANCE.md`, and
   `docs/workflows/CODE_REVIEW_GUIDELINES.md`.
8. Project backlog and active surface: `docs/TODO.md` and `docs/ACTIVE_TASK_INVENTORY.md`.
9. Task reviews: the browser app in `docs/workflows/TASK_REVIEW_WEB_APP.md`
   is the default task inspection surface, with generated artifacts under
   `../review/task-reviews/`. External benchmark model-response inspection
   uses `docs/workflows/BENCHMARK_REVIEW_WEB_APP.md`.

## Task docs
- Rules: `docs/tasks/README.md`
- Template: `docs/tasks/TASK_DOC_TEMPLATE.md`
- Task contracts: `docs/tasks/<domain>/<scene_id>/<task_id>.md`

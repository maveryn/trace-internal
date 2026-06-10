# Workflow Docs

Use this folder for implementation and review procedures.

Repo-local workflow skills under `skills/` are operational overlays. The canonical process docs are listed here. Skill-folder maintenance rules live in `../../skills/README.md`.

## Authoring
- `TASK_AUTHORING.md` — task creation checklist and contract guidance.
- `SHARED_UTILITIES.md` — helper placement and anti-duplication rules.
- `SHARED_LABEL_ASSETS.md` — repo-wide label/name manifests, source metadata,
  and task-local filtering guidance.
- `SHARED_CONTEXT_TEXT_ASSETS.md` — repo-wide non-answer context/distractor
  text manifests, source metadata, and renderer usage rules.
- `SHARED_FONT_ASSETS.md` — repo-wide vendored font assets, deterministic
  font-family sampling, and text-role consistency rules.
- `TEMPLATED_RATIONALE_TARGETS.md` — standard for optional metadata-generated
  rationale targets across output modes, detail levels, and domains.
- `PUZZLE_GAME_RENDERING_UPGRADE.md` — scene-by-scene checklist for repeated-unit puzzle/game rendering upgrades.
- `TECHNICAL_DIAGRAM_RENDERING_UPGRADE.md` — scene-by-scene checklist for geometry/physics technical-diagram rendering upgrades.
- `INFORMATION_SCENE_RENDERING_UPGRADE.md` — scene-by-scene checklist for charts/pages/graph structured-information rendering upgrades.

## RLVR-specific workflows
RLVR training/export/validation docs live under:
- `../../rlvr/README.md` for the active Vero-derived RLVR port.
- `../../review/docs/README.md` for the active task-review and calibration workspace.
- `../../review/docs/CALIBRATION_GUIDE.md` for the current per-task acceptance gates,
  model-specific response caps, and split vLLM server commands used by
  calibration agents.

## Review
- `BUILD_VALIDATION.md` — build/test/review workflow.
- `DOMAIN_AUDIT_REVIEW.md` — domain-by-domain sanitation and audit workflow.
- `ANNOTATION_CONTRACT_MIGRATION.md` — repo-wide breaking migration runbook
  for replacing the public `annotation` contract with `annotation`.
- `TAXONOMY_V0_DOMAIN_MIGRATION.md` — strict per-domain migration workflow for
  applying the approved contract-v0 taxonomy with no compatibility aliases or
  stale public task ids.
- `SCENE_PACKAGE_MIGRATION/README.md` — tracked scene-package migration
  workflow for retiring legacy task-group packages, enforcing objective
  ownership, and validating domain/scene/task packages.
- `TASK_REVIEW_WEB_APP.md` — browser app workflow for inspecting active
  task-review sidecars and collecting sample-level reviewer issues.
- `BENCHMARK_REVIEW_WEB_APP.md` — separate browser app workflow for inspecting
  external benchmark model responses by benchmark and correctness status.
- `TASK_UNIT_AUDIT.md` — rubric for auditing whether a task is the right unit for uniform task-level sampling.
- `VALIDATION_ERROR_CODES.md` — validation error taxonomy.

## Quality
- `CODE_DOCUMENTATION.md` — documentation standards and update triggers.
- `CODE_REVIEW_GUIDELINES.md` — reusable review checklist and distilled findings.
- `DOCS_AND_SKILLS_MAINTENANCE.md` — required docs/skills update workflow,
  anti-drift rules, and validation commands.

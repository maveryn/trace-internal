# Workflow Docs

Use this folder for cross-domain implementation and review procedures. Do not
keep domain-specific rendering/style upgrade checklists here; durable
domain-specific rendering rules belong in `../domains/<domain>.md`.

Repo-local workflow skills under `skills/` are operational overlays. The canonical process docs are listed here. Skill-folder maintenance rules live in `../../skills/README.md`.

## Authoring
- `TASK_AUTHORING.md` — task creation checklist and contract guidance.
Shared text/font/rationale resources live under `../resources/`.

## RLVR-specific workflows
RLVR training/export/validation docs live under:
- `../../rlvr/README.md` for the active Vero-derived RLVR port.
- `../RLVR_TRAINING_STRATEGY.md` for tentative TRACE RLVR training,
  reward-ablation, response-length, and evaluation-cadence strategy.
- `RLVR_TRAINING_RUNBOOK.md` for the current split-v1 training, validation,
  checkpoint-merge, resume, and external-benchmark commands.
- `TASK_REVIEW_WEB_APP.md` for the active task-review workspace.
- `CALIBRATION_GUIDE.md` for the current per-task acceptance gates,
  model-specific response caps, and split vLLM server commands used by
  calibration agents.

## Review
- `BUILD_VALIDATION.md` — build/test/review workflow.
- `../review/README.md` — human/agent review procedures for task, scene, and
  domain audits, including annotation review.
- `../review/DOMAIN_RELEASE_READINESS.md` — release-readiness review for
  complete domain task surfaces.
- `TASK_REVIEW_WEB_APP.md` — browser app workflow for inspecting active
  task-review sidecars and collecting sample-level reviewer issues.
- `BENCHMARK_REVIEW_WEB_APP.md` — separate browser app workflow for inspecting
  external benchmark model responses by benchmark and correctness status.
Validation error-code taxonomy lives in
`../contracts/VALIDATION_ERROR_CODES.md`.

## Quality
- `CODE_REVIEW_GUIDELINES.md` — compact reusable review checklist.
- `DOC_STRUCTURE.md` — allowed documentation roots, banned legacy roots, and
  source-of-truth placement rules.
- `DOCS_AND_SKILLS_MAINTENANCE.md` — required docs/skills update workflow,
  code-documentation rules, anti-drift rules, and validation commands.

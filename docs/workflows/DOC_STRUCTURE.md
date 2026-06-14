# Documentation Structure

This is the repo-wide placement contract for source-of-truth documentation.
Keep it short and current; detailed policy belongs in the specific contract or
workflow doc.

## Allowed Top-Level Docs Areas
- `docs/contracts/` — repo-wide contracts: taxonomy, task-unit policy, prompt
  system, annotation/reward schema, architecture, validation errors, and ABI.
- `docs/workflows/` — procedures for authoring, review, calibration,
  documentation maintenance, benchmark review, and build validation.
- `docs/domains/` — domain-specific contracts only: scene boundaries,
  annotation conventions, prompt constraints, and domain rendering rules.
- `docs/resources/` — shared resource guidance for fonts, labels, context text,
  and generated rationale targets.
- `docs/tasks/` — public task contracts at
  `docs/tasks/<domain>/<scene_id>/<task_id>.md`, plus the task-doc template and
  task-doc maintenance guide.
- `docs/SCENE_PACKAGE_MIGRATION/` — active scene-package migration rules,
  checklists, receipts, and shared-boundary notes.
- `docs/ACTIVE_TASK_INVENTORY.md` — generated active task inventory.
- `docs/TODO.md` — current project backlog only.

## What Does Not Belong In Docs
- Historical migration reports, old taxonomy analyses, retired task lists, and
  stale benchmark scratch reports.
- Generated task-review artifacts, issue databases, calibration status files,
  cache files, notebooks, or local run output.
- Duplicate exhaustive task inventories outside
  `docs/ACTIVE_TASK_INVENTORY.md` and generated/checked task docs.

## Banned Legacy Roots
Do not recreate these roots or link to them from active docs/skills:

- `docs/core/`
- `docs/project/`
- `plans/`
- `review/docs/`
- `review/code-review/`
- `review/taxonomy-audit/`
- `review/trace-extension/`

The `review/` tree is for generated review artifacts and reviewer issue state,
not source-of-truth documentation.

## Update Rule
If a change introduces a new documentation location or changes ownership of a
doc category, update this file, `docs/README.md`,
`docs/workflows/README.md`, and the docs consistency tests in the same patch.

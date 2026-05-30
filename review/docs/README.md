# TRACE Review Workspace

This directory is the active workspace for task-review and calibration
operation. Generated review artifacts live under `review/task-reviews/`;
reviewer feedback and calibration status are fresh state under `review/` and
are not copied from older workspaces.

Canonical review and calibration references:

- `review/docs/CALIBRATION_GUIDE.md` for the current model, server, artifact
  freshness, and acceptance gates.
- `docs/workflows/TASK_REVIEW_WEB_APP.md` for browser-app review workflow.
- `docs/workflows/DOMAIN_AUDIT_REVIEW.md` for domain-by-domain audit rules.
- `docs/workflows/BUILD_VALIDATION.md` for validation and review commands.

The browser app defaults to `review/task-reviews` and persists feedback in
`review/feedback/review_feedback.sqlite`. Agents that fix reviewer feedback
should add a brief repair note to the relevant feedback item in the app after
changing code, prompts, configs, docs, or generated artifacts. Repair notes do
not resolve feedback; human review resolves feedback after inspecting the
updated sample or task.

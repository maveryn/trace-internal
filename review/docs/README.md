# TRACE Review Workspace

This directory is the active workspace for task-review and calibration
operation. Generated review artifacts live under `review/task-reviews/`;
reviewer issue state and calibration status are fresh state under `review/` and
are not copied from older workspaces.

Canonical review and calibration references:

- `review/docs/CALIBRATION_GUIDE.md` for the current model, server, artifact
  freshness, and acceptance gates.
- `docs/workflows/TASK_REVIEW_WEB_APP.md` for browser-app review workflow.
- `docs/workflows/BENCHMARK_REVIEW_WEB_APP.md` for the separate external
  benchmark model-performance review app.
- `docs/workflows/DOMAIN_AUDIT_REVIEW.md` for domain-by-domain audit rules.
- `docs/workflows/BUILD_VALIDATION.md` for validation and review commands.

The browser app defaults to `review/task-reviews` and persists issue threads in
`review/feedback/review_feedback.sqlite`. The reviewer-facing UI term is
"issue" and browser issue pages use `/issues`; internal APIs and storage keep
the `feedback` name for compatibility. Agents that fix reviewer issues should
add a brief repair note to the relevant issue item in the app after
changing code, prompts, configs, docs, or generated artifacts. Repair notes do
not resolve issues; human review resolves issues after inspecting the
updated sample or task.

Agent quick rules:

- Generate task-review artifacts under `review/task-reviews/`, not under stale
  planning or root-level review paths.
- Reload the app index after any `review/task-reviews` artifact change; restart
  the app after review-app code, template, CSS/JS, indexer, resource, feedback,
  or schema changes.
- Use app issue threads for task/sample comments. If a thread already exists,
  continue that thread instead of creating a duplicate issue item.
- Add agent repair notes only after making and validating the fix. Include the
  validation/review command and whether artifacts were regenerated/reloaded.
- Leave issues `open` for human verification unless explicitly instructed to
  resolve them. Resolved issues leave the open-blocker view on `/issues` but
  remain stored and visible on their thread/detail pages.
- Treat a task as complete only when browser-app manual audit gates pass and
  current solve-rate status is accepted.
- Keep task review and benchmark review separate: task review reads
  `review/task-reviews`, while benchmark review reads external benchmark run
  artifacts such as `runs/external_benchmarks/qwen25vl7b/20260522T062435Z`.

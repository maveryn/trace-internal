# Review Docs

This folder contains reviewer-facing procedures for judging task, scene, and
domain quality. These docs explain how to audit generated tasks against current
TRACE norms; they do not define new public task contracts.

Use these docs when reviewing existing tasks, generated review artifacts, or
domain-wide consistency:

- `ANNOTATION_REVIEW.md` — how to review annotation schema choices, witness
  geometry, prompt hints, task docs, and clear versus borderline annotation
  issues.
- `PROMPT_REVIEW.md` — how to review prompt wording, output examples,
  annotation hints, verbosity, and prompt/answer/annotation alignment.
- `RENDERER_REVIEW.md` — how to review prompt-render consistency, semantic
  marker colors/styles, layout, labels, options, visual variety, and annotation
  projection onto final pixels.
- `DOMAIN_RELEASE_READINESS.md` — how to review a domain as a complete
  training/release surface, including scene/task uniqueness, prompts,
  annotation, renderer quality, artifacts, docs, and remaining blockers.

Dated domain release-readiness snapshots that are worth keeping as references
live under `domain-release-readiness/reference/`. They are historical reports,
not active policy.

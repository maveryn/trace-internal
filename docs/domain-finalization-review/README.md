# Domain Finalization Review

Use this folder for release-readiness reviews after a domain has completed
scene-package migration and the active task set is intended to be final for the
current training/release surface.

This is not the scene-package migration workflow. Migration verifies source
layout and objective ownership. Finalization verifies the domain as a coherent
collection: scene uniqueness, task uniqueness, query boundaries, prompts,
annotation contracts, renderer quality, distributions, review artifacts, and
remaining release blockers.

Primary checklist:

```text
docs/domain-finalization-review/DOMAIN_FINALIZATION_CHECKLIST.md
```

Domain outputs should live under:

```text
docs/domain-finalization-review/<domain>/
```

Keep reports issue-focused. Do not copy generated task-review artifacts into
this folder; generated review samples remain under `review/task-reviews/`.

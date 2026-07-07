# TRACE Source Layout

This document defines the current TRACE v0 task-source shape. It is a
final-state architecture contract.

## Public Task Files

Each active public task id maps to one public task module:

```text
trace/tasks/<domain>/<scene_id>/<objective_contract>.py
```

The public task file owns the objective-specific behavior:

- literal public `task_id`;
- supported `query_id` values and query validation;
- objective-specific sampling constraints;
- answer binding;
- `annotation_gt` binding;
- dynamic prompt slots;
- task-specific trace fields;
- final `TaskOutput` construction.

A public task file may call shared primitives, but it must not be a wrapper
that only sets constants and delegates the whole objective to shared code.

## Shared-Code Boundaries

Use the narrowest reusable layer that fits:

```text
trace/core/
trace/tasks/shared/
trace/tasks/<domain>/shared/
trace/tasks/<domain>/<scene_id>/shared/
task-local helpers
```

Scene-local `shared/` contains reusable scene primitives: state, sampling,
layout, rendering, projection, annotation helpers, validation helpers, and
scene math or mechanics.

Domain `shared/` contains code reused across multiple scenes in one domain. It
is not a dumping ground for one scene's objective logic.

Shared code must stay identity-free. It must not accept or branch on public
`task_id`, `query_id`, objective contract, public task name, registered class
name, or sibling task identity. Resolve public task/query branches in the
public task file and pass semantic arguments into shared helpers.

## Prompt And Config Ownership

User-facing prompt prose, examples, answer instructions, annotation
instructions, and static wording live in prompt bundles under `prompts/`.
Task modules provide dynamic slot values and selected prompt keys.

Configs hold generation, rendering, prompt, and visual knobs. They must not
contain public objective dispatch, task coverage, query routing, query weights,
or retired difficulty gates.

## Retired Surface Policy

Retired public task ids are deleted from active code and docs. Do not keep
compatibility task aliases, disabled registry entries, redirect docs, config
stubs, prompt branches, absence-only tests, or stale review paths for retired
public ids.

Active source, configs, prompts, docs, taxonomy metadata, tests, and review
artifacts should describe only the current task surface.

## Review Expectations

Before generating or accepting task-review artifacts for changed tasks, verify:

- source ownership follows this layout;
- prompt, answer, annotation, and trace fields come from the same execution;
- task docs contain concrete program contracts and current query ids;
- review artifacts are regenerated under `review/task-reviews/` after source,
  config, prompt, or task-doc changes;
- browser review gates and reviewer issues are updated through the review app.

Passing tests are guardrails, not a substitute for source ownership review.

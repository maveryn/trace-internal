# Scene Migration Guide

Use this guide for one assigned scene. Do not migrate a whole domain from this
document.

## First Rule

Do not start by moving files. First understand the scene contract and each task
contract. A correct migration makes ownership obvious in source.

## Target Layout

```text
trace/tasks/<domain>/<scene_id>/<objective_contract>.py
trace/tasks/<domain>/<scene_id>/_lifecycle.py        # optional
trace/tasks/<domain>/<scene_id>/shared/
configs/domains/<domain>/<scene_id>.yaml
```

`_lifecycle.py` is allowed only for neutral scene plumbing. It must not route
objective behavior by task id, query id, objective name, or registered class.

## Public Task Files Own

Each public task file must own the public task behavior:

- literal public `TASK_ID`
- supported local query ids
- query selection and query validation
- objective-specific sampling constraints
- target/candidate construction when objective-specific
- answer binding
- `annotation_gt` binding
- dynamic prompt slot values
- task-specific trace fields
- final `TaskOutput` construction

The public file may call shared primitives. It must not hand the objective to a
shared `generate_task(...)`, `Builder`, `Runtime`, or multi-task pipeline.

## Scene Shared Owns

`shared/` contains scene primitives only:

- state/dataclasses/enums
- neutral sampling primitives
- rendering/layout/projection helpers
- annotation projection primitives
- reusable validation helpers
- scene math/mechanics/geometry primitives

`shared/` must not:

- accept or branch on public `task_id`, `query_id`, objective contract, public
  task name, registered class name, or sibling task identity
- export public query-id routing tables
- build final `TaskOutput` for public tasks
- contain task-named runtime files
- hide copied public task bodies

If shared code needs to know which public task or query is running, the branch
belongs in the public task file. Resolve the semantic argument there and pass
the semantic value into shared code.

## Domain Shared Promotion

Do not move helpers into `trace/tasks/<domain>/shared/` during the first pass
just because they look reusable. Keep helpers in the owning scene first. Promote
only after a second scene actually needs the helper, or after the domain has an
explicit approved family boundary for that helper. Promotion is a separate
cleanup step from objective migration.

Domain shared code must remain scene-neutral and identity-free. It must not
accept or branch on public task ids, query ids, objective names, registered task
classes, or scene ids.

## Prompt And Config Rules

- User-facing prompt prose lives in prompt assets, not task modules.
- Task code provides dynamic slot values and selected prompt keys.
- Configs hold scene/task generation and rendering knobs.
- Configs must not contain query routing, query weights, public task ids,
  objective dispatch, or task coverage.
- Query branches are task-internal mirrors of one objective contract and are
  sampled uniformly unless a later approved global policy says otherwise.

## Annotation Rules

- Use `annotation` / `annotation_gt`, not historical `evidence`.
- Annotation marks minimal visual witnesses.
- Use keyed annotation when witness roles matter.
- Answer and annotation must come from the same execution trace.

## Required Process

1. Inventory active task ids, source files, config, prompts, docs, tests, and
   review folders for the assigned scene.
2. Write the scene contract: visual grammar, layout/view, style variation, and
   annotation projection assumptions.
3. Write one task contract per active public task: answer schema, annotation
   schema, query ids, reasoning program, and owned logic.
4. Decide any split/merge/delete before moving code.
5. Extract reusable scene primitives into `shared/`.
6. Rewrite each public task file so it owns the objective.
7. Record any cross-scene promotion candidates, but do not promote them during
   the scene migration unless the domain companion doc already approves that
   family boundary.
8. Remove retired source files, aliases, stale configs, stale prompts, and stale
   review folders for that scene.
9. Smoke-generate every task and every supported query branch.
10. Add the scene to `SCENE_PACKAGE_REVIEW_CANDIDATE_SCENES`.
11. Manually audit source boundaries before generating review artifacts.
12. Run the required scene-scoped migration/review tests with
    `TRACE_SCENE_PACKAGE_REVIEW_SCENE=<domain>/<scene_id>`.
13. Record passing manual audit and migration test status under
    `review/task-reviews/<domain>/<scene_id>/`.
14. Generate fresh task-review artifacts only after the gates pass.
15. Reload the review app index.

## Failure Rule

If a gate fails, fix the scene source or remove the scene from the
review-candidate registry. Do not edit tests, weaken policies, rename the
violation, fake manual audit status, fake migration status, or hand over stale
review artifacts.

## Handoff

Report:

- scene migrated
- active task ids
- files changed
- tests run
- review artifacts generated
- app reload/restart status
- blockers or reviewer issues

Do not call the scene complete. Human review in the browser app is required.

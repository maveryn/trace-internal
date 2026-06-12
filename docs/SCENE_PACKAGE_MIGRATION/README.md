# Scene-Package Migration

This folder defines the current rules for migrating one scene package at a
time.

## Intent

Migration is a source-design task. It is not a path move, a wrapper split, a
test chase, or a way to manufacture review artifacts.

The target source shape is:

```text
domain -> scene_id -> task_id
task_<domain>__<scene_id>__<objective_contract>
```

A scene is not review-ready if it still depends on public task/query routing in
shared code, wrapper-only task files, copy-split task bodies, stale review
artifacts, forged status files, or compatibility aliases.

## Read Order

1. `SCENE_MIGRATION_GUIDE.md`
2. `ENFORCEMENT_TESTS.md`
3. `RECEIPT_SCHEMA.md`

Domain-level companion docs may be added here only when a domain has shared
scene infrastructure that needs explicit ownership rules before scene work can
proceed. Current companion docs:

- `GRAPH_SHARED_STRUCTURE.md`: graph-domain ownership plan for graph algorithms,
  renderers, scene-local shared role files, and the `graph/node_link` migration.
- `GAMES_SHARED_BOUNDARY.md`: games-domain ownership plan for domain-shared
  helpers versus one scene's `shared/` package.
- `CHARTS_SHARED_BOUNDARY.md`: charts-domain ownership plan for implementation-
  only renderer families, chart-domain shared helpers, and scene-local shared
  packages.

Even with a companion doc, migrate one scene correctly before broad domain work.

## Non-Negotiables

- One active public task id maps to one public task file.
- Public task files own objective/query logic, answer binding, annotation
  binding, task-specific prompt slots, task-specific trace fields, and final
  task output construction.
- Scene `shared/` code owns reusable scene primitives only.
- Shared code must not accept or branch on public `task_id`, `query_id`,
  objective contract, public task name, registered class name, or sibling task
  identity.
- No wrapper-only task files.
- No copy-split legacy modules.
- No task-named shared runtime files.
- No hardcoded user-facing prompt prose in task modules.
- No stale task ids, compatibility aliases, or disabled retired tasks.
- No generated review artifacts for scenes that fail pre-review gates.
- No speculative domain-shared promotion. Keep helpers scene-local first, then
  promote only after confirmed multi-scene reuse or an approved family boundary.

Tests are guardrails. Passing tests does not prove the migration is complete.
Failing tests prove the scene is not ready. Fix the source design; do not weaken
tests, hide the violation, or write status files that pretend the design is
valid.

## Status Terms

- `unmigrated`: no current scene-package refactor.
- `in progress`: source is being refactored and is not ready for review.
- `review-candidate`: scene is listed in
  `SCENE_PACKAGE_REVIEW_CANDIDATE_SCENES` so migration tests and review gates
  inspect it.
- `review-ready`: source audit, tests, smoke generation, review artifacts, and
  app reload are complete. Human review is still required.
- `accepted`: the human reviewer accepted the scene in the browser app and a
  receipt was recorded in the review workspace.

There is no Python "complete" registry. Human acceptance is not represented by
adding a source allowlist entry.

## Scope

During scene migration, work only on the assigned scene and the live references
needed for that scene:

- `trace/tasks/<domain>/<scene_id>/`
- `configs/domains/<domain>/<scene_id>.yaml`
- prompt assets for that scene
- live registry/taxonomy/docs rows for active task ids in that scene
- focused tests for that scene and the shared migration contract
- `review/task-reviews/<domain>/<scene_id>/`

Do not use a scene migration as broad repo cleanup. Do not edit migration
contract tests, migration registries, migration docs, or policy modules unless
the user explicitly asks for a contract change.

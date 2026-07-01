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
2. `TAXONOMY_REVIEW_CHECKLIST.md`
3. `SCALAR_ANNOTATION_ROLLOUT.md`
4. `../contracts/PROGRAM_SCHEMA_CATALOG.md`
5. `ENFORCEMENT_TESTS.md`
6. `RECEIPT_SCHEMA.md`
7. `POST_MIGRATION_DOMAIN_CHECKLIST.md` after every scene in a domain has
   passed human review and the domain needs a final consistency sweep.

Domain-level companion docs may be added here only when a domain has shared
scene infrastructure that needs explicit ownership rules before scene work can
proceed. Current companion docs:

- `GRAPH_SHARED_STRUCTURE.md`: graph-domain shared-boundary guidance for graph
  algorithms, renderers, and scene-local shared role files.
- `GAMES_SHARED_BOUNDARY.md`: games-domain ownership plan for domain-shared
  helpers versus one scene's `shared/` package.
- `CHARTS_SHARED_BOUNDARY.md`: charts-domain ownership plan for implementation-
  only renderer families, chart-domain shared helpers, and scene-local shared
  packages.
- `GEOMETRY_SHARED_BOUNDARY.md`: geometry-domain ownership plan for approved
  low-level primitives, scene-local diagram grammars, and legacy shared
  surfaces to decompose during scene migration.
- `ICONS_SHARED_BOUNDARY.md`: icons-domain ownership plan for curated/procedural
  icon assets, shared visual primitives, scene-local icon grammars, and legacy
  output/query plumbing to decompose during scene migration.
- `ILLUSTRATIONS_SHARED_BOUNDARY.md`: illustrations-domain ownership plan for
  reusable object/person renderers, scene-local visual grammars, derived visual
  scenes, and legacy counting/task-common surfaces to decompose during scene
  migration.
- `PAGES_SHARED_BOUNDARY.md`: pages-domain ownership plan for page-layout,
  text, control, form, route, document, and infographic primitives versus
  scene-local page grammars and legacy routing surfaces to decompose during
  scene migration.
- `PHYSICS_SHARED_BOUNDARY.md`: physics-domain ownership plan for physical
  system diagrams, formulas, apparatus renderers, scene-local physical
  grammars, and legacy family modules to decompose during scene migration.
- `PUZZLES_SHARED_BOUNDARY.md`: puzzles-domain ownership plan for repeated-cell
  puzzle primitives, scene-local rules/constraints/solvers, and legacy
  `*_scene.py` / `*_common.py` surfaces to decompose during scene migration.
- `SYMBOLIC_SHARED_BOUNDARY.md`: symbolic-domain ownership plan for notation,
  readout, automaton, probability-device, logic-circuit, and chemistry-scene
  primitives versus scene-local shared packages.
- `THREE_D_SHARED_BOUNDARY.md`: three_d-domain ownership plan for reusable 3D
  object resources/renderers, scene-local spatial grammars, and legacy
  objective-base surfaces to decompose during scene migration.

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
- No generated review artifacts without a passing scene-level taxonomy review
  status file.
- No generated review artifacts without passing scene-level manual source audit
  and scene-scoped migration test status files.
- No scene taxonomy review passes with a one-item set annotation for a task that
  guarantees exactly one point or box witness.
- No task can be review-done until the human reviewer checks the task-level
  taxonomy review gate in the browser app.
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
- `review-ready`: source audit, taxonomy audit, scene-scoped migration tests,
  automated source audit, smoke generation, review artifacts, and app reload
  are complete. Human review is still required.
- `accepted`: the human reviewer accepted the scene in the browser app and a
  receipt was recorded in the review workspace.

There is no Python "complete" registry. Human acceptance is not represented by
adding a source allowlist entry.

Use `migrated` only for an `accepted` scene. A scene-shaped source package,
passing migration tests, passing manual source audit, passing taxonomy audit,
or appearing as a review-candidate is not by itself migrated. Before human
review, the best status is `review-ready`.

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

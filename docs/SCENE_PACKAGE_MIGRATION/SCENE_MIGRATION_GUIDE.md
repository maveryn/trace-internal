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

## Source Formatting

- Migrated scene-package source should be Black-style Python with an
  88-character line length.
- Public task files must be easy to visually audit: split long calls,
  dictionaries, tuples, and lifecycle invocations across multiple lines.
- Do not compress public objective/query logic into long one-line calls just
  because the code is mechanically correct.
- The automated source-formatting gate is being rolled out scene by scene. It
  currently applies to `puzzles/arithmetic_panel`; expand it to additional
  migrated scenes after formatting those scenes.

## Annotation Rules

- Use `annotation` / `annotation_gt`.
- Annotation marks minimal visual answer-verification witnesses for the task
  family, not the full reasoning proof. Direct visible-answer tasks usually
  annotate selected/countable answer objects; derived value tasks annotate the
  minimal visible operands needed to verify the computation; diagram tasks
  annotate canonical visual primitives. Keep reference objects, scope regions,
  candidate sets, derivation operands, and debug/proof details in trace
  metadata unless they are part of the task's answer-verification witness.
- Use map annotation when witness roles matter.
- Use scalar `point` / `bbox` for tasks that guarantee exactly one witness once
  those public contracts are wired. Do not use one-item sets for guaranteed
  single-witness tasks.
- Answer and annotation must come from the same execution trace.

## Required Process

1. Inventory active task ids, source files, config, prompts, docs, tests, and
   review folders for the assigned scene.
2. Write the scene contract: visual grammar, layout/view, style variation, and
   annotation projection assumptions.
3. Write one task contract per active public task: answer schema, annotation
   schema, query ids, reasoning program, and owned logic.
4. Apply `TAXONOMY_REVIEW_CHECKLIST.md`: verify concrete program codes,
   explicit allowed arguments, stable answer/annotation contracts, and semantic
   query ids before moving code.
   Also apply `SCALAR_ANNOTATION_ROLLOUT.md` for single-witness annotation
   eligibility.
5. Decide any split/merge/delete before moving code.
6. Extract reusable scene primitives into `shared/`.
7. Rewrite each public task file so it owns the objective.
8. Record any cross-scene promotion candidates, but do not promote them during
   the scene migration unless the domain companion doc already approves that
   family boundary.
9. Remove retired source files, aliases, stale configs, stale prompts, and stale
   review folders for that scene.
10. Smoke-generate every task and every supported query branch.
11. Add the scene to `SCENE_PACKAGE_REVIEW_CANDIDATE_SCENES`.
12. Manually audit source boundaries and write
    `review/task-reviews/<domain>/<scene_id>/manual_code_audit_status.json`
    only after the audit really passed.
13. Re-run taxonomy review against the migrated source and task docs, then
    write `review/task-reviews/<domain>/<scene_id>/taxonomy_review_status.json`
    only after every active task has a concrete app-visible Program Contract,
    stable answer/annotation schemas, valid semantic query ids, and completed
    scalar annotation review recorded as `scalar_annotation_checked=true`.
14. Run the required scene-scoped migration/review tests with
    `TRACE_SCENE_PACKAGE_REVIEW_SCENE=<domain>/<scene_id>`.
15. Record passing `migration_test_status.json` under
    `review/task-reviews/<domain>/<scene_id>/`, including the command and the
    required migration test files.
16. Generate fresh task-review artifacts only after the manual source audit,
    taxonomy audit, scene-scoped migration tests, and automated source audit
    all pass. `scripts/run_task_review.py` enforces these status files for
    registered review-candidate scenes and rejects stale taxonomy status files
    that have not recorded scalar annotation review.
17. Reload the review app index.

## Failure Rule

If a gate fails, fix the scene source or remove the scene from the
review-candidate registry. Do not edit tests, weaken policies, rename the
violation, fake taxonomy status, fake manual audit status, fake migration
status, or hand over stale review artifacts.

Do not use migration as broad cleanup. Scene-local cleanup required to make the
assigned scene correct is part of migration. Cross-scene/domain cleanup is a
separate approved task unless the scene is blocked and the user explicitly
approves a shared-boundary change.

## Handoff

Report:

- scene migrated
- active task ids
- files changed
- tests run
- taxonomy review status
- review artifacts generated
- app reload/restart status
- blockers or reviewer issues

Do not call the scene complete. Human review in the browser app is required.

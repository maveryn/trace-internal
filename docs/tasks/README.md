# Task Docs

Task docs describe durable public task contracts. They are not task inventory,
review status, solve-rate status, migration history, or compatibility notes.

## Public Identity

Public task identity uses:

```text
domain -> scene_id -> task_id
task_<domain>__<scene_id>__<objective_contract>
```

Generated outputs record the concrete internal branch as `query_id`.
`query_id` is replay/review metadata, not a public sampling unit.

## Location

Task contract docs live at:

```text
docs/tasks/<domain>/<scene_id>/<task_id>.md
```

Use `docs/ACTIVE_TASK_INVENTORY.md` for the generated active task listing.
Do not duplicate the inventory in this README.

## Required Content

Each task doc should include only stable contract details:

- public identity;
- answer schema;
- annotation schema;
- supported `query_id` values;
- reasoning/program contract;
- prompt bundle reference;
- deterministic sampling or uniqueness constraints that matter to the public
  contract.

Keep generated review artifacts, solve-rate status, calibration notes,
migration status, stale task ids, and compatibility routing out of task docs.

## Template

Use `docs/tasks/TASK_DOC_TEMPLATE.md` for new or rewritten task docs.

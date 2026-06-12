# Taxonomy-V0 Domain Migration

Use this workflow when migrating one TRACE domain from the current public task
ids to the approved contract-v0 taxonomy. It is designed for parallel work:
one agent should own one domain at a time and should not edit unrelated
domains except for truly shared infrastructure required by that domain.

## Purpose

The approved taxonomy is the active `v0` design. The migration should make the
repository look as if the approved taxonomy has always been the current task
surface.

This means:

1. public task ids, configs, docs, tests, prompts, review artifacts, and
   taxonomy metadata must agree;
2. retired public ids must be deleted, not preserved;
3. task-level sampling remains meaningful because each public task is one
   stable scene contract plus one stable task contract.

## Required Reading

Read these before changing a domain:

1. `docs/README.md`
2. `docs/core/TAXONOMY.md`
3. `docs/core/TASK_UNIT_POLICY.md`
4. `docs/workflows/DOMAIN_AUDIT_REVIEW.md`
5. `docs/workflows/TASK_REVIEW_WEB_APP.md`
6. the domain setup doc in `docs/domains/`
7. the relevant task docs in `docs/tasks/`
8. the approved rows in `review/taxonomy-audit/contract_v0_reanalysis/`

Repo-local skills may be read for operational hints, but they are not authority
for task-boundary decisions. If skills conflict with the core taxonomy docs,
use the core docs and update the stale reference in the same change.

## Source Of Truth

The domain migration source is:

```text
review/taxonomy-audit/contract_v0_reanalysis/proposed_task_summary.csv
review/taxonomy-audit/contract_v0_reanalysis/task_query_analysis.csv
```

Use the proposed mapping only after the relevant taxonomy decision has been
approved or explicitly cleared by the reviewer. If a mapping is questionable,
stop and discuss it; do not invent a new split/merge during the migration pass.

The public task id form is:

```text
task_<domain>__<scene_id>__<task_slug>
```

`scene_id` is implementation/config routing only. It is not the public
taxonomy unit.

## No Compatibility Layer

There is no compatibility support after the migration.

Do not keep:

1. alias task ids;
2. disabled legacy tasks;
3. compatibility wrapper tasks;
4. redirect docs saying an old task became a new task;
5. config entries for retired ids;
6. prompt/template branches kept only for retired ids;
7. tests whose only purpose is to check retired ids stay absent;
8. stale review folders for retired task ids;
9. historical taxonomy/review artifacts in active review surfaces;
10. comments, examples, or docs that describe the old taxonomy as history.

Shared implementation code may remain only when it is genuinely reusable and
not named, registered, or documented as a retired public task.

## Migration Units

For each current task in the domain, classify the taxonomy action from the
approved audit:

1. `keep`: public id stays the same, but metadata/docs may still need cleanup.
2. `rename`: one current public id becomes one new public id.
3. `split`: one current public id becomes multiple new public ids.
4. `merge`: multiple current public ids become one new public id.
5. `delete`: current public id is retired without replacement.

Do not perform extra merges or splits during implementation unless the reviewer
explicitly approves the change.

## Contract Rules

Each final public task must have one stable:

```text
scene_contract + answer_schema + annotation_schema + concrete program_schema
```

`query_id` is internal. It may vary only within one stable task contract, such
as mirror directions, bounded predicate directions, rank parameters, target
attributes, or replay keys. It must not hide a different answer schema,
annotation schema, program schema, or query-facing view contract.

If a branch changes the concrete program skeleton, it belongs in a separate
public task.

## Implementation Patterns

### Rename

For a one-to-one rename:

1. change the registered public task id;
2. update taxonomy, configs, prompts, docs, tests, and review paths;
3. delete old public id references;
4. keep implementation code only if its names are no longer legacy-facing or
   are clearly private implementation details.

### Split

For one current task that splits into several public tasks:

1. create one registered public task per proposed task id;
2. restrict each public task to the query/program branches it owns;
3. share renderer/sampler/helper code through neutral private helpers;
4. do not keep the old public task id;
5. remove old review folders and regenerate review artifacts for each new task.

Split tasks may live in the same source module when that is the narrowest
clean implementation. Public class/task names, configs, docs, and review paths
must still use the final task ids.

### Merge

For multiple current tasks that merge:

1. create or retain one final registered public task id;
2. move allowed branch differences into internal query parameters only when
   the task contract stays identical;
3. delete all retired public task ids from active registry/config/docs/tests;
4. remove stale review folders for the retired ids.

### Delete

For a retired task with no replacement:

1. unregister it;
2. remove imports and docs;
3. remove config/prompt/test/review artifacts;
4. remove stale taxonomy/review references from active surfaces.

## Files That Must Stay In Sync

For every changed task id, update all applicable surfaces:

1. task module and registered class/task id;
2. package imports in `trace/tasks/**/__init__.py` or equivalent;
3. `trace/core/taxonomy.py`;
4. domain/scene config YAML under `configs/domains/<domain>/`;
5. prompt bundle and prompt config keys under `prompts/`;
6. task docs under `docs/tasks/`;
7. domain setup doc under `docs/domains/`;
8. generated active inventory if stale;
9. pytest files for that domain/task;
10. review artifacts under
    `review/task-reviews/<domain>/<scene_id>/<task_id>/`;
11. taxonomy audit source/output if the implementation exposes a needed
    correction to the approved mapping;
12. reviewer issue threads: add repair notes for fixed issues.

After deleting or renaming task ids, search the repo:

```bash
rg '<old_task_id>'
```

Any remaining hit must be either removed or justified as non-active source
data. In general, old task ids should not remain anywhere in code, docs,
configs, prompts, tests, or active review surfaces.

## Review Artifacts

Generate task-review artifacts only under:

```bash
review/task-reviews/
```

Use:

```bash
PYTHONPATH=. python scripts/run_task_review.py --tasks <task_id> --mode full --out-root review/task-reviews
```

After review artifacts change, reload the app index:

```bash
curl -fsS -X POST http://127.0.0.1:7860/api/reload
```

Restart the app only if app code, templates, CSS, JavaScript, indexing,
resource handling, feedback storage, or schema code changed.

Delete review folders for retired task ids. Do not keep old folders as
provenance in `review/task-reviews`.

Solve-rate artifacts do not automatically transfer across splits or merges.
Unless the reviewer explicitly says a previous solve-rate status transfers,
leave the new task's solve-rate status pending.

## Validation

Run focused checks for the domain before handoff:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest <domain/task tests> -q
PYTHONPATH=. python scripts/check_active_inventory_integrity.py
PYTHONPATH=. python scripts/generate_active_task_inventory.py --check
PYTHONPATH=. python review/taxonomy-audit/contract_v0_reanalysis/build_contract_v0_reanalysis.py
git diff --check
```

Also regenerate task reviews for every changed public task and reload the app
index. If a shared helper changed, expand pytest coverage to sibling tasks that
use the helper.

If a distribution check fails during review generation, fix the generator or
sampling support before handoff. Do not silently accept a failed distribution.

## Parallel Work Rules

1. One agent owns one domain.
2. Avoid broad repo-wide rewrites during a domain migration.
3. Do not touch another domain's task ids unless the reviewer explicitly asks.
4. Shared helper changes must be minimal and documented.
5. If another agent edits the same file, inspect the current file and work with
   their changes; do not revert unrelated work.
6. If a conflict requires a taxonomy decision, stop and ask rather than making
   a local policy exception.

## Handoff Format

End every domain migration with:

1. domain name;
2. task count before and after;
3. old-to-new task id mapping;
4. deleted retired ids;
5. split/merge/rename summary;
6. files changed;
7. review artifacts regenerated;
8. review app reload/restart status;
9. tests and checks run;
10. remaining blockers or reviewer decisions needed.

Use concise tables for mappings. Do not bury retired ids in prose.

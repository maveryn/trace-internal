# Taxonomy Bookkeeping

This file defines where taxonomy migration state lives during scene-package
migration.

## Current Sources

Use these as the current sources of truth:

1. Rules:
   - `docs/core/TAXONOMY.md`
   - `docs/core/TASK_UNIT_POLICY.md`
   - `docs/core/PROGRAM_SCHEMA_CATALOG.md`
   - `docs/SCENE_PACKAGE_MIGRATION/TAXONOMY_REVIEW_CHECKLIST.md`
2. Active public mapping:
   - `trace/core/taxonomy.py`
   - registered task modules
   - current configs, prompt assets, and task docs
3. Scene migration status:
   - `review/task-reviews/<domain>/<scene_id>/taxonomy_review_status.json`
   - `review/task-reviews/<domain>/<scene_id>/migration_test_status.json`
   - browser-review issue threads and human checklist state

## Retired Audit Package

`review/taxonomy-audit/contract_v0_reanalysis/` was a generated taxonomy audit
package. It is no longer a reliable source of truth for current migration
decisions because it can contain stale inventories, stale task ids, partial
generated summaries, and historical review rows.

Do not use that package to decide current task boundaries. If it contains a
manual note that is still useful, port the durable rule into one of the current
docs above and then treat the old row as obsolete.

## What To Keep From Old Audits

Keep only durable, policy-level content:

- reusable program-schema names and do-not-merge boundaries;
- task/query boundary examples that still match current code;
- one-off approved merge/split decisions only after revalidating them against
  current code and task docs;
- reviewer rationale that explains a current rule.

Do not keep old generated artifacts as active references:

- stale inventory CSVs;
- stale proposed task summaries;
- stale domain markdown summaries;
- stale validation JSON;
- old review rows for retired task ids;
- old scripts whose output is no longer used by the review app.

## Current Review Workflow

For each migrated scene:

1. Review task contracts using the current docs and current code.
2. Ensure every task has concrete program code and valid `query_id` boundaries.
3. Write or update scene-local taxonomy status under `review/task-reviews/`.
4. Generate task reviews only after migration tests and manual code audit pass.
5. Reload the review app index after artifact changes.

The migration checkpoint should be scene-local. One stale or failing taxonomy
row from another domain must not block review artifact generation for the
assigned scene.

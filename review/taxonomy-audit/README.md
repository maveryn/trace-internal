# TRACE Taxonomy Audit Artifacts

This folder contains generated taxonomy audit artifacts from prior review
passes. These artifacts are review data, not current task-boundary policy.

Current policy and bookkeeping live in:

- `docs/core/TAXONOMY.md`
- `docs/core/TASK_UNIT_POLICY.md`
- `docs/core/PROGRAM_SCHEMA_CATALOG.md`
- `docs/SCENE_PACKAGE_MIGRATION/TAXONOMY_REVIEW_CHECKLIST.md`
- `docs/SCENE_PACKAGE_MIGRATION/TAXONOMY_BOOKKEEPING.md`
- scene-local status under `review/task-reviews/<domain>/<scene_id>/`

## Legacy Package

`contract_v0_reanalysis/` is a generated snapshot package. It may contain stale
inventories, stale task ids, and partial generated summaries. Do not use it as a
migration source of truth. If a manual note in that package is still useful,
port the durable rule into the current docs above and treat the old row as
obsolete.

The review app may still expose legacy taxonomy packages for inspection, but
current scene-package migration decisions must use the docs and live code.

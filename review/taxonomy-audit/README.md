# TRACE Contract-v0 Taxonomy Review

This folder contains the current contract-v0 task-boundary review package.

## Current Package

- `contract_v0_reanalysis/`: active taxonomy review artifacts.
- `contract_v0_reanalysis/task_query_analysis.csv`: current task/query rows mapped to proposed task units.
- `contract_v0_reanalysis/proposed_task_summary.csv`: current task to proposed task-unit summary.
- `contract_v0_reanalysis/canonical_program_schemas.csv`: canonical program signatures used by the review app tree.
- `contract_v0_reanalysis/domain_taxonomies/`: per-domain notes.
- `contract_v0_reanalysis/source/`: seed inputs used to rebuild the current package.

The review app exposes this package at `/taxonomy` and `/taxonomy/contract-v0`.
The tree view is `/taxonomy/contract-v0/tree`.

No other taxonomy package is part of the active review surface.

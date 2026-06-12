# Contract-v0 TRACE Taxonomy Reanalysis

This package applies the current scene-contract plus task-contract rule to the live default task inventory.
The source seed files provide hand-authored task/query boundary coverage; this package is the current contract-v0 reanalysis output.

## Totals

- Live tasks audited: 966
- Live task/query rows audited: 1158
- Proposed task units: 966
- Base program contracts: 966
- Duplicate base program contracts: 0
- Program argument metadata rows: 1158
- Program argument rows needing review: 26
- Canonical program signatures: 137
- Current tasks with split recommendation: 0
- Current tasks with rename-only recommendation: 0
- Approved current-task merges: 1
- Exact same-scene merge candidates requiring human review: 0

## Domain Summary

| Domain | Current tasks | Proposed task units | Split tasks | Rename-only | Delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| charts | 186 | 186 | 0 | 0 | +0 |
| games | 161 | 161 | 0 | 0 | +0 |
| geometry | 192 | 192 | 0 | 0 | +0 |
| graph | 61 | 61 | 0 | 0 | +0 |
| icons | 40 | 40 | 0 | 0 | +0 |
| illustrations | 26 | 26 | 0 | 0 | +0 |
| misc | 42 | 42 | 0 | 0 | +0 |
| pages | 92 | 92 | 0 | 0 | +0 |
| physics | 53 | 53 | 0 | 0 | +0 |
| puzzles | 80 | 80 | 0 | 0 | +0 |
| three_d | 33 | 33 | 0 | 0 | +0 |

## Output Files

- `task_query_analysis.csv` is the row-level source of truth for proposed task units; count unique `proposed_task_id` values there for final unit counts.
- `proposed_task_summary.csv` is grouped by current live task id. Split rows list multiple proposed task ids in `proposed_task_ids`; the file is not one row per proposed task.
- `canonical_program_schemas.csv` tracks reusable program signatures. Reuse of a signature does not imply public task merging.

## Validation Notes

- Every active default task from the registry is represented.
- Every query id from the live audit inventory is represented.
- Per-query observed review samples are preferred for answer/annotation schema; inventory strings are fallback only.
- Program names are canonicalized through `canonical_program_schemas.csv`; reuse across domains canonicalizes terminology but does not merge public tasks.
- Approved current-task merges are listed in `source/approved_current_task_merges.csv`; unapproved proposed-task-id collisions are validation failures.
- Exact same-scene merge candidates are listed separately and must be manually approved before any code refactor.

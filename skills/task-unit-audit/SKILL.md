---
name: task-unit-audit
description: Use when auditing whether a TRACE task is the right unit for uniform task-level sampling, especially to decide whether tasks should be kept, broadened, merged, split, or removed based on visual-grounding breadth and within-task variety.
---

# Task-Unit Audit

Use this when reviewing the TRACE task inventory as benchmark units rather than only as implementation modules.

## Read first
1. `docs/workflows/TASK_UNIT_AUDIT.md`
2. `docs/workflows/DOMAIN_AUDIT_REVIEW.md`
3. `docs/workflows/CODE_REVIEW_GUIDELINES.md`
4. The relevant domain setup doc in `docs/domains/`
5. The relevant domain skill in `skills/domain-<domain>/`

## Workflow
1. Inventory the task's actual scene variants, query variants, and evidence contract.
2. Judge whether it is one uniform visual-grounding family with enough within-task variety.
3. Assign one outcome:
   - `Keep`
   - `Broaden`
   - `Merge`
   - `Split`
   - `Retire`
4. If merge/split is recommended, name the neighboring tasks or variants involved.
5. Keep the reasoning focused on visual-grounding breadth and uniform task sampling, not on whether the task is text-heavy or reasoning-heavy.

## Handoff
Report each audited task under:
- `Outcome`
- `Why`
- `Scene variety`
- `Query variety`
- `Grounding necessity`
- `Evidence fit`
- `Follow-up`

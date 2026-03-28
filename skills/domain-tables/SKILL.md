---
name: domain-tables
description: Use when designing, implementing, or reviewing TRACE table-domain tasks, especially for styled table scene variants, bbox evidence policy, row/column summary structure, and table shared-helper reuse.
---

# Tables Domain

Use this whenever the task lives under `domain=tables`.

## Read first
1. `docs/domains/TABLE_TASK_SETUP.md`
2. `docs/project/STATUS.md`
3. `docs/workflows/TASK_AUTHORING.md`
4. `docs/workflows/SHARED_UTILITIES.md`

## Table-domain rules
- Keep `task_group` aligned to reasoning family, not table style.
- Keep `scene_variant` for visual table styling and keep the table semantics separate from the style layer.
- Styled table scenes currently live under `trace/tasks/tables/shared/table_scene.py`.
- Table construction/config helpers currently live under `trace/tasks/tables/shared/table_common.py`.
- Table-domain background/noise defaults currently live under `trace/tasks/tables/shared/visual_defaults.py`.
- Reuse the shared short-name manifest through `trace/tasks/shared/name_assets.py` whenever visible person-style row labels are needed.

## Evidence rules
- Tables should use one stable prompt-facing evidence type: `bbox_set`.
- Table evidence boxes should mark the minimal supporting table region(s).
- Use one cell bbox when a single numeric cell is decisive.
- Use one row-region bbox when the witness is a whole row of numeric cells.
- Use one column-region bbox when the witness is a whole numeric column.
- For column-filter counting tasks, use one bbox per matching queried-column value cell in deterministic top-to-bottom row order.
- If a task has multiple disjoint decisive regions, use multiple boxes in deterministic order rather than inventing a new evidence type.
- For table readout tasks that query multiple cells, keep bbox evidence in the same order the cells are named in the prompt and record that ordered query-cell metadata in trace.
- For pairwise table comparison tasks, keep evidence as the ordered pair of compared value-cell bboxes rather than only the winning cell so the comparison witness remains explicit.
- For counting tasks that compare two columns row-by-row, keep evidence row-major and preserve prompt column order within each matching row's bbox pair.
- For filtered table aggregation tasks, keep evidence as ordered `[filter cell, target cell]` bbox pairs for each selected row instead of inventing a special filter witness type.
- For extremum-transfer tasks, keep evidence as exactly two boxes ordered `[source extremum cell, transferred target cell]`.
- For table ranking tasks beyond plain argmax/argmin, use the queried-column region bbox when the witness is the column-wide ordering, not a single decisive cell.

## Design heuristics
- Treat table style as presentation only. `spreadsheet`, `zebra`, `ledger`, and `card_table` should not change the reasoning contract.
- Keep one leftmost row-label column unless a task has a documented reason to change the schema.
- Prefer short visible row labels and short metric headers so the table stays readable at moderate row/column counts.
- When tasks aggregate over one column, keep that as a column-summary task instead of mixing row and column aggregation into one contract.
- When tasks aggregate over one row, treat that as a separate row-summary task rather than overloading a column-summary task.
- Keep early table tasks column-centric where possible: column summary, column filtering, and direct row+column cell readout all reuse the same clear table schema before row-summary tasks are added.
- If a table readout task broadens from one exact cell to one-or-more queried cells with simple arithmetic, rename the task/module to the broader subset concept instead of keeping a stale `cell_value` name.
- Keep prompts explicit about what evidence region should be boxed.
- When row/column summary mirrors share the same answer shape and the same `bbox_set` evidence contract, prefer widening `task_variant` inside the existing statistics task instead of adding a near-duplicate sibling task id.
- When a table task combines selection and aggregation, keep one semantic axis in `task_variant` and let simpler internal subtypes (for example filter condition flavor) vary inside the task if that avoids exploding the task count without changing the evidence contract.

## Schema lessons learned
- Row-name answers can be real visible strings; they do not need to be forced into `option_letter`.
- The evidence contract is cleaner if the answer is the row label and the evidence is the decisive supporting cell/region bbox.
- For row-comparison tasks, a row-label answer plus the ordered pair of compared cells is cleaner than trying to invent a new pairwise evidence type.
- The prompt should always name the queried column or row explicitly so the evidence region is obvious.
- Table tasks are a strong fit for `scene_variant` expansion because table styling can vary widely while the cell geometry contract stays stable.

## Readability rules
- Prefer moderate row/column counts and readable cell padding over squeezing in more schema complexity.
- Use style variation through shading, borders, and frame treatment before changing the semantic table layout.
- Keep header text and row labels short enough that cells do not rely on clipping or tiny fonts.
- If a new style makes cell text hard to read, adjust canvas size, font size, or padding before reducing the task contract.

## Coverage reference
For current table coverage and active task families, use:
- `docs/project/STATUS.md`
- `docs/domains/TASK_FAMILY_VARIANTS.md`

## Pair with
- `skills/task-design/SKILL.md`
- `skills/task-complexity/SKILL.md`
- `skills/task-implementation/SKILL.md`
- `skills/verification-review/SKILL.md`

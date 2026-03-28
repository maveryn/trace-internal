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

## Design heuristics
- Treat table style as presentation only. `spreadsheet`, `zebra`, `ledger`, and `card_table` should not change the reasoning contract.
- Keep one leftmost row-label column unless a task has a documented reason to change the schema.
- Prefer short visible row labels and short metric headers so the table stays readable at moderate row/column counts.
- When tasks aggregate over one column, keep that as a column-summary task instead of mixing row and column aggregation into one contract.
- When tasks aggregate over one row, treat that as a separate row-summary task rather than overloading a column-summary task.
- Keep early table tasks column-centric where possible: column summary, column filtering, and direct row+column cell readout all reuse the same clear table schema before row-summary tasks are added.
- Keep prompts explicit about what evidence region should be boxed.
- The current statistics family already splits naturally into row-identity questions (`summary_label`) and numeric column-summary questions (`summary_value`); follow that separation for future table tasks too.

## Schema lessons learned
- Row-name answers can be real visible strings; they do not need to be forced into `option_letter`.
- The evidence contract is cleaner if the answer is the row label and the evidence is the decisive supporting cell/region bbox.
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

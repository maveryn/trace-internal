# `task_tables_counting_column_pair_count`

## 1) Identity
1. Domain: `tables`
2. Task group: `counting`
3. Task id: `task_tables_counting_column_pair_count`
4. Objective: count how many rows satisfy one strict comparison between two queried numeric columns.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `col_a_gt_col_b`
   - `col_a_lt_col_b`
2. Supported `scene_variant` values:
   - `spreadsheet`
   - `zebra`
   - `ledger`
   - `card_table`
3. `answer_gt.type`: `integer`
4. `evidence_gt.type`: `bbox_set`
5. Scene contract:
   - one table per image,
   - one leftmost `Name` column,
   - `3..5` numeric columns by default,
   - `5..10` data rows by default,
   - row labels are short visible person-style names,
   - the query names two distinct numeric columns,
   - the answer is the number of rows whose two queried values satisfy the strict comparison.
6. Generation guarantees:
   - the answer count is sampled from the feasible `0..row_count` support before the two queried columns are finalized,
   - the queried columns are always distinct,
   - all row comparisons are strict, so equality never determines a counted row,
   - evidence is the ordered set of two queried value-cell bboxes for every matching row, in top-to-bottom row order and prompt column order within each row.

## 3) Prompt contract
1. Bundle: `tables_counting_v1`
2. `task_family_key`: `styled_table_counting`
3. `task_key`: `column_pair_count_query`
4. `task_variant_key`: one of `col_a_gt_col_b|col_a_lt_col_b`
5. Required slots:
   - task-family: `object_description`
   - task-variant: `query_column_a`, `query_column_b`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/tables/counting.yaml`,
   - deterministic bundle selection from `prompts/tables/counting/tables_counting_v1.json`.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt-facing answer is the exact integer count; prompt-facing evidence is the bbox array of all matching queried-column cell pairs.

## 4) Evidence + trace contract
1. Prompt-facing evidence is a `bbox_set` containing one ordered pair of queried-column value-cell bboxes per matching row.
2. Global evidence order is top-to-bottom row order.
3. Within each matching row, the two bboxes stay in the same column order as the prompt query.
4. `projected_evidence` includes:
   - `bbox_set`
5. `scene_ir.entities` stores one entity per table cell with:
   - `cell_role`
   - `row_index`
   - `column_index`
   - row/column labels when applicable
   - rendered cell/text geometry
6. `render_map` includes:
   - `column_region_bboxes_px`
   - `row_region_bboxes_px`
   - `row_label_bboxes_px`
   - `header_bboxes_px`
   - `cell_bboxes_px`
7. `execution_trace` records:
   - `task_variant`
   - `scene_variant`
   - row labels, column headers, and full numeric table values
   - queried column A / queried column B
   - answer count
   - matching row labels/indices
   - supporting cell ids in evidence order
   - row/column count ranges

## 5) Visual policy
1. Background and post-image noise use the merged tables-domain visual defaults from `configs/domains/tables/base.yaml`.
2. V1 tables use clean light solid backgrounds only.
3. The 4 active `scene_variant` styles change grid/shading/frame presentation while preserving the same cell geometry contract.
4. Numeric values are printed directly in cells for all active table styles.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. `task_variant` and `scene_variant` are sampled independently at the policy level.
3. Answers and evidence come from the same generated table.
4. No semantic auto-relaxation.
5. Review overlays rely on the ordered value-cell pair bboxes recorded in trace, not OCR from pixels.

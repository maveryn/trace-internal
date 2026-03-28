# `task_tables_statistics_summary_value`

## 1) Identity
1. Domain: `tables`
2. Task group: `statistics`
3. Task id: `task_tables_statistics_summary_value`
4. Objective: return a numeric summary value for one queried column or row subset.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `column_sum`
   - `column_mean`
   - `column_median`
   - `row_sum`
   - `row_mean`
   - `table_sum`
   - `table_mean`
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
   - column variants query one numeric column,
   - row variants query one visible row label,
   - table variants summarize all numeric cells in the table,
   - the answer is the requested integer summary over that column, row, or whole-table numeric subset.
6. Generation guarantees:
   - `column_sum` uses integer cell values and returns the exact column total,
   - `column_mean` is constructed so the column mean is an integer,
   - `column_median` uses an odd row count and a unique median value by construction,
   - `row_sum` uses integer cell values and returns the exact row total,
   - `row_mean` is constructed so the row mean is an integer,
   - `table_sum` uses integer cell values and returns the exact total across all numeric cells,
   - `table_mean` is constructed so the mean across all numeric cells is an integer,
   - evidence is exactly one bbox for the supporting queried-column data region on column variants, one bbox for the supporting queried-row region on row variants, and one bbox for the full numeric-table region on table variants.

## 3) Prompt contract
1. Bundle: `tables_statistics_v1`
2. `task_family_key`: `styled_table_statistics`
3. `task_key`: `summary_value_query` for column variants, `summary_row_value_query` for row variants, and `summary_table_value_query` for table variants
4. `task_variant_key`: one of `column_sum|column_mean|column_median|row_sum|row_mean|table_sum|table_mean`
5. Required slots:
   - task-family: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/tables/statistics.yaml`,
   - deterministic bundle selection from `prompts/tables/statistics/tables_statistics_v1.json`.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt-facing answer is the exact integer summary value; prompt-facing evidence is the bbox of the supporting queried-column region on column variants, the supporting queried-row region on row variants, or the full numeric-table region on table variants.

## 4) Evidence + trace contract
1. Prompt-facing evidence is one `bbox_set` containing exactly one supporting column-region bbox on column variants, one supporting row-region bbox on row variants, or one full numeric-table region bbox on table variants.
2. `projected_evidence` includes:
   - `bbox_set`
3. `scene_ir.entities` stores one entity per table cell with:
   - `cell_role`
   - `row_index`
   - `column_index`
   - row/column labels when applicable
   - rendered cell/text geometry
4. `render_map` includes:
   - `column_region_bboxes_px`
   - `numeric_table_region_bbox_px`
   - `row_region_bboxes_px`
   - `row_label_bboxes_px`
   - `header_bboxes_px`
   - `cell_bboxes_px`
5. `execution_trace` records:
   - `task_variant`
   - `scene_variant`
   - row labels, column headers, and full numeric table values
   - queried column on column variants
   - queried row on row variants
   - numeric cell count on table variants
   - answer value
   - supporting region kind/header, supporting region kind/row label, or supporting table region metadata
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
5. Review overlays rely on the supporting column-region bbox, supporting row-region bbox, or supporting full numeric-table region bbox recorded in trace, not OCR from pixels.

# `task_tables_statistics_row_summary_label`

## 1) Identity
1. Domain: `tables`
2. Task group: `statistics`
3. Task id: `task_tables_statistics_row_summary_label`
4. Objective: return the row label that has the highest or lowest total across the numeric columns.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `row_sum_argmax`
   - `row_sum_argmin`
2. Supported `scene_variant` values:
   - `spreadsheet`
   - `zebra`
   - `ledger`
   - `card_table`
3. `answer_gt.type`: `string`
4. `evidence_gt.type`: `bbox_set`
5. Scene contract:
   - one table per image,
   - one leftmost `Name` column,
   - `3..5` numeric columns by default,
   - `5..10` data rows by default,
   - row labels are short visible person-style names,
   - the answer is the visible row label whose numeric-row total is the unique maximum or minimum, depending on `task_variant`.
6. Generation guarantees:
   - each row total is unique by construction,
   - `row_sum_argmax` returns the row with the largest numeric-row total,
   - `row_sum_argmin` returns the row with the smallest numeric-row total,
   - evidence is exactly one bbox for the supporting winning-row numeric-cell region.

## 3) Prompt contract
1. Bundle: `tables_statistics_v1`
2. `task_family_key`: `styled_table_statistics`
3. `task_key`: `summary_row_label_query`
4. `task_variant_key`: one of `row_sum_argmax|row_sum_argmin`
5. Required slots:
   - task-family: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/tables/statistics.yaml`,
   - deterministic bundle selection from `prompts/tables/statistics/tables_statistics_v1.json`.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt-facing answer is the exact winning row-name string; prompt-facing evidence is the bbox of the supporting winning-row region.

## 4) Evidence + trace contract
1. Prompt-facing evidence is one `bbox_set` containing exactly one supporting row-region bbox.
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
   - `row_region_bboxes_px`
   - `row_label_bboxes_px`
   - `header_bboxes_px`
   - `cell_bboxes_px`
5. `execution_trace` records:
   - `task_variant`
   - `scene_variant`
   - row labels, column headers, and full numeric table values
   - answer row label/index
   - answer winning row-total value
   - supporting region kind/row label
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
5. Review overlays rely on the supporting winning-row region bbox recorded in trace, not OCR from pixels.

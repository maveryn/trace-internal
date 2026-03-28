# `task_tables_readout_subset_value`

## 1) Identity
1. Domain: `tables`
2. Task group: `readout`
3. Task id: `task_tables_readout_subset_value`
4. Objective: return the exact integer value of one queried cell or a simple arithmetic result over two queried cells.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `cell_lookup`
   - `cell_sum_two`
   - `cell_difference_two_abs`
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
   - `cell_lookup` names one visible row label and one numeric column,
   - `cell_sum_two` and `cell_difference_two_abs` name two visible row/column cells,
   - `cell_difference_two_abs` always asks for the absolute difference,
   - the answer is an integer read or computed directly from the queried cells.
6. Generation guarantees:
   - the queried cell or ordered queried cell pair is sampled explicitly and recorded in trace,
   - queried cell values are set explicitly after the table is sampled so readout answers stay answer-diverse,
   - evidence is one bbox for `cell_lookup` and two ordered bboxes for the two-cell variants.

## 3) Prompt contract
1. Bundle: `tables_readout_v1`
2. `task_family_key`: `styled_table_readout`
3. `task_key`: `subset_value_query`
4. `task_variant_key`: `cell_lookup|cell_sum_two|cell_difference_two_abs`
5. Required slots:
   - task-family: `object_description`
   - `cell_lookup`: `query_row_label_1`, `query_column_1`
   - `cell_sum_two|cell_difference_two_abs`: `query_row_label_1`, `query_column_1`, `query_row_label_2`, `query_column_2`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/tables/readout.yaml`,
   - deterministic bundle selection from `prompts/tables/readout/tables_readout_v1.json`.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt-facing answer is the exact requested integer result; prompt-facing evidence is the bbox of the queried supporting cell for `cell_lookup` and the ordered pair of queried supporting cell bboxes for the two-cell variants.

## 4) Evidence + trace contract
1. Prompt-facing evidence is a `bbox_set` containing the queried supporting cell bbox or the ordered pair of queried supporting cell bboxes.
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
   - ordered queried cell metadata (row labels, column headers, indices, values, cell ids)
   - answer value
   - supporting cell ids in the same order as the prompt query
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
5. Review overlays rely on the supporting queried-cell bbox or ordered queried-cell bboxes recorded in trace, not OCR from pixels.

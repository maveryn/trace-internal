# `task_tables_relation_extremum_transfer_value`

## 1) Identity
1. Domain: `tables`
2. Task group: `relation`
3. Task id: `task_tables_relation_extremum_transfer_value`
4. Objective: identify the row with the requested source-column extremum and return its value in another target column.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `argmax_transfer`
   - `argmin_transfer`
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
   - the prompt names one source numeric column and one distinct target numeric column,
   - the answer is the target-column value from the unique row that wins the requested source-column extremum.
6. Generation guarantees:
   - the source and target columns are always distinct,
   - the source-column values are unique across rows, so the extremum row is unique,
   - evidence is exactly two bbox witnesses ordered as `[source extremum cell, target value cell]`.

## 3) Prompt contract
1. Bundle: `tables_relation_v1`
2. `task_family_key`: `styled_table_relation`
3. `task_key`: `extremum_transfer_value_query`
4. `task_variant_key`: `argmax_transfer|argmin_transfer`
5. Required slots:
   - task-family: `object_description`
   - task-variant: `query_source_column`, `query_target_column`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/tables/relation.yaml`,
   - deterministic bundle selection from `prompts/tables/relation/tables_relation_v1.json`.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt-facing answer is the exact integer target-column value; prompt-facing evidence is the ordered pair `[source extremum cell, target value cell]`.

## 4) Evidence + trace contract
1. Prompt-facing evidence is one `bbox_set` containing exactly two queried value-cell bboxes in this fixed order:
   - source extremum cell,
   - transferred target value cell.
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
   - full row labels, column headers, and table values
   - source-column and target-column metadata
   - winning row label/index
   - source extremum value and transferred target value
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
5. Review overlays rely on the ordered `[source extremum cell, target value cell]` bboxes recorded in trace, not OCR from pixels.

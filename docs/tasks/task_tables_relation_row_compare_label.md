# `task_tables_relation_row_compare_label`

## 1) Identity
1. Domain: `tables`
2. Task group: `relation`
3. Task id: `task_tables_relation_row_compare_label`
4. Objective: return which of two named rows has the higher or lower value in one queried numeric column.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `higher_of_two_rows`
   - `lower_of_two_rows`
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
   - the query names exactly two visible row labels and one visible numeric column,
   - the answer is the winning row label for the requested higher/lower comparison.
6. Generation guarantees:
   - the queried row pair is ordered and recorded in trace,
   - the compared values in the queried column are always distinct,
   - evidence is exactly two bbox witnesses for the compared value cells in prompt order.

## 3) Prompt contract
1. Bundle: `tables_relation_v1`
2. `task_family_key`: `styled_table_relation`
3. `task_key`: `row_compare_label_query`
4. `task_variant_key`: `higher_of_two_rows|lower_of_two_rows`
5. Required slots:
   - task-family: `object_description`
   - task-variant: `query_row_label_a`, `query_row_label_b`, `query_column`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/tables/relation.yaml`,
   - deterministic bundle selection from `prompts/tables/relation/tables_relation_v1.json`.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt-facing answer is the winning row label; prompt-facing evidence is the ordered pair of compared value-cell bboxes.

## 4) Evidence + trace contract
1. Prompt-facing evidence is one `bbox_set` containing exactly two queried value-cell bboxes in prompt order.
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
   - queried column and ordered queried-row metadata
   - answer row label/value
   - supporting cell ids in prompt order
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
5. Review overlays rely on the ordered compared-cell bboxes recorded in trace, not OCR from pixels.

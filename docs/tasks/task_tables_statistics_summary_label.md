# `task_tables_statistics_summary_label`

## 1) Identity
1. Domain: `tables`
2. Task group: `statistics`
3. Task id: `task_tables_statistics_summary_label`
4. Objective: return the row label that wins under one supported table-summary objective.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `argmax`
   - `argmin`
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
   - column variants query one numeric column,
   - row-summary variants compare row totals across the numeric columns,
   - the answer is the visible row name with the unique winning statistic under the selected variant.
6. Generation guarantees:
   - column variants construct a queried column with a unique winner by construction,
   - row-summary variants construct unique row totals by construction,
   - row labels are sampled from the vendored short-name manifest used by charts,
   - numeric cell values use the default integer range `1..32`,
   - evidence is exactly one bbox for the decisive numeric cell on column variants and one bbox for the supporting winning-row region on row-summary variants.

## 3) Prompt contract
1. Bundle: `tables_statistics_v1`
2. `task_family_key`: `styled_table_statistics`
3. `task_key`: `summary_label_query` for column variants and `summary_row_label_query` for row-summary variants
4. `task_variant_key`: one of `argmax|argmin|row_sum_argmax|row_sum_argmin`
5. Required slots:
   - task-family: `object_description`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/tables/statistics.yaml`,
   - deterministic bundle selection from `prompts/tables/statistics/tables_statistics_v1.json`.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt-facing answer is the visible row name string; prompt-facing evidence is the bbox of the supporting value cell on column variants or the supporting winning-row region on row-summary variants.

## 4) Evidence + trace contract
1. Prompt-facing evidence is one `bbox_set` containing exactly one supporting numeric cell bbox on column variants or one supporting row-region bbox on row-summary variants.
2. `projected_evidence` includes:
   - `bbox_set`
3. `scene_ir.entities` stores one entity per table cell with:
   - `cell_role`
   - `row_index`
   - `column_index`
   - row/column labels when applicable
   - rendered cell/text geometry
4. `execution_trace` records:
   - `task_variant`
   - `scene_variant`
   - row labels, column headers, and full numeric table values
   - queried column on column variants
   - answer row label and decisive cell id on column variants
   - answer row label and supporting row label on row-summary variants
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
5. Review overlays rely on the recorded decisive cell bbox or winning-row region bbox in trace, not OCR from pixels.

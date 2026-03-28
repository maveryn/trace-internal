# `task_tables_ranking_label`

## 1) Identity
1. Domain: `tables`
2. Task group: `ranking`
3. Task id: `task_tables_ranking_label`
4. Objective: return the row label whose value is kth highest or kth lowest in one queried numeric column.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `kth_highest_in_column`
   - `kth_lowest_in_column`
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
   - the query names one visible numeric column and an internal rank `k` currently sampled from `2..4`,
   - the answer is the row label whose value has the requested kth highest or kth lowest position in that column.
6. Generation guarantees:
   - the queried column values are unique across all rows,
   - the queried rank is always at least `2`, so this task is not a duplicate of plain `argmax` or `argmin`,
   - evidence is exactly one bbox witness for the supporting queried-column region.

## 3) Prompt contract
1. Bundle: `tables_ranking_v1`
2. `task_family_key`: `styled_table_ranking`
3. `task_key`: `kth_label_query`
4. `task_variant_key`: `kth_highest_in_column|kth_lowest_in_column`
5. Required slots:
   - task-family: `object_description`
   - task-variant: `query_column`, `query_rank`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/tables/ranking.yaml`,
   - deterministic bundle selection from `prompts/tables/ranking/tables_ranking_v1.json`.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt-facing answer is the row label at the requested rank; prompt-facing evidence is the bbox of the supporting queried-column region.

## 4) Evidence + trace contract
1. Prompt-facing evidence is one `bbox_set` containing exactly one bbox for the queried-column region.
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
   - queried column and queried rank
   - answer row label/index and answer value
   - full row labels, column headers, and numeric table values
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
5. Review overlays rely on the queried-column region bbox recorded in trace, not OCR from pixels.

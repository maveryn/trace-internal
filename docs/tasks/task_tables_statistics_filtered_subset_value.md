# `task_tables_statistics_filtered_subset_value`

## 1) Identity
1. Domain: `tables`
2. Task group: `statistics`
3. Task id: `task_tables_statistics_filtered_subset_value`
4. Objective: aggregate one target numeric column over the rows selected by a filter condition on another numeric column.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `filtered_column_sum`
   - `filtered_column_mean`
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
   - one queried filter column and one distinct queried target column are named in the prompt,
   - the answer is the requested integer aggregation over the target-column values from only the rows selected by the filter.
6. Generation guarantees:
   - the selected-row count is always at least `1`,
   - the internal filter subtype is one of `above_threshold|below_threshold|in_interval`,
   - the filter and target columns are always distinct,
   - `filtered_column_mean` is constructed so the selected target-column values average to an integer,
   - evidence is the ordered set of `[filter cell, target cell]` pairs for every selected row, in top-to-bottom row order.

## 3) Prompt contract
1. Bundle: `tables_statistics_v1`
2. `task_family_key`: `styled_table_statistics`
3. `task_key`: `filtered_subset_value_query`
4. `task_variant_key`: `filtered_column_sum|filtered_column_mean`
5. Required slots:
   - task-family: `object_description`
   - task-variant: `query_filter_column`, `query_target_column`, `filter_condition`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/tables/statistics.yaml`,
   - deterministic bundle selection from `prompts/tables/statistics/tables_statistics_v1.json`.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt-facing answer is the exact integer filtered summary value; prompt-facing evidence is the ordered bbox array of supporting `[filter cell, target cell]` pairs.

## 4) Evidence + trace contract
1. Prompt-facing evidence is a `bbox_set` containing one ordered pair `[filter cell, target cell]` for every selected row.
2. Global evidence order is top-to-bottom row order.
3. Within each selected row, the filter-column cell comes first and the target-column cell comes second.
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
   - full row labels, column headers, and table values
   - filter subtype plus threshold/interval parameters
   - filter column and target column metadata
   - selected row indices/labels
   - supporting cell ids in evidence order
   - row/column count ranges

## 5) Visual policy
1. Background and post-image noise use the merged tables-domain visual defaults from `configs/domains/tables/base.yaml`.
2. V1 tables use clean light solid backgrounds only.
3. The 4 active `scene_variant` styles change grid/shading/frame presentation while preserving the same cell geometry contract.
4. Numeric values are printed directly in cells for all active table styles.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. `task_variant` and `scene_variant` are sampled independently at the policy level; the internal filter subtype is also deterministic from seed.
3. Answers and evidence come from the same generated table.
4. No semantic auto-relaxation.
5. Review overlays rely on the ordered filter/target cell-pair bboxes recorded in trace, not OCR from pixels.

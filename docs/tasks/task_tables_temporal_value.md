# `task_tables_temporal_value`

## 1) Identity
1. Domain: `tables`
2. Task group: `temporal`
3. Task id: `task_tables_temporal_value`
4. Objective: answer one year-conditioned numeric question for a visible row in a table whose numeric columns are chronological years.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `value_at_year`
   - `delta_between_years`
   - `absolute_difference_between_years`
   - `sum_over_year_interval`
   - `mean_over_year_interval`
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
   - `3..5` year columns in chronological order by default,
   - `5..10` data rows by default,
   - row labels are short visible person-style names,
   - the prompt always names one visible row and one year or year interval.
6. Generation guarantees:
   - year headers are contiguous visible years,
   - `delta_between_years` and `absolute_difference_between_years` always use two distinct years,
   - interval variants always use one contiguous inclusive year range,
   - `mean_over_year_interval` is constructed so the interval mean is an exact integer.

## 3) Prompt contract
1. Bundle: `tables_temporal_v1`
2. `task_family_key`: `styled_table_temporal`
3. `task_key`: `temporal_value_query`
4. `task_variant_key`: `value_at_year|delta_between_years|absolute_difference_between_years|sum_over_year_interval|mean_over_year_interval`
5. Required slots:
   - task-family: `object_description`
   - task-variant `value_at_year`: `query_row_label`, `query_year`
   - task-variant `delta_between_years|absolute_difference_between_years|sum_over_year_interval|mean_over_year_interval`: `query_row_label`, `query_year_start`, `query_year_end`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/tables/temporal.yaml`,
   - deterministic bundle selection from `prompts/tables/temporal/tables_temporal_v1.json`.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt-facing answer is the exact integer temporal result; prompt-facing evidence is the ordered queried year-cell bbox list.

## 4) Evidence + trace contract
1. Prompt-facing evidence is one `bbox_set`:
   - `value_at_year`: exactly one queried year-cell bbox,
   - `delta_between_years|absolute_difference_between_years`: exactly two queried year-cell bboxes ordered as `[start year, end year]`,
   - `sum_over_year_interval|mean_over_year_interval`: the ordered queried year-cell bboxes from the start year through the end year.
2. `witness_symbolic` stores the same ordered `bbox_set` used for the public evidence contract.
3. `projected_evidence` includes:
   - `bbox_set`
4. `scene_ir.entities` stores one entity per table cell with:
   - `cell_role`
   - `row_index`
   - `column_index`
   - row/column labels when applicable
   - rendered cell/text geometry
5. `render_map` includes:
   - `column_region_bboxes_px`
   - `row_region_bboxes_px`
   - `row_label_bboxes_px`
   - `header_bboxes_px`
   - `cell_bboxes_px`
6. `execution_trace` records:
   - `task_variant`
   - `scene_variant`
   - full row labels, year headers, and table values
   - queried row label/index
   - queried years and queried cell metadata
   - supporting cell ids in evidence order
   - row/column count ranges
   - final integer answer

## 5) Visual policy
1. Background and post-image noise use the merged tables-domain visual defaults from `configs/domains/tables/base.yaml`.
2. V1 tables use clean light solid backgrounds only.
3. The 4 active `scene_variant` styles change grid/shading/frame presentation while preserving the same cell geometry contract.
4. Numeric values remain printed directly in cells for all active table styles.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. `task_variant` and `scene_variant` are sampled independently at the policy level.
3. Answers and evidence come from the same generated table.
4. No semantic auto-relaxation.
5. Review overlays rely on the ordered queried year-cell bboxes recorded in trace, not OCR from pixels.

# `task_tables_counting_value_count`

## 1) Identity
1. Domain: `tables`
2. Task group: `counting`
3. Task id: `task_tables_counting_value_count`
4. Objective: count how many rows satisfy one queried numeric-column predicate.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `above_threshold`
   - `below_threshold`
   - `in_interval`
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
   - the query names one numeric column and one threshold/interval predicate,
   - the answer is the number of matching rows.
6. Generation guarantees:
   - the answer count is sampled from the feasible `0..row_count` support before the queried column is constructed,
   - `above_threshold` and `below_threshold` use strict inequalities,
   - `in_interval` uses an inclusive interval `[min, max]`,
   - evidence is the ordered set of supporting value-cell bboxes in top-to-bottom row order, or `[]` when no row matches.

## 3) Prompt contract
1. Bundle: `tables_counting_v1`
2. `task_family_key`: `styled_table_counting`
3. `task_key`: `value_count_query`
4. `task_variant_key`: one of `above_threshold|below_threshold|in_interval`
5. Required slots:
   - task-family: `object_description`
   - task-variant:
     - `above_threshold` / `below_threshold`: `query_column`, `threshold_value`
     - `in_interval`: `query_column`, `interval_min`, `interval_max`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/tables/counting.yaml`,
   - deterministic bundle selection from `prompts/tables/counting/tables_counting_v1.json`.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt-facing answer is the exact integer count; prompt-facing evidence is the bbox array of all matching value cells.

## 4) Evidence + trace contract
1. Prompt-facing evidence is a `bbox_set` containing one bbox per matching queried-column value cell in top-to-bottom row order.
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
   - queried column plus threshold/interval parameters
   - answer count
   - matching row labels/indices
   - supporting cell ids
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
5. Review overlays rely on the supporting value-cell bboxes recorded in trace, not OCR from pixels.

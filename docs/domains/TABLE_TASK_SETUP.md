# Table Task Setup

This document defines the concrete v1 tables-domain contract.

## 1) Domain shape
1. `domain = tables`
2. The active task groups are `statistics`, `counting`, `readout`, and `relation`.
3. The current active table tasks are:
   - `task_tables_statistics_summary_label`
   - `task_tables_statistics_summary_value`
   - `task_tables_statistics_row_summary_value`
   - `task_tables_counting_value_count`
   - `task_tables_counting_column_pair_count`
   - `task_tables_readout_subset_value`
   - `task_tables_relation_row_compare_label`

## 2) Active task contracts
1. `task_tables_statistics_summary_label`
   - `task_variant`: `argmax|argmin`
   - `scene_variant`: `spreadsheet|zebra|ledger|card_table`
   - `answer_gt.type`: `string`
   - `evidence_gt.type`: `bbox_set`
2. `task_tables_statistics_summary_value`
   - `task_variant`: `column_sum|column_mean|column_median`
   - `scene_variant`: `spreadsheet|zebra|ledger|card_table`
   - `answer_gt.type`: `integer`
   - `evidence_gt.type`: `bbox_set`
3. `task_tables_counting_value_count`
   - `task_variant`: `above_threshold|below_threshold|in_interval`
   - `scene_variant`: `spreadsheet|zebra|ledger|card_table`
   - `answer_gt.type`: `integer`
   - `evidence_gt.type`: `bbox_set`
4. `task_tables_counting_column_pair_count`
   - `task_variant`: `col_a_gt_col_b|col_a_lt_col_b`
   - `scene_variant`: `spreadsheet|zebra|ledger|card_table`
   - `answer_gt.type`: `integer`
   - `evidence_gt.type`: `bbox_set`
5. `task_tables_statistics_row_summary_value`
   - `task_variant`: `row_sum|row_mean`
   - `scene_variant`: `spreadsheet|zebra|ledger|card_table`
   - `answer_gt.type`: `integer`
   - `evidence_gt.type`: `bbox_set`
6. `task_tables_readout_subset_value`
   - `task_variant`: `cell_lookup|cell_sum_two|cell_difference_two_abs`
   - `scene_variant`: `spreadsheet|zebra|ledger|card_table`
   - `answer_gt.type`: `integer`
   - `evidence_gt.type`: `bbox_set`
7. `task_tables_relation_row_compare_label`
   - `task_variant`: `higher_of_two_rows|lower_of_two_rows`
   - `scene_variant`: `spreadsheet|zebra|ledger|card_table`
   - `answer_gt.type`: `string`
   - `evidence_gt.type`: `bbox_set`

## 3) Table semantics
1. One table per image.
2. Tables use one leftmost `Name` column with short visible person-style row labels.
3. Tables use `3..5` numeric columns by default.
4. Tables use `5..10` data rows by default.
5. Summary-label tasks query one numeric column and ask which row has the highest or lowest value in that column.
6. Summary-value tasks query one numeric column and ask for a numeric summary over that column.
7. Row-summary-value tasks query one visible row label and ask for a numeric summary over that row's numeric cells.
8. Counting tasks query one numeric column plus a threshold/interval predicate and count matching rows.
9. Column-pair counting tasks query two visible numeric columns and count rows where one strict column comparison holds.
10. Readout tasks query one visible cell or an ordered pair of visible cells and ask for an exact integer readout, sum, or absolute difference.
11. Relation tasks query two visible row labels plus one numeric column and ask which row has the higher or lower value in that column.
12. Row-name answers are visible row-name strings from the table, not option letters.

## 4) Evidence policy
1. Tables use one fixed evidence type from the start: `bbox_set`.
2. Table evidence boxes should mark the minimal supporting table region(s).
3. For `task_tables_statistics_summary_label`, evidence is exactly one bbox for the decisive numeric value cell.
4. For `task_tables_statistics_summary_value`, evidence is exactly one bbox for the supporting queried-column data region.
5. For `task_tables_statistics_row_summary_value`, evidence is exactly one bbox for the supporting queried-row data region.
6. For `task_tables_counting_value_count`, evidence is the ordered set of supporting queried-column value-cell bboxes in top-to-bottom row order.
7. For `task_tables_counting_column_pair_count`, evidence is the ordered set of compared queried-column value-cell pairs for every matching row, in top-to-bottom row order and prompt column order within each row.
8. For `task_tables_readout_subset_value`, evidence is one queried value-cell bbox for `cell_lookup` and an ordered pair of queried value-cell bboxes for the two-cell arithmetic variants.
9. For `task_tables_relation_row_compare_label`, evidence is the ordered pair of compared queried-column value-cell bboxes.
10. Prompt wording should explicitly say whether the evidence is a supporting value cell, a set of matching value cells, a supporting row region, a supporting column region, or an ordered queried-cell pair.

## 5) Visual policy
1. Table scenes use light solid backgrounds only in v1.
2. Scene variants change table styling, not table semantics:
   - `spreadsheet`: full grid and shaded header row
   - `zebra`: alternating row shading plus full grid
   - `ledger`: strong horizontal rules with minimal vertical separators
   - `card_table`: rounded outer frame with softer card-like styling
3. Numeric values remain printed directly in cells for all active table variants.

## 6) Label sources
1. Row labels reuse the vendored short-name manifest already used by chart legends.
2. The canonical shared loader now lives in `trace/tasks/shared/name_assets.py`.
3. The current short-name manifest is `assets/charts/series_legend_names_random_name_2to4.txt`.

## 7) Prompt policy
1. Prompt bundles:
   - `tables_statistics_v1`
   - `tables_counting_v1`
   - `tables_readout_v1`
   - `tables_relation_v1`
2. Task family keys:
   - `styled_table_statistics`
   - `styled_table_counting`
   - `styled_table_readout`
   - `styled_table_relation`
3. Active task keys:
   - `summary_label_query`
   - `summary_value_query`
   - `summary_row_value_query`
   - `value_count_query`
   - `column_pair_count_query`
   - `subset_value_query`
   - `row_compare_label_query`
4. Prompts must name the queried numeric column explicitly for column-summary/counting/relation tasks, the queried row explicitly for row-summary tasks, and the queried row+column cell coordinates explicitly for each readout query cell.
5. Prompts must describe the evidence as the bbox of the supporting value cell, the ordered set of matching value cells, the supporting row region, the supporting column region, or the ordered queried-cell pair, depending on the task.

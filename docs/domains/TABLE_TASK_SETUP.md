# Table Task Setup

This document defines the concrete v1 tables-domain contract.

## 1) Domain shape
1. `domain = tables`
2. The active task groups are `statistics`, `counting`, `readout`, `relation`, `ranking`, and `temporal`.
3. The current active table tasks are:
   - `task_tables_statistics_summary_label`
   - `task_tables_statistics_summary_value`
   - `task_tables_statistics_filtered_subset_value`
   - `task_tables_statistics_filtered_subset_label`
   - `task_tables_counting_value_count`
   - `task_tables_readout_subset_value`
   - `task_tables_relation_row_compare_label`
   - `task_tables_relation_extremum_transfer_value`
   - `task_tables_ranking_label`
   - `task_tables_temporal_value`

## 2) Active task contracts
1. `task_tables_statistics_summary_label`
   - `task_variant`: `argmax|argmin|row_sum_argmax|row_sum_argmin`
   - `scene_variant`: `spreadsheet|zebra|ledger|card_table`
   - `answer_gt.type`: `string`
   - `evidence_gt.type`: `bbox_set`
2. `task_tables_statistics_summary_value`
   - `task_variant`: `column_sum|column_mean|column_median|row_sum|row_mean|table_sum|table_mean`
   - `scene_variant`: `spreadsheet|zebra|ledger|card_table`
   - `answer_gt.type`: `integer`
   - `evidence_gt.type`: `bbox_set`
3. `task_tables_statistics_filtered_subset_value`
   - `task_variant`: `filtered_column_sum|filtered_column_mean`
   - `scene_variant`: `spreadsheet|zebra|ledger|card_table`
   - `answer_gt.type`: `integer`
   - `evidence_gt.type`: `bbox_set`
4. `task_tables_statistics_filtered_subset_label`
   - `task_variant`: `filtered_argmax|filtered_argmin`
   - `scene_variant`: `spreadsheet|zebra|ledger|card_table`
   - `answer_gt.type`: `string`
   - `evidence_gt.type`: `bbox_set`
5. `task_tables_counting_value_count`
   - `task_variant`: `above_threshold|below_threshold|in_interval|col_a_gt_col_b|col_a_lt_col_b`
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
8. `task_tables_relation_extremum_transfer_value`
   - `task_variant`: `argmax_transfer|argmin_transfer`
   - `scene_variant`: `spreadsheet|zebra|ledger|card_table`
   - `answer_gt.type`: `integer`
   - `evidence_gt.type`: `bbox_set`
9. `task_tables_ranking_label`
   - `task_variant`: `kth_highest_in_column|kth_lowest_in_column`
   - `scene_variant`: `spreadsheet|zebra|ledger|card_table`
   - `answer_gt.type`: `string`
   - `evidence_gt.type`: `bbox_set`
10. `task_tables_temporal_value`
   - `task_variant`: `value_at_year|delta_between_years|absolute_difference_between_years|sum_over_year_interval|mean_over_year_interval`
   - `scene_variant`: `spreadsheet|zebra|ledger|card_table`
   - `answer_gt.type`: `integer`
   - `evidence_gt.type`: `bbox_set`

## 3) Table semantics
1. One table per image.
2. Tables use one leftmost `Name` column with short visible person-style row labels.
3. Tables use `3..5` numeric columns by default.
4. Tables use `5..10` data rows by default.
5. Summary-label tasks query either one numeric column (`argmax|argmin`) or the row totals across numeric columns (`row_sum_argmax|row_sum_argmin`) and ask which row wins.
6. Summary-value tasks query either one numeric column (`column_*`), one visible row label (`row_*`), or the full numeric table (`table_*`) and ask for the requested integer summary over that subset.
7. Filtered-subset statistics value tasks query one filter column plus one distinct target column and aggregate the target values over only the rows that satisfy the filter condition.
8. Filtered-subset statistics label tasks query one filter column plus one distinct target column, keep only the rows that satisfy the filter condition, and ask which remaining row has the requested target-column extremum.
9. Counting tasks either query one numeric column plus a threshold/interval predicate or query two visible numeric columns with a strict row-wise comparison, and count matching rows.
10. Readout tasks query one visible cell or an ordered pair of visible cells and ask for an exact integer readout, sum, or absolute difference.
11. Relation tasks either compare two visible row labels in one numeric column or transfer from the extremum row of one source column to another target-column value in that same row.
12. Ranking tasks query one numeric column plus an internal rank `k` (currently `2..4`) and ask which row is the kth highest or kth lowest in that column.
13. Temporal tasks use the same single-table layout, but the numeric columns are year headers in chronological order rather than metric headers and the prompt always names one visible row plus one year or year interval.
14. Row-name answers are visible row-name strings from the table, not option letters.

## 4) Evidence policy
1. Tables use one fixed evidence type from the start: `bbox_set`.
2. Table evidence boxes should mark the minimal supporting table region(s).
3. For `task_tables_statistics_summary_label`, column variants use exactly one bbox for the decisive numeric value cell and row-summary variants use exactly one bbox for the supporting winning-row data region.
4. For `task_tables_statistics_summary_value`, column variants use exactly one bbox for the supporting queried-column data region, row variants use exactly one bbox for the supporting queried-row data region, and table variants use exactly one bbox for the supporting full numeric-table region.
5. For `task_tables_statistics_filtered_subset_value`, evidence is the ordered set of `[filter cell, target cell]` value-cell pairs for every selected row, in top-to-bottom row order.
6. For `task_tables_statistics_filtered_subset_label`, evidence is the ordered set of `[filter cell, target cell]` value-cell pairs for every selected row, in top-to-bottom row order.
7. For `task_tables_counting_value_count`, single-column variants use the ordered set of supporting queried-column value-cell bboxes in top-to-bottom row order, while pairwise variants use the ordered set of compared queried-column value-cell pairs for every matching row in top-to-bottom row order and prompt column order within each row.
8. For `task_tables_readout_subset_value`, evidence is one queried value-cell bbox for `cell_lookup` and an ordered pair of queried value-cell bboxes for the two-cell arithmetic variants.
9. For `task_tables_relation_row_compare_label`, evidence is the ordered pair of compared queried-column value-cell bboxes.
10. For `task_tables_relation_extremum_transfer_value`, evidence is the ordered pair `[source extremum cell, transferred target cell]`.
11. For `task_tables_ranking_label`, evidence is exactly one bbox for the supporting queried-column region because the ranking witness depends on the ordered values across the full column.
12. For `task_tables_temporal_value`, `value_at_year` uses exactly one queried year-cell bbox, the two-year variants use exactly two queried year-cell bboxes ordered as `[start year, end year]`, and the interval variants use the ordered queried year-cell bboxes from the start year through the end year.
13. Prompt wording should explicitly say whether the evidence is a supporting value cell, a set of matching value cells, a supporting row region, a supporting column region, a full numeric-table region, or an ordered queried-cell pair.

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
   - `tables_ranking_v1`
   - `tables_temporal_v1`
2. Task family keys:
   - `styled_table_statistics`
   - `styled_table_counting`
   - `styled_table_readout`
   - `styled_table_relation`
   - `styled_table_ranking`
   - `styled_table_temporal`
3. Active task keys:
   - `summary_label_query`
   - `summary_row_label_query`
   - `summary_value_query`
   - `summary_row_value_query`
   - `summary_table_value_query`
   - `filtered_subset_value_query`
   - `filtered_subset_label_query`
   - `value_count_query`
   - `column_pair_count_query`
   - `subset_value_query`
   - `row_compare_label_query`
   - `extremum_transfer_value_query`
   - `kth_label_query`
   - `temporal_value_query`
4. Prompts must name the queried numeric column explicitly for column-summary/counting/relation/ranking tasks, the queried row explicitly for row-summary-value tasks, describe the whole numeric table explicitly for whole-table summary variants, name the filter and target columns explicitly for filtered-subset tasks, name the queried row+column cell coordinates explicitly for each readout query cell, and name the queried row plus the queried year or year interval explicitly for temporal tasks.
5. Prompts must describe the evidence as the bbox of the supporting value cell, the ordered set of matching value cells, the supporting row region, the supporting column region, the full numeric-table region, or the ordered queried year-cell set, depending on the task.

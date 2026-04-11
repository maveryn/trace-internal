# Tables Task-Unit Audit

Task-unit audit for `domain=tables` using `docs/workflows/TASK_UNIT_AUDIT.md`.

## Domain summary
1. The tables domain is strong overall: every task depends on real table reading, and the shared table grammar still supports a good spread of grounded query types.
2. Most table tasks are healthy benchmark units because they keep one stable table scaffold and one stable witness semantics.
3. The main task-unit pressure points are:
   - `task_tables_counting_value_count`, which mixes single-column threshold counting with pairwise column-comparison counting,
   - `task_tables_statistics_summary_value`, which mixes column, row, and whole-table aggregation families under one id.
4. Recommended domain outcome:
   - `Keep`: `8`
   - `Split`: `2`
   - `Merge`: `0`
   - `Retire`: `0`

## Task findings

### `task_tables_counting_value_count`
- Outcome: `Split`
- Why: this task currently mixes two different counting families:
  - single-column threshold / interval counting (`above_threshold|below_threshold|in_interval`)
  - pairwise row-wise column comparison counting (`col_a_gt_col_b|col_a_lt_col_b`)
- Scene variety: moderate; the table scaffold is stable, but the witness semantics differ materially across the two halves.
- Query variety: strong, but split across different grounding jobs.
- Grounding necessity: strong in both halves, but the model alternates between:
  - testing one value against a threshold or interval,
  - comparing two cells within each row.
- Evidence fit: mixed; one-cell-per-row evidence versus ordered cell-pair evidence do not feel like one uniform task unit.
- Follow-up:
  1. Keep the single-column threshold / interval variants together as one counting task.
  2. Move `col_a_gt_col_b|col_a_lt_col_b` into a separate row-wise column-comparison count task.

### `task_tables_ranking_label`
- Outcome: `Keep`
- Why: one coherent kth-rank-in-column family.
- Scene variety: moderate; one stable table scaffold with varying column choice, row set, and queried rank.
- Query variety: modest but coherent (`kth_highest_in_column|kth_lowest_in_column`).
- Grounding necessity: strong; the solver must order the values in the named column.
- Evidence fit: acceptable; the queried-column region is a broad but stable witness.
- Follow-up: none required now.

### `task_tables_readout_subset_value`
- Outcome: `Keep`
- Why: one coherent direct-readout / local-two-cell-arithmetic family over explicitly named cells.
- Scene variety: moderate; stable table scaffold with varying rows/columns and local arithmetic.
- Query variety: moderate (`cell_lookup|cell_sum_two|cell_difference_two_abs`) but still one local-readout family.
- Grounding necessity: strong; the solver must locate the named cells and read their visible values.
- Evidence fit: good; the queried cell or ordered queried-cell pair is the natural witness.
- Follow-up: none required now.

### `task_tables_relation_extremum_transfer_value`
- Outcome: `Keep`
- Why: one coherent “find extremum row in source column, then transfer target-column value” family.
- Scene variety: moderate; one stable table scaffold with varying source/target columns.
- Query variety: modest but coherent (`argmax_transfer|argmin_transfer`).
- Grounding necessity: strong; the model must identify the extremum row and then transfer across columns.
- Evidence fit: good; the ordered `[source extremum cell, target value cell]` pair is the natural witness.
- Follow-up: none required now.

### `task_tables_relation_row_compare_label`
- Outcome: `Keep`
- Why: one coherent two-row comparison family.
- Scene variety: moderate; stable table scaffold with varying queried rows/column.
- Query variety: modest but coherent (`higher_of_two_rows|lower_of_two_rows`).
- Grounding necessity: strong; the solver must locate exactly two rows and compare their values in one column.
- Evidence fit: good; the ordered compared-cell pair is the natural witness.
- Follow-up: none required now.

### `task_tables_statistics_filtered_subset_label`
- Outcome: `Keep`
- Why: one coherent filtered-subset winner-selection family.
- Scene variety: moderate; stable table scaffold with varying filter conditions and target columns.
- Query variety: moderate (`filtered_argmax|filtered_argmin`) within one stable filtered-extremum family.
- Grounding necessity: strong; the solver must first filter rows, then compare the target-column values among the selected rows.
- Evidence fit: good; ordered `[filter cell, target cell]` pairs per selected row are a consistent witness.
- Follow-up: none required now.

### `task_tables_statistics_filtered_subset_value`
- Outcome: `Keep`
- Why: one coherent filtered-subset aggregation family.
- Scene variety: moderate; stable table scaffold with varying filter conditions and target columns.
- Query variety: modest but coherent (`filtered_column_sum|filtered_column_mean`).
- Grounding necessity: strong; the solver must identify the selected rows and aggregate the target values.
- Evidence fit: good; ordered `[filter cell, target cell]` pairs per selected row are a consistent witness.
- Follow-up: none required now.

### `task_tables_statistics_summary_label`
- Outcome: `Keep`
- Why: this is broad, but it still feels like one coherent “which row wins this summary objective?” family.
- Scene variety: moderate; the table scaffold stays fixed while the winning objective changes.
- Query variety: strong (`argmax|argmin|row_sum_argmax|row_sum_argmin`) but still unified by row-label selection.
- Grounding necessity: strong; the solver must identify the winning row under the stated statistic.
- Evidence fit: acceptable; decisive cell versus winning-row region differ somewhat, but both support the same row-winner semantics.
- Follow-up: watch this if more row-summary variants are added later.

### `task_tables_statistics_summary_value`
- Outcome: `Split`
- Why: this task currently mixes three different aggregation families:
  - column summaries (`column_sum|column_mean|column_median`)
  - row summaries (`row_sum|row_mean`)
  - whole-table summaries (`table_sum|table_mean`)
- Scene variety: high, but too mixed for one task unit under uniform sampling.
- Query variety: high, but spread across materially different support regions.
- Grounding necessity: strong throughout, but the witness semantics differ:
  - one column region,
  - one row region,
  - the full numeric table region.
- Evidence fit: mixed; column, row, and full-table region witnesses do not feel like one stable benchmark unit.
- Follow-up:
  1. Keep column-summary variants together.
  2. Keep row-summary variants together if we want a row-aggregation task.
  3. Move whole-table summaries into their own task if we keep them.

### `task_tables_temporal_value`
- Outcome: `Keep`
- Why: one coherent year-conditioned row-readout / row-aggregation family over chronological columns.
- Scene variety: moderate; stable table scaffold with visible year columns and one named row.
- Query variety: strong (`value_at_year|delta_between_years|absolute_difference_between_years|sum_over_year_interval|mean_over_year_interval`) but still one stable temporal-row family.
- Grounding necessity: strong; the solver must align the named row with the requested year or interval.
- Evidence fit: good; ordered queried year-cell bboxes are a consistent witness.
- Follow-up: none required now.

## Recommended next action
1. Leave the other tables tasks unchanged for now.
2. Treat `task_tables_counting_value_count` and `task_tables_statistics_summary_value` as the first concrete table split candidates.
3. Keep an eye on `task_tables_statistics_summary_label`, but it does not yet need a split.

# Table Task Setup

This document defines the concrete v1 tables-domain contract.

## 1) Domain shape
1. `domain = tables`
2. The first active task group is `statistics`.
3. The first active statistics tasks are:
   - `task_tables_statistics_summary_label`
   - `task_tables_statistics_summary_value`

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

## 3) Table semantics
1. One table per image.
2. Tables use one leftmost `Name` column with short visible person-style row labels.
3. Tables use `3..5` numeric columns by default.
4. Tables use `5..10` data rows by default.
5. Summary-label tasks query one numeric column and ask which row has the highest or lowest value in that column.
6. Summary-value tasks query one numeric column and ask for a numeric summary over that column.
7. Row-name answers are visible row-name strings from the table, not option letters.

## 4) Evidence policy
1. Tables use one fixed evidence type from the start: `bbox_set`.
2. Table evidence boxes should mark the minimal supporting table region(s).
3. For `task_tables_statistics_summary_label`, evidence is exactly one bbox for the decisive numeric value cell.
4. For `task_tables_statistics_summary_value`, evidence is exactly one bbox for the supporting queried-column data region.
5. Prompt wording should explicitly say whether the evidence is a supporting value cell or a supporting column region.

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
1. Prompt bundle: `tables_statistics_v1`
2. Task family key: `styled_table_statistics`
3. Active task keys:
   - `summary_label_query`
   - `summary_value_query`
4. Prompts must name the queried numeric column explicitly.
5. Prompts must describe the evidence as the bbox of the supporting value cell or supporting column region, depending on the task.

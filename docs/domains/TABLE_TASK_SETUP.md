# Table Task Setup

This document defines the first concrete tables-domain contract.

## 1) Domain shape
1. `domain = tables`
2. The first active task group is `statistics`.
3. The first active task is `task_tables_statistics_summary_label`.

## 2) First task contract
1. Task id: `task_tables_statistics_summary_label`
2. `task_variant` values:
   - `argmax`
   - `argmin`
3. `scene_variant` values:
   - `spreadsheet`
   - `zebra`
   - `ledger`
   - `card_table`
4. `answer_gt.type`: `string`
5. `evidence_gt.type`: `bbox_set`

## 3) Table semantics
1. One table per image.
2. Tables use one leftmost `Name` column with short visible person-style row labels.
3. Tables use `3..5` numeric columns by default.
4. Tables use `5..10` data rows by default.
5. The first task queries one numeric column and asks which row has the highest or lowest value in that column.
6. Answers are the visible row-name strings from the table, not option letters.

## 4) Evidence policy
1. Tables use one fixed evidence type from the start: `bbox_set`.
2. Table evidence boxes should mark the minimal supporting table region(s).
3. For `task_tables_statistics_summary_label`, evidence is exactly one bbox for the decisive numeric value cell.
4. Prompt wording should explicitly say that the evidence is the bbox of the supporting value cell.

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
3. Task key: `summary_label_query`
4. Prompts must name the queried numeric column explicitly.
5. Prompts must describe the evidence as the bbox of the supporting value cell.

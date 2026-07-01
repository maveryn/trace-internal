# Charts Post-Migration Checklist Issues

Audit date: 2026-06-29

Scope: `charts` domain only. This report records identified issues only.

Audit artifacts generated in this pass:

- `docs/domain-migration-report/charts/bbox_min_side_audit.json`
- `docs/domain-migration-report/charts/bbox_min_side_audit.md`
- `docs/domain-migration-report/charts/semantic_sampling_modulo_audit.md`
- `docs/domain-migration-report/charts/visual_candidate_modulo_audit.md`
- `docs/domain-migration-report/charts/prompt_concision_audit.md`
- `docs/domain-migration-report/charts/prompt_annotation_contracts/`
- `docs/domain-migration-report/charts/prompt_annotation_contracts_fixes/`

Commands run:

- `PYTHONPATH=. python -B scripts/generate_active_task_inventory.py --check`
- `PYTHONPATH=. python -B scripts/check_active_inventory_integrity.py --include-local-cache`
- `PYTHONPATH=. python -B scripts/audit_active_domain_surfaces.py`
- `PYTHONPATH=. python -B scripts/audit_review_bbox_min_side.py --review-root review/task-reviews --docs-root docs --domains charts --min-side-px 24 --out-json docs/domain-migration-report/charts/bbox_min_side_audit.json --out-md docs/domain-migration-report/charts/bbox_min_side_audit.md --fail-on-issue`
- `PYTHONPATH=. python -B scripts/audit_semantic_sampling_modulo.py --root trace/tasks/charts --root trace/core --output docs/domain-migration-report/charts/semantic_sampling_modulo_audit.md`
- `PYTHONPATH=. python -B scripts/audit_visual_candidate_modulo.py --root trace/tasks/charts --root trace/core --output docs/domain-migration-report/charts/visual_candidate_modulo_audit.md`
- `PYTHONPATH=. python -B scripts/audit_prompt_concision.py --tasks <180 active chart task ids> --query-id-coverage --samples-per-query-id 1 --include-all-prompts --output docs/domain-migration-report/charts/prompt_concision_audit.md --workers 4 --max-attempts 200 --max-total-samples-per-task 1024`
- `PYTHONPATH=. python -B scripts/audit_prompt_annotation_contracts.py --tasks <180 active chart task ids> --samples-per-query-id 1 --output-dir docs/domain-migration-report/charts/prompt_annotation_contracts --workers 1 --max-attempts 200 --max-total-samples-per-task 1024 --task-timeout-seconds 60 --progress`
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_charts_heatmap_tasks.py tests/test_charts_waterfall_tasks.py`
- `PYTHONPATH=. python -B scripts/run_task_review.py --tasks <34 affected heatmap/waterfall/bar_3d/candlestick/combo_mark/dumbbell/radar task ids> --mode full --out-root review/task-reviews --workers 4`
- `PYTHONPATH=. python -B scripts/run_task_review.py --tasks <25 affected bar_3d/candlestick/combo_mark/dumbbell/radar task ids> --mode inspection --out-root review/task-reviews --workers 4`
- `PYTHONPATH=. python -B scripts/audit_prompt_annotation_contracts.py --tasks <11 fixed annotation-contract task ids> --samples-per-query-id 1 --output-dir docs/domain-migration-report/charts/prompt_annotation_contracts_fixes --workers 1 --max-attempts 200 --max-total-samples-per-task 1024 --task-timeout-seconds 60`
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_cleanup_retired_task_audit_rows.py`
- `PYTHONPATH=. python -B scripts/cleanup_retired_task_audit_rows.py --domain charts --output-root review/feedback-cleanup`
- `PYTHONPATH=. python -B scripts/cleanup_retired_task_audit_rows.py --domain charts --output-root review/feedback-cleanup --apply`
- `PYTHONPATH=. python -B scripts/run_task_review.py --tasks <142 stale chart task ids> --mode full --out-root review/task-reviews --workers 4`
- `PYTHONPATH=. python -B scripts/run_task_review.py --tasks task_charts__error_interval__reference_exclusion_side_count --mode full --out-root review/task-reviews --count-per-query-id 300 --workers 4`
- Read-only checks over `review/task-reviews/charts`, `docs/tasks/charts`, and `review/feedback/review_feedback.sqlite`.

Notes:

- Active chart review folders currently cover `180` tasks across `42` scenes.
- Active review manifests have `calibration_baseline: v0` and matching task ids.
- Distribution reviews are present and passing for all `180` active chart task folders.
- Active chart review artifacts are current with source/config/prompt/task-doc inputs for all `42` chart scenes.
- Scene status files exist for all `42` chart scenes; `manual_code_audit_status.json`, `taxonomy_review_status.json`, and `migration_test_status.json` all have `passed: true`, and every `taxonomy_review_status.json` has `checklist.scalar_annotation_checked: true`.
- `scripts/check_active_inventory_integrity.py --include-local-cache` failed because of non-chart local cache/checkpoint artifacts under the repo tree. No chart-specific active-surface failure was found by `audit_active_domain_surfaces.py`.

## Open Issues

### CHARTS-009 - Review DB has no accepted solve-rate status for active chart tasks

Severity: followup

Category: calibration / review status

Scope:

- `review/feedback/review_feedback.sqlite`
- active `charts` tasks

Issue:

- Active chart task rows have no accepted solve-rate status.
- Current active-task DB counts:
  - `prompt_pass`: `180/180`
  - `image_pass`: `180/180`
  - `annotation_pass`: `180/180`
  - `distribution_pass`: `180/180`
  - `code_review_pass`: `180/180`
  - `taxonomy_review_pass`: `180/180`
  - `solve_rate_pass`: `0/180`

Supporting artifact:

- Read-only SQLite query over `review/feedback/review_feedback.sqlite`.

Follow-up fix:

- Do not run solve-rate as part of this report-only pass.
- After stale artifacts and required source/prompt/annotation issues are fixed, run current chart solve-rate calibration only when explicitly requested and update review app status for accepted tasks.

## Resolved

### CHARTS-006 - Chart task docs used compact one-line Program Contract sections

Severity: followup

Category: taxonomy/program docs

Resolved on: 2026-06-30

Scope:

- `docs/tasks/charts/**/*.md`
- `scripts/normalize_chart_program_contract_docs.py`
- `review/task-reviews/charts/**`

Original issue:

- All `180` chart task docs contained a `## Program Contract`, but the sections were compact one-line program expressions rather than the newer structured form that names candidate set, operands, operation, output binding, annotation witnesses, and query ids as separate reviewable fields.
- A strict structured-field scan flagged all `180` chart docs as missing those fields.

Fix:

- Added `scripts/normalize_chart_program_contract_docs.py`, an idempotent maintainer script for chart Program Contract doc sections.
- Normalized all `180` active chart task docs so each `## Program Contract` contains:
  - `Program:`
  - `Candidate set:`
  - `Operands:`
  - `Operation:`
  - `Output binding:`
  - `Annotation witnesses:`
  - `Query ids:`
- Preserved existing concrete program expressions, task ids, source paths, query ids, answer schemas, annotation schemas, annotation contracts, and query-detail tables.
- Refreshed chart task-review inspection artifacts and scene workbooks under `review/task-reviews/charts` for all `180` active chart tasks across `42` scenes. Distribution artifacts and solve-rate were not rerun.
- Reloaded all `42` chart scenes in the review app with `POST /api/reload/scene/charts/<scene_id>`.

Verification:

- `PYTHONPATH=. python -B scripts/normalize_chart_program_contract_docs.py --check` -> `chart task docs scanned: 180`, `docs requiring normalization: 0`.
- Independent structural scan over `docs/tasks/charts` -> `chart_task_docs 180`, `missing_required_labels 0`.
- `PYTHONPATH=. python -B scripts/generate_active_task_inventory.py --check` -> `docs/ACTIVE_TASK_INVENTORY.md is up to date`.
- `PYTHONPATH=. python -B scripts/check_active_inventory_integrity.py` -> `active inventory integrity OK`.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_chart_scene_primitives.py tests/test_charts_counting_tasks.py tests/test_charts_statistics_tasks.py tests/test_charts_distribution_tasks.py` -> `44 passed`.
- Review artifact counts after refresh: `180` chart task manifests and `42` chart scene manifests.
- Review app `GET /api/reload/status` after scene reloads returned `status=succeeded`, `in_progress=false`, `queued=false`, `stale=false`, and `stale_scenes=[]`.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -B scripts/check_active_inventory_integrity.py --include-local-cache` still reported Python `__pycache__` artifacts created by import/test paths; these are generated cache files and not chart source/inventory mismatches.

### CHARTS-007 - Chart visual modulo sites needed manual source triage

Severity: followup

Category: renderer-style / sampling

Resolved on: 2026-06-30

Scope:

- `trace/tasks/charts/**`
- `trace/tasks/charts/shared/**`
- `scripts/audit_semantic_sampling_modulo.py`
- `scripts/audit_visual_candidate_modulo.py`

Original issue:

- The modulo audits found no confirmed random candidate-selection refactor sites, but they did find chart visual/style modulo sites that still needed source review.
- The accepted rule is that modulo is allowed only for deterministic assignment from an already-sampled candidate set, such as cycling through a selected palette because there are more marks than colors.

Fix:

- Refactored the fallback guide-line style resolver in `trace/tasks/charts/shared/chart_scene_primitives.py` from seed modulo indexing to seeded support sampling through `uniform_choice` and `spawn_rng`.
- Classified reviewed chart palette, dash-pattern, neutral-fill, and repeated-category cycling sites in the modulo audit scripts as safe deterministic assignment from already-selected supports.
- Regenerated `docs/domain-migration-report/charts/semantic_sampling_modulo_audit.md` and `docs/domain-migration-report/charts/visual_candidate_modulo_audit.md`.

Verification:

- `docs/domain-migration-report/charts/semantic_sampling_modulo_audit.md` now reports `Needs refactor: 0` and `Needs manual review: 0`.
- `docs/domain-migration-report/charts/visual_candidate_modulo_audit.md` now reports `Random candidate selection needs refactor: 0`, `Sampling-time assignment needs review: 0`, and `Needs manual review: 0`.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_chart_scene_primitives.py tests/test_charts_counting_tasks.py tests/test_charts_statistics_tasks.py tests/test_charts_distribution_tasks.py` -> `44 passed`.
- No task-review regeneration was required because the changed code path is a fallback for unresolved chart primitive params; normal chart task render params already resolve guide-line style before primitive rendering.

### CHARTS-001 - Review artifacts are stale for most active charts scenes

Severity: blocking

Category: stale artifact/docs

Resolved on: 2026-06-29

Scope:

- `review/task-reviews/charts/*`
- Previously stale chart scenes: `annotated_series`, `area`, `boxplot`, `composition_panels`, `contour_density`, `curve_panels`, `dashboard`, `density_curve`, `error_interval`, `errorbar_series`, `hexbin_density`, `histogram`, `matrix`, `multiseries`, `parallel_coords`, `part_whole`, `pictogram`, `population_pyramid`, `radial_progress`, `radial_sankey`, `region_map`, `sankey`, `scatter_cluster`, `scatter_points`, `scatter_readout`, `scientific_axis_frame`, `single_series`, `style_legend`, `sunburst`, `surface_3d`, `table`, `treemap`, `uncertainty_band`, and `violin`.

Original issue:

- A freshness comparison found that `34` active chart scenes had review manifests older than source, prompt, config, or task-doc inputs.

Fix:

- Regenerated full task-review artifacts for the `142` active tasks in the stale chart scenes.
- All regenerated scenes wrote updated per-task review artifacts and combined `scene_review.xlsx` workbooks.
- One regenerated distribution check, `task_charts__error_interval__reference_exclusion_side_count`, initially missed the max-answer-frequency cap by one sample for `entirely_above_reference_count` (`0.34` observed vs `0.3333333333333333` threshold). The task was rerun with `--count-per-query-id 300`, after which the distribution review passed.
- Reloaded the review app index for all `34` regenerated chart scenes through `POST /api/reload/scene/charts/<scene_id>`.

Verification:

- Freshness scan after regeneration: `scenes=42`, `stale=0`.
- Distribution scan after regeneration: `distribution_total=180`, `distribution_bad=[]`.
- `PYTHONPATH=. python -B scripts/audit_review_bbox_min_side.py --review-root review/task-reviews --docs-root docs --domains charts --min-side-px 24 --out-json docs/domain-migration-report/charts/bbox_min_side_audit.json --out-md docs/domain-migration-report/charts/bbox_min_side_audit.md` reports `tasks=180 bbox_tasks=68 failures=0 invalid=0 missing=0`.
- Final review app reload status after `charts/violin`: `status=succeeded`, `stale=false`, `queued=false`, and `stale_scenes=[]`.

### CHARTS-008 - Review feedback DB contains retired chart task rows

Severity: required_fix

Category: review workspace state

Resolved on: 2026-06-29

Scope:

- `review/feedback/review_feedback.sqlite`
- retired `charts` task ids

Original issue:

- The review workspace contained `180` active chart task-review directories, but the feedback DB `task_audit` table contained `186` chart rows.
- Six rows were for retired task ids:
  - `task_charts__contour_density__nearest_region_option_label`
  - `task_charts__curve_panels__panel_point_threshold_count`
  - `task_charts__histogram__bin_count_between_values`
  - `task_charts__marker_map__marker_region_extremum_label`
  - `task_charts__marker_map__marker_region_threshold_count`
  - `task_charts__region_map__group_filtered_region_value`

Fix:

- Ran the retired-task review cleanup script for `domain=charts`.
- Applied cleanup deleted the six retired `task_audit` rows only.
- Wrote the cleanup receipt and SQLite backup under `review/feedback-cleanup/`.

Verification:

- Cleanup script test passed: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_cleanup_retired_task_audit_rows.py` -> `1 passed`.
- Applied cleanup receipt: `review/feedback-cleanup/retired_task_audit_cleanup_20260629T194041Z0000.json`.
- SQLite backup: `review/feedback-cleanup/review_feedback.sqlite.retired_task_audit_cleanup_20260629T194041Z0000.bak`.
- Post-cleanup dry-run receipt: `review/feedback-cleanup/retired_task_audit_cleanup_20260629T205929Z0000.json`.
- Current chart `task_audit` rows: `180`.
- Current retired/stale chart `task_audit` rows: `0`.

### CHARTS-002 - Size-encoding word-cloud annotations violate the 24 px bbox minimum

Severity: required_fix

Category: annotation / renderer-style

Resolved on: 2026-06-29

Scope:

- `task_charts__size_encoding__category_relative_size_count`
- `task_charts__size_encoding__filtered_item_extremum_label`
- `task_charts__size_encoding__global_item_extremum_category_label`

Original issue:

- Existing size-encoding review samples contained bbox-family annotation boxes with one side shorter than the required `24px`.
- The failures came from word-cloud/item text witnesses whose rendered text height could be below the bbox minimum.

Fix:

- Added centered post-layout bbox expansion for word-cloud item bboxes in `trace/tasks/charts/size_encoding/shared/rendering.py`.
- Expansion is clipped to the final content panel and uses a `24.5px` guard margin to avoid strict floating-point boundary failures.
- The drawn chart image and task answers are unchanged; only stored item/entity annotation bboxes are expanded.
- Added a focused size-encoding test assertion that all generated annotation boxes satisfy the `24px` minimum side.
- Regenerated all four `charts/size_encoding` task reviews and `scene_review.xlsx`.
- Reloaded the review app index for `charts/size_encoding`.

Verification:

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_charts_size_encoding_tasks.py` passed with `8 passed`.
- `PYTHONPATH=. python scripts/run_task_review.py --tasks task_charts__size_encoding__category_relative_size_count,task_charts__size_encoding__filtered_item_extremum_label,task_charts__size_encoding__global_item_extremum_category_label,task_charts__size_encoding__panel_category_extremum_panel_label --mode full --out-root review/task-reviews --workers 4` passed distribution review for all four tasks and regenerated the scene workbook.
- `PYTHONPATH=. python -B scripts/audit_review_bbox_min_side.py --review-root review/task-reviews --docs-root docs --domains charts --min-side-px 24 --out-json docs/domain-migration-report/charts/bbox_min_side_audit.json --out-md docs/domain-migration-report/charts/bbox_min_side_audit.md` now reports `tasks=180 bbox_tasks=68 failures=0 invalid=0 missing=0`.
- Focused size-encoding bbox parse reports:
  - `category_relative_size_count`: `pass`, `min=24.5`, `failures=0`, `invalid=0`
  - `filtered_item_extremum_label`: `pass`, `min=24.5`, `failures=0`, `invalid=0`
  - `global_item_extremum_category_label`: `pass`, `min=24.5`, `failures=0`, `invalid=0`
  - `panel_category_extremum_panel_label`: `pass`, `min=47.678`, `failures=0`, `invalid=0`
- Review app reload status for `scene:charts/size_encoding` completed with `status=succeeded`, `stale=false`, and no queued scopes.

### CHARTS-003 - Heatmap axis-cell extremum emits empty scalar bbox annotation for unanswerable samples

Severity: required_fix

Category: annotation

Resolved on: 2026-06-29

Scope:

- `task_charts__heatmap__axis_cell_extremum_label`

Original issue:

- The task declared scalar `bbox` annotation but allowed unanswerable samples, producing `annotation_gt={"type":"bbox","value":[]}` in stale review artifacts.

Fix:

- Disabled controlled-unanswerable sampling for `axis_cell_extremum_label` because its contract requires one visible selected target-cell bbox.
- Removed the unanswerable prompt placeholder from the axis-cell query templates and documented the answerable-only scalar bbox contract.
- Made the heatmap scalar-bbox projection helper raise if a scalar bbox task has no projected cell bbox, so future invalid empty scalar annotations fail generation instead of being exported.
- Added a regression test that forces `unanswerable_probability=1.0` and verifies the task still emits answerable scalar bbox annotations.
- Regenerated all five `charts/heatmap` task reviews and `scene_review.xlsx`.

Verification:

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_charts_heatmap_tasks.py tests/test_charts_waterfall_tasks.py` passed with `24 passed`.
- `PYTHONPATH=. python -B scripts/run_task_review.py --tasks <34 affected heatmap/waterfall/bar_3d/candlestick/combo_mark/dumbbell/radar task ids> --mode full --out-root review/task-reviews --workers 4` passed distribution review for every affected task.
- `PYTHONPATH=. python -B scripts/audit_review_bbox_min_side.py --review-root review/task-reviews --docs-root docs --domains charts --min-side-px 24 --out-json docs/domain-migration-report/charts/bbox_min_side_audit.json --out-md docs/domain-migration-report/charts/bbox_min_side_audit.md` reports `failures=0 invalid=0 missing=0`.

### CHARTS-004 - Some segment annotation prompts and docs still use legacy endpoint variable names

Severity: required_fix

Category: prompt / annotation

Resolved on: 2026-06-29

Scope:

- Segment prompt/doc contracts under `bar_3d`, `candlestick`, `combo_mark`, `dumbbell`, and `radar`.

Original issue:

- Active segment prompts and task docs used legacy endpoint notation such as `[[x1, y1], [x2, y2]]`.

Fix:

- Normalized active segment prompt hints and matching task docs to the canonical endpoint format `[[x0, y0], [x1, y1]]`.
- Tightened the affected prompt hints to explicitly describe segments as two `[x, y]` pixel points, avoiding ambiguity in the annotation contract.
- Regenerated full review artifacts once for the affected scenes, then regenerated inspection artifacts again after the final prompt wording tightening.

Verification:

- Source scan for legacy `[[x1, y1], [x2, y2]]` and compact `[[x1,y1],[x2,y2]]` patterns under `prompts/charts` and `docs/tasks/charts` returns no matches.
- `PYTHONPATH=. python -B scripts/audit_prompt_annotation_contracts.py --tasks <11 fixed annotation-contract task ids> --samples-per-query-id 1 --output-dir docs/domain-migration-report/charts/prompt_annotation_contracts_fixes --workers 1 --max-attempts 200 --max-total-samples-per-task 1024 --task-timeout-seconds 60` reports `audited 11 tasks, 23 expected query ids, 23 samples, 0 issues`.
- Inspection review artifacts and scene workbooks were regenerated for `bar_3d`, `candlestick`, `combo_mark`, `dumbbell`, and `radar`.

### CHARTS-005 - Waterfall bbox-map prompt examples wrap scalar boxes in one-item arrays

Severity: required_fix

Category: prompt / annotation

Resolved on: 2026-06-29

Scope:

- `task_charts__waterfall__remove_step_final_total`
- `task_charts__waterfall__reverse_step_final_total`

Original issue:

- The prompt examples for these `bbox_map` tasks mapped roles such as `final_total_bar` to one-item bbox arrays instead of scalar `[x0, y0, x1, y1]` boxes.

Fix:

- Updated the waterfall prompt examples so `final_total_bar` and `target_contribution_bar` map directly to scalar bbox values.
- Regenerated all four `charts/waterfall` task reviews and `scene_review.xlsx`.

Verification:

- Source scan for `final_total_bar` or `target_contribution_bar` mapped to one-item bbox arrays returns no matches.
- The focused annotation prompt audit in `docs/domain-migration-report/charts/prompt_annotation_contracts_fixes/` reports `0 issues` across the fixed waterfall, heatmap, and segment tasks.
- Waterfall distribution checks remain passing for all four active waterfall tasks.

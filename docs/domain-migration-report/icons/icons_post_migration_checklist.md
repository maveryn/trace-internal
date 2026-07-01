# Icons Post-Migration Checklist Issues

Audit date: 2026-06-27

Scope: `icons` domain only. This report records identified issues only.

Audit artifacts generated in this pass:

- `docs/domain-migration-report/icons/bbox_min_side_audit.json`
- `docs/domain-migration-report/icons/bbox_min_side_audit.md`
- `docs/domain-migration-report/icons/semantic_sampling_modulo_audit.md`
- `docs/domain-migration-report/icons/visual_candidate_modulo_audit.md`
- `docs/domain-migration-report/icons/prompt_concision_audit.md`
- `docs/domain-migration-report/icons/prompt_annotation_contracts/`

Commands run:

- `PYTHONPATH=. python scripts/audit_active_domain_surfaces.py`
- `PYTHONPATH=. python scripts/audit_review_bbox_min_side.py --review-root review/task-reviews --docs-root docs --domains icons --out-json docs/domain-migration-report/icons/bbox_min_side_audit.json --out-md docs/domain-migration-report/icons/bbox_min_side_audit.md --fail-on-issue`
- `PYTHONPATH=. python scripts/audit_semantic_sampling_modulo.py --root trace/tasks/icons --output docs/domain-migration-report/icons/semantic_sampling_modulo_audit.md`
- `PYTHONPATH=. python scripts/audit_visual_candidate_modulo.py --root trace/tasks/icons --output docs/domain-migration-report/icons/visual_candidate_modulo_audit.md`
- `PYTHONPATH=. python scripts/audit_prompt_concision.py --tasks <40 registered icon task ids> --query-id-coverage --samples-per-query-id 1 --include-all-prompts --output docs/domain-migration-report/icons/prompt_concision_audit.md --workers 4 --max-attempts 200 --max-total-samples-per-task 1024`
- `PYTHONPATH=. python scripts/audit_prompt_annotation_contracts.py --tasks <40 registered icon task ids> --samples-per-query-id 1 --output-dir docs/domain-migration-report/icons/prompt_annotation_contracts --workers 4 --max-attempts 200 --max-total-samples-per-task 1024`

## Open Issues

### ICO-009 - Review DB has no accepted solve-rate status for icon tasks

Severity: Medium

Category: calibration/review status

Scope:

- `review/feedback/review_feedback.sqlite`
- active `icons` tasks

Issue:

- The `task_audit` table records `solve_rate_pass=0` for every icon task row.
- Existing prompt/image/annotation/distribution/code/taxonomy audit flags are
  marked passed, but solve-rate acceptance is absent.

Observed in:

- SQLite query over `review/feedback/review_feedback.sqlite`

Follow-up fix:

- Do not run solve-rate as part of this report-only pass.
- When requested, run current icon solve-rate calibration and update the review
  app status for accepted tasks.

## Resolved

### ICO-010 - Icon task docs used compact Program Contract sections

Severity: Medium

Category: task docs / taxonomy review

Resolved on: 2026-07-01

Fix:

- Normalized all `40` icon task docs under `docs/tasks/icons/` so each
  `## Program Contract` section exposes:
  `Program:`, `Candidate set:`, `Operands:`, `Operation:`, `Output binding:`,
  `Annotation witnesses:`, and `Query ids:`.
- Used `scripts/normalize_reviewed_domain_program_contract_docs.py` to preserve
  each existing compact program expression and expand it into reviewable fields.
- This was docs-only; task code, configs, prompts, review artifacts, and solve
  rate were not changed.

Verification:

- `PYTHONDONTWRITEBYTECODE=1 python -B scripts/normalize_reviewed_domain_program_contract_docs.py --check`
- Result: `reviewed-domain task docs scanned: 444`, `docs requiring normalization: 0`.
- Custom structural scan reports `icons docs 40`, `missing_any 0`, and no
  placeholder schema wording in normalized icon Program Contract sections.

### ICO-006 - One distribution review has non-gating thin query coverage warning

Severity: Low

Category: distribution

Resolved on: 2026-06-28

Scope:

- `task_icons__named_field__scoped_attribute_count`
- query id `outside_band_count`

Original issue:

- The distribution review passed overall, but recorded a non-gating
  `thin_query_id_branch_review_coverage` warning because `outside_band_count`
  appeared only 8 times in the displayed 100-sample review set.

Resolution:

- No code or artifact change needed.
- The underlying distribution artifact collected 100 samples for every query
  id, including `outside_band_count`.
- Overall and per-query distribution checks pass; the warning reflects random
  review-display slice variance, not a task distribution or taxonomy issue.

Verification:

- Inspected
  `review/task-reviews/icons/named_field/task_icons__named_field__scoped_attribute_count/distribution_review.json`.
- Confirmed `pass: true`, no failed query ids, and
  `collected_query_id_counts["outside_band_count"] == 100`.

### ICO-003 - Icon-object bbox annotations violated the 24 px minimum-side rule

Severity: High

Category: annotation

Resolved on: 2026-06-28

Scope:

- `task_icons__icon_field__singleton_type_count`
- `task_icons__reference_canvas__anchor_position_count`
- `task_icons__reference_canvas__reference_type_match_count`
- `task_icons__reference_canvas__reference_color_match_count`
- `task_icons__reference_canvas__reference_rotation_match_count`
- `task_icons__reference_canvas__reference_type_color_rotation_match_count`
- `task_icons__reference_canvas__reference_metric_relation_count`

Original issue:

- Existing task-review artifacts contained icon-object bbox annotations with
  width or height below the required 24 px minimum side.
- The first failing audit found `singleton_type_count` at 16 px and
  `anchor_position_count` at 18 px; after those paths were fixed and
  regenerated, the fresh audit exposed the same raw-bbox issue in sibling
  `reference_canvas` matching tasks.

Fix:

- Routed icon-field and reference-canvas icon-object bbox-set annotations
  through `icon_bbox_set_annotation`.
- Expanded annotation bboxes around rendered icon centers, clipped to each
  scene's semantic content panel, without changing rendered images or answer
  semantics.
- Regenerated affected task-review artifacts under `review/task-reviews/`.

Verification:

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_icons_counting_singleton_type_tasks.py tests/test_icons_counting_singleton_type_contracts.py tests/test_icons_relation_relative_position_type_tasks.py tests/test_icons_relation_relative_position_type_contracts.py tests/test_icons_scene_config.py`
  passed.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_icons_counting_reference_match_count_tasks.py tests/test_icons_counting_reference_match_count_contracts.py tests/test_icons_counting_size_relation_tasks.py tests/test_icons_counting_size_relation_contracts.py tests/test_icons_relation_relative_position_type_tasks.py tests/test_icons_relation_relative_position_type_contracts.py tests/test_icons_counting_singleton_type_tasks.py tests/test_icons_counting_singleton_type_contracts.py tests/test_icons_scene_config.py`
  passed.
- `PYTHONPATH=. python scripts/run_task_review.py --tasks task_icons__icon_field__singleton_type_count,task_icons__reference_canvas__anchor_position_count --mode full --out-root review/task-reviews --max-attempts-per-instance 300 --workers 2`
  passed distribution and regenerated review artifacts.
- `PYTHONPATH=. python scripts/run_task_review.py --tasks task_icons__reference_canvas__reference_type_match_count,task_icons__reference_canvas__reference_color_match_count,task_icons__reference_canvas__reference_rotation_match_count,task_icons__reference_canvas__reference_type_color_rotation_match_count,task_icons__reference_canvas__reference_metric_relation_count,task_icons__reference_canvas__anchor_position_count --mode full --out-root review/task-reviews --max-attempts-per-instance 300 --workers 2`
  passed distribution and regenerated review artifacts.
- `PYTHONPATH=. python scripts/audit_review_bbox_min_side.py --review-root review/task-reviews --docs-root docs --domains icons --out-json docs/domain-migration-report/icons/bbox_min_side_audit.json --out-md docs/domain-migration-report/icons/bbox_min_side_audit.md --fail-on-issue`
  passed with `failures=0`, `invalid=0`, and `missing=0`.

### ICO-001 - Active inventory is stale for icons

Severity: High

Category: stale artifact/docs

Resolved on: 2026-06-27

Scope:

- `docs/ACTIVE_TASK_INVENTORY.md`
- `icons/pair_grid`
- `icons/sequence_strip`

Original issue:

- The task registry and review artifacts exposed 40 active icon tasks, but
  `docs/ACTIVE_TASK_INVENTORY.md` reported 39.
- The inventory listed retired or unknown icon task ids from old `pair_grid`
  and `sequence_strip` contracts.
- The registry/review active set instead contained:
  - `task_icons__pair_grid__reference_color_pair_match_label`
  - `task_icons__pair_grid__reference_transform_match_label`
  - `task_icons__sequence_strip__count_progression_completion_label`
  - `task_icons__sequence_strip__rotation_progression_completion_label`
  - `task_icons__sequence_strip__size_progression_completion_label`

Fix:

- Updated the icons domain summary row from 39 to 40 tasks.
- Replaced retired `pair_grid` task ids with the registered active label tasks.
- Replaced retired `sequence_strip` task ids with the three registered active
  completion-label tasks.

Verification:

- Confirmed `trace.tasks.TASK_REGISTRY` exposes 40 active `task_icons__...`
  task ids.
- Confirmed the `icons` section in `docs/ACTIVE_TASK_INVENTORY.md` now lists
  the same active `pair_grid` and `sequence_strip` task ids as the registry.

### ICO-002 - Retired icon task ids remain in review/example state

Severity: Medium

Category: stale artifact/docs

Resolved on: 2026-06-27

Scope:

- `review/feedback/review_feedback.sqlite`
- `configs/examples/`

Original issue:

- The review feedback DB `task_audit` table had 42 `icons` rows while the
  current registry had 40 active icon tasks.
- Stale `task_audit` rows remained for retired `icon_field` and
  `sequence_strip` ids.
- During the fix, the same retired `sequence_strip` task was also found in
  `feedback` and `feedback_notes`.
- Retired example configs remained for old `icon_field` and `pair_grid`
  contracts.

Fix:

- Deleted retired icon task rows from `feedback_notes`, `feedback_comments`,
  `feedback`, `task_audit`, and `taxonomy_decision_review`.
- Deleted the two retired icon example configs.

Verification:

- Confirmed no stale DB rows remain for the retired `icon_field`,
  `sequence_strip`, or `pair_grid` contracts.
- Confirmed icon `task_audit` row count is now 40.
- Confirmed there is still no open icon feedback in the review DB.
- Confirmed the retired icon example config files no longer exist.

### ICO-004 - Config-level query weights remain in migrated icon scenes

Severity: Medium

Category: query split / config

Resolved on: 2026-06-27

Scope:

- `configs/domains/icons/named_grid.yaml`
- `configs/domains/icons/named_field.yaml`
- `tests/test_icons_scene_config.py`
- `review/task-reviews/icons/named_grid/`
- `review/task-reviews/icons/named_field/`

Original issue:

- Review-candidate migrated scenes should sample query ids uniformly by default
  and should not carry config-level query routing/weight maps unless a later
  global policy explicitly approves them.
- Icons still had uniform config-level query weights in `named_grid.yaml` and
  `named_field.yaml`.

Fix:

- Removed `query_id_weights`, `query_weights`, and
  `distance_rank_query_weights` from icon scene config.
- Updated icon scene-config tests to assert these config-level query-weight
  maps are absent.
- Regenerated review artifacts for the five affected tasks:
  - `task_icons__named_grid__scoped_attribute_count`
  - `task_icons__named_grid__row_column_shape_extreme_number`
  - `task_icons__named_grid__group_predicate_count`
  - `task_icons__named_field__count_arithmetic`
  - `task_icons__named_field__reference_distance_rank_label`
- Reloaded the review app scenes for `icons/named_field` and
  `icons/named_grid`.

Verification:

- Confirmed no `configs/domains/icons/*.yaml` file contains
  `query_id_weights:`, `query_weights:`, or `distance_rank_query_weights:`.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_icons_scene_config.py`
  passed.
- A targeted smoke check confirmed all explicit query ids still generate for
  the five affected tasks and do not record config-level query-weight maps in
  `query_spec.params`.
- Targeted task-review regeneration passed distribution checks for all five
  affected tasks with zero warnings.
- `PYTHONPATH=. python scripts/audit_active_domain_surfaces.py` passed.
- Review app scene reloads for `icons/named_field` and `icons/named_grid`
  completed successfully.

### ICO-005 - Some icon query ids encode attribute operands or mixed operations

Severity: Medium

Category: taxonomy/program

Resolved on: 2026-06-27

Fix:

- Retired the combined public task ids:
  - `task_icons__reference_canvas__reference_attribute_match_count`
  - `task_icons__paired_canvas__panel_attribute_change_count`
  - `task_icons__named_field__count_arithmetic`
- Added split public task ids:
  - `task_icons__reference_canvas__reference_type_match_count`
  - `task_icons__reference_canvas__reference_color_match_count`
  - `task_icons__reference_canvas__reference_rotation_match_count`
  - `task_icons__reference_canvas__reference_type_color_rotation_match_count`
  - `task_icons__paired_canvas__color_change_count`
  - `task_icons__paired_canvas__rotation_change_count`
- Split tasks use public `query_id = single` where there is no real public
  branch. Internal legacy branch names are retained only as `internal_query_id`
  trace metadata.
- Updated icon task docs, icon scene configs, icon tests, and the shared task
  unit/query policy docs.
- Later paired-canvas cleanup retired the original-lookup split tasks and the
  movement-direction task, leaving paired-canvas with set-relation, color-change,
  and rotation-change count objectives.
- Later icon cleanup retired the structured pattern-violation scene and the
  named-field count-arithmetic objectives entirely.

Verification:

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/test_icons_counting_reference_match_count_tasks.py tests/test_icons_counting_reference_match_count_contracts.py tests/test_icons_paired_canvas_tasks.py tests/test_icons_scene_config.py tests/test_icons_prompt_wording.py`
  passed.

### ICO-008 - Unused legacy public-query helper remains in icon shared code

Severity: Low

Category: stale code

Resolved on: 2026-06-28

Fix:

- Deleted `trace/tasks/icons/shared/public_query_task.py`.
- Updated `docs/SCENE_PACKAGE_MIGRATION/ICONS_SHARED_BOUNDARY.md` to record the
  helper as retired and to keep future icon scene packages from using retired
  icon-specific public-query output rewriters.

Verification:

- Confirmed no current source or tests import `rewrite_icons_query_output` or
  `trace.tasks.icons.shared.public_query_task`.

### ICO-007 - Stale icon task doc points to a retired scene/prompt bundle

Severity: Low

Category: stale docs

Resolved on: 2026-06-28

Fix:

- Updated `docs/tasks/icons/named_field/task_icons__named_field__reference_distance_rank_label.md`
  to declare only `scene_id: named_field`.
- Replaced the retired relation prompt bundle reference with
  `prompts/icons/named_field/icons_named_field_v1.json`.
- Updated the prompt contract to the active `scene_key: single_scene_counting`
  and `task_key: counting_query` used by `configs/domains/icons/named_field.yaml`.

Verification:

- Confirmed the task doc no longer references `scene_id: relation`,
  `icons_relation_v0`, `named_reference_distance_relation`, or
  `relation_query`.

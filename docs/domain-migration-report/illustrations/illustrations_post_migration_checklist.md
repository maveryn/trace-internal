# Illustrations Post-Migration Checklist Issues

Audit date: 2026-06-28

Scope: `illustrations` domain only. This report records identified issues only.

Audit artifacts generated in this pass:

- `docs/domain-migration-report/illustrations/bbox_min_side_audit.json`
- `docs/domain-migration-report/illustrations/bbox_min_side_audit.md`
- `docs/domain-migration-report/illustrations/semantic_sampling_modulo_audit.md`
- `docs/domain-migration-report/illustrations/visual_candidate_modulo_audit.md`
- `docs/domain-migration-report/illustrations/prompt_concision_audit.md`
- `docs/domain-migration-report/illustrations/prompt_annotation_contracts/`

Commands run:

- `PYTHONPATH=. python scripts/generate_active_task_inventory.py --check`
- `PYTHONPATH=. python scripts/check_active_inventory_integrity.py --include-local-cache`
- `PYTHONPATH=. python scripts/audit_active_domain_surfaces.py`
- `PYTHONPATH=. python scripts/audit_review_bbox_min_side.py --review-root review/task-reviews --docs-root docs --domains illustrations --min-side-px 24 --out-json docs/domain-migration-report/illustrations/bbox_min_side_audit.json --out-md docs/domain-migration-report/illustrations/bbox_min_side_audit.md --fail-on-issue`
- `PYTHONPATH=. python scripts/audit_semantic_sampling_modulo.py --root trace/tasks/illustrations --root trace/core --output docs/domain-migration-report/illustrations/semantic_sampling_modulo_audit.md`
- `PYTHONPATH=. python scripts/audit_visual_candidate_modulo.py --root trace/tasks/illustrations --root trace/core --output docs/domain-migration-report/illustrations/visual_candidate_modulo_audit.md`
- `PYTHONPATH=. python scripts/audit_prompt_concision.py --tasks <60 illustration task ids> --query-id-coverage --samples-per-query-id 1 --include-all-prompts --output docs/domain-migration-report/illustrations/prompt_concision_audit.md --workers 4 --max-attempts 200 --max-total-samples-per-task 1024`
- `PYTHONPATH=. python scripts/audit_prompt_annotation_contracts.py --tasks <60 illustration task ids> --samples-per-query-id 1 --output-dir docs/domain-migration-report/illustrations/prompt_annotation_contracts --workers 4 --max-attempts 200 --max-total-samples-per-task 1024`
- `TRACE_SCENE_PACKAGE_REVIEW_SCENE=illustrations/<scene_id> PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_scene_package_migration_contracts.py` for all 12 illustration scenes.
- `PYTHONPATH=. python scripts/run_task_review.py --tasks <60 illustration task ids> --mode full --out-root review/task-reviews --random-count 100 --max-attempts-per-instance 512 --workers 4`
- `PYTHONPATH=. python scripts/run_task_review.py --tasks <7 pixel-village task ids> --mode full --out-root review/task-reviews --random-count 100 --max-attempts-per-instance 512 --workers 4`
- `PYTHONPATH=. python scripts/run_task_review.py --tasks <6 park-playground task ids> --mode full --out-root review/task-reviews --random-count 100 --max-attempts-per-instance 512 --workers 4`

## Open Issues

### ILL-007 - Review DB has no accepted solve-rate status for illustration tasks

Severity: Medium

Category: calibration/review status

Scope:

- `review/feedback/review_feedback.sqlite`
- active `illustrations` tasks

Issue:

- The `task_audit` table has 60 illustration rows.
- Prompt, image, annotation, distribution, code review, and taxonomy review
  flags are all set for those rows.
- `solve_rate_pass=0` for all 60 illustration tasks.

Follow-up fix:

- Do not run solve-rate as part of this report-only pass.
- When requested, run current illustration solve-rate calibration and update
  review app status for accepted tasks.

## Resolved issues

### ILL-008 - Illustration task docs used compact Program Contract sections

Resolved on: 2026-07-01

Fix:

- Normalized all `60` illustration task docs under
  `docs/tasks/illustrations/` so each `## Program Contract` section exposes:
  `Program:`, `Candidate set:`, `Operands:`, `Operation:`, `Output binding:`,
  `Annotation witnesses:`, and `Query ids:`.
- Used `scripts/normalize_reviewed_domain_program_contract_docs.py` to preserve
  each existing compact program expression and expand it into reviewable fields.
- This was docs-only; task code, configs, prompts, review artifacts, and solve
  rate were not changed.

Verification:

- `PYTHONDONTWRITEBYTECODE=1 python -B scripts/normalize_reviewed_domain_program_contract_docs.py --check`
- Result: `reviewed-domain task docs scanned: 444`, `docs requiring normalization: 0`.
- Custom structural scan reports `illustrations docs 60`, `missing_any 0`, and
  no placeholder schema wording in normalized illustration Program Contract
  sections.

### ILL-001 - Review artifacts were stale for every illustration scene

Resolved:

- Regenerated current task-review artifacts under `review/task-reviews/` for all
  60 active illustration tasks across all 12 illustration scenes.
- Rebuilt the scene review workbooks for every illustration scene.
- Stabilized `task_illustrations__pixel_village__river_side_object_count` by
  sampling a requested target answer count from configured support and requiring
  the rendered river-side count to match it. This removed the incidental
  low-count distribution skew found during fresh review generation.
- Regenerated all seven `pixel_village` task reviews and the scene workbook
  after the river-side count stabilization.
- During the fresh bbox audit, fixed a newly surfaced
  `task_illustrations__park_playground__playground_equipment_count` annotation
  bbox below the `24 px` minimum by expanding equipment semantic bboxes before
  rendering/annotation packaging.
- Regenerated all six `park_playground` task reviews and the scene workbook
  after the park equipment bbox fix.
- Reloaded the review app scenes for all 12 illustration scenes after the
  regenerated artifacts were written.

Verification:

- `PYTHONPATH=. python scripts/audit_active_domain_surfaces.py`
  passed with `active domain surfaces OK`.
- Active illustration distribution aggregation found
  `active_illustration_tasks=60`, `missing_distribution=0`, and
  `failing_distribution=0`.
- `PYTHONPATH=. python scripts/audit_review_bbox_min_side.py --review-root review/task-reviews --docs-root docs --domains illustrations --min-side-px 24 --out-json docs/domain-migration-report/illustrations/bbox_min_side_audit.json --out-md docs/domain-migration-report/illustrations/bbox_min_side_audit.md --fail-on-issue`
  passed with `failures=0 invalid=0 missing=0`.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_illustrations_pixel_village_tasks.py::test_pixel_village_river_side_object_count_uses_strict_tile_side_membership tests/test_illustrations_pixel_village_tasks.py::test_pixel_village_river_side_object_count_sampler_cycles_target_counts`
  passed with 2 tests.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_illustrations_park_playground_tasks.py::test_playground_equipment_count_contract`
  passed.
- `GET /api/reload/status` reported `in_progress=false`, no queued scopes, and
  `stale_scenes=[]` after the scene reload queue completed.

### ILL-002 - Active taxonomy mapping was missing 12 illustration tasks

Resolved:

- Added the 12 missing `isometric_farmstead`, `isometric_quarry`, and
  `rpg_tactical_map` public task ids to `trace/core/taxonomy.py`.
- Updated `docs/ACTIVE_TASK_INVENTORY.md` so the inventory warning section no
  longer lists illustration missing-taxonomy rows.

Verification:

- Focused illustration taxonomy comparison:
  `review=60 taxonomy=60 missing=0 extra=0`.
- `scripts/generate_active_task_inventory.py --check` reports
  `docs/ACTIVE_TASK_INVENTORY.md is up to date`.
- `scripts/check_active_inventory_integrity.py` still reports unrelated icon
  taxonomy gaps for `task_icons__pair_grid__reference_color_pair_match_label`
  and `task_icons__pair_grid__reference_transform_match_label`.

### ILL-003 - `rpg_dungeon` failed current scene-package source-boundary gates

Resolved:

- Refactored the three RPG dungeon count tasks so their public files expose
  direct `generate` methods plus objective-local scene-kwargs and witness
  binders.
- Replaced the old private plan/inheritance routing with identity-free
  lifecycle plumbing for defaults, retry rendering, and neutral packaging.
- Moved count trace assembly out of scene shared code so shared role files no
  longer carry task/query identity keys.
- Regenerated the four `rpg_dungeon` task-review artifacts and scene workbook.
- Reloaded the review app index for `illustrations/rpg_dungeon`.

Verification:

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_illustrations_rpg_dungeon_tasks.py`
  passed with 8 tests.
- `TRACE_SCENE_PACKAGE_REVIEW_SCENE=illustrations/rpg_dungeon PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_scene_package_migration_contracts.py`
  passed with 41 tests.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_review_app.py tests/test_run_task_review.py`
  passed with 46 tests.
- `PYTHONPATH=. python scripts/run_task_review.py --tasks task_illustrations__rpg_dungeon__reachable_chest_count,task_illustrations__rpg_dungeon__monster_chamber_count,task_illustrations__rpg_dungeon__safe_reachable_chest_count,task_illustrations__rpg_dungeon__missing_patch_label --mode full --out-root review/task-reviews --random-count 100 --max-attempts-per-instance 512 --workers 4`
  regenerated review artifacts with all four distribution reviews passing.

### ILL-004 - One bbox-family task violated the 24 px minimum-side rule

Resolved:

- Added renderer-side normalization for isometric-harbor boat entity bboxes so
  boat annotations are expanded to at least `24.5 px` on both sides after final
  projection and kept inside the canvas.
- The normalization is applied before task annotation/render-map packaging, so
  `annotation_gt`, `projected_annotation`, `scene_ir`, and `render_map` use the
  same bbox values.
- Added a focused mooring-status contract assertion that generated boat bboxes
  meet the `24 px` minimum-side rule.
- Regenerated all four `isometric_harbor` task-review artifacts and the scene
  workbook because the renderer bbox projection affects every harbor boat task.
- Reloaded the review app index for `illustrations/isometric_harbor`.

Verification:

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_illustrations_isometric_harbor_tasks.py::test_isometric_harbor_boat_mooring_status_count_contract`
  passed.
- `PYTHONPATH=. python scripts/run_task_review.py --tasks task_illustrations__isometric_harbor__boat_side_count,task_illustrations__isometric_harbor__boat_mooring_status_count,task_illustrations__isometric_harbor__boat_heading_status_count,task_illustrations__isometric_harbor__shoreline_nearest_boat_label --mode full --out-root review/task-reviews --random-count 100 --max-attempts-per-instance 512 --workers 4`
  regenerated the harbor task reviews with all four distribution reviews passing.
- `PYTHONPATH=. python scripts/audit_review_bbox_min_side.py --review-root review/task-reviews --docs-root docs --domains illustrations --min-side-px 24 --out-json docs/domain-migration-report/illustrations/bbox_min_side_audit.json --out-md docs/domain-migration-report/illustrations/bbox_min_side_audit.md --fail-on-issue`
  passed with `failures=0 invalid=0 missing=0`.

### ILL-005 - Scalar bbox prompt example used a one-item bbox list

Resolved:

- Changed the shoreline-nearest boat prompt example from a one-item bbox list
  to the scalar bbox shape required by the task contract:
  `{"annotation":[188,408,252,452],"answer":"C"}`.
- Regenerated the illustration prompt/annotation contract audit and the
  affected shoreline-nearest task-review artifacts.
- Reloaded the review app scenes for `illustrations/isometric_harbor`,
  `illustrations/indoor_room`, and `illustrations/library`.

Verification:

- `PYTHONPATH=. python scripts/audit_prompt_annotation_contracts.py --tasks <60 illustration task ids> --samples-per-query-id 1 --output-dir docs/domain-migration-report/illustrations/prompt_annotation_contracts --workers 4 --max-attempts 200 --max-total-samples-per-task 1024`
  audited 60 tasks, 74 query ids, 74 samples, and reported 0 issues.
- `PYTHONPATH=. python scripts/run_task_review.py --tasks task_illustrations__isometric_harbor__shoreline_nearest_boat_label,task_illustrations__indoor_room__rotated_tile_label,task_illustrations__indoor_room__missing_patch_label,task_illustrations__library__rotated_tile_label,task_illustrations__library__swapped_tile_pair_label,task_illustrations__library__missing_patch_label --mode full --out-root review/task-reviews --random-count 100 --max-attempts-per-instance 512 --workers 4 --skip-scene-workbooks`
  regenerated the affected task artifacts, with all six distribution reviews passing.

### ILL-006 - Dormant prompt variants used banned "Look at" openers

Resolved:

- Rewrote the five dormant `Look at` query templates in the indoor-room and
  library prompt bundles to direct task wording.
- Regenerated the illustration prompt concision report and the affected
  indoor-room/library task-review artifacts.
- Reloaded the review app scenes for `illustrations/indoor_room` and
  `illustrations/library`.

Verification:

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_prompt_system.py::test_prompt_bundles_avoid_awkward_visual_openers`
  passed.
- `PYTHONPATH=. python scripts/audit_prompt_concision.py --tasks <60 illustration task ids> --query-id-coverage --samples-per-query-id 1 --include-all-prompts --output docs/domain-migration-report/illustrations/prompt_concision_audit.md --workers 4 --max-attempts 200 --max-total-samples-per-task 1024`
  refreshed the report with 148 rendered prompts.
- Direct scan over the updated illustration prompt bundles and refreshed audit
  reports found no `Look at` prompt variants.

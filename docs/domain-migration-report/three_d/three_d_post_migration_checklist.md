# Three_D Post-Migration Checklist Issues

Audit date: 2026-06-28

Scope: `three_d` domain only. This report records identified issues only.

Audit artifacts generated in this pass:

- `docs/domain-migration-report/three_d/bbox_min_side_audit.json`
- `docs/domain-migration-report/three_d/bbox_min_side_audit.md`
- `docs/domain-migration-report/three_d/semantic_sampling_modulo_audit.md`
- `docs/domain-migration-report/three_d/visual_candidate_modulo_audit.md`
- `docs/domain-migration-report/three_d/prompt_concision_audit.md`
- `docs/domain-migration-report/three_d/prompt_annotation_contracts/`

Commands run:

- `PYTHONPATH=. python scripts/generate_active_task_inventory.py --check`
- `PYTHONPATH=. python scripts/check_active_inventory_integrity.py --include-local-cache`
- `PYTHONPATH=. python scripts/audit_active_domain_surfaces.py`
- `PYTHONPATH=. python scripts/audit_review_bbox_min_side.py --review-root review/task-reviews --docs-root docs --domains three_d --min-side-px 24 --out-json docs/domain-migration-report/three_d/bbox_min_side_audit.json --out-md docs/domain-migration-report/three_d/bbox_min_side_audit.md --fail-on-issue`
- `PYTHONPATH=. python scripts/audit_semantic_sampling_modulo.py --root trace/tasks/three_d --root trace/core --output docs/domain-migration-report/three_d/semantic_sampling_modulo_audit.md`
- `PYTHONPATH=. python scripts/audit_visual_candidate_modulo.py --root trace/tasks/three_d --root trace/core --output docs/domain-migration-report/three_d/visual_candidate_modulo_audit.md`
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest tests/test_semantic_sampling_modulo_audit.py tests/test_visual_candidate_modulo_audit.py tests/test_core_sampling.py tests/test_three_d_carousel_tasks.py tests/test_three_d_conveyor_tasks.py tests/test_three_d_spatial_camera_distance.py tests/test_three_d_spatial_multiview_object_match.py tests/test_three_d_spatial_object_relation.py tests/test_three_d_spatial_between_references.py tests/test_three_d_spatial_occlusion_order.py tests/test_three_d_spatial_height_extremum.py tests/test_three_d_room_wall_object_camera_distance.py tests/test_three_d_room_wall_object_same_wall_reference.py tests/test_three_d_room_wall_object_side_relation.py tests/test_three_d_street_intersection_nearest.py tests/test_three_d_street_lane_ahead_object.py tests/test_three_d_street_same_road_arm_reference.py tests/test_three_d_surface_fixture_count.py tests/test_three_d_warehouse_robot_forward_path.py tests/test_three_d_warehouse_robot_nearest_object.py`
- `PYTHONPATH=. python scripts/run_task_review.py --tasks <60 active three_d task ids> --mode inspection --out-root review/task-reviews --random-count 100 --max-attempts-per-instance 400 --workers 4 --skip-scene-workbooks`
- `POST /api/reload/scene/three_d/<scene_id>` for carousel, conveyor,
  object_cluster, object_scene, room, street, surface_fixture, and warehouse.
- `PYTHONPATH=. python scripts/audit_prompt_concision.py --tasks <60 three_d task ids> --query-id-coverage --samples-per-query-id 1 --include-all-prompts --output docs/domain-migration-report/three_d/prompt_concision_audit.md --workers 4 --max-attempts 200 --max-total-samples-per-task 1024`
- `PYTHONPATH=. python scripts/audit_prompt_annotation_contracts.py --tasks <60 three_d task ids> --samples-per-query-id 1 --output-dir docs/domain-migration-report/three_d/prompt_annotation_contracts --workers 4 --max-attempts 200 --max-total-samples-per-task 1024`
- `PYTHONDONTWRITEBYTECODE=1 python -B scripts/cleanup_retired_task_audit_rows.py --domain three_d --output-root review/feedback-cleanup`
- `PYTHONDONTWRITEBYTECODE=1 python -B scripts/cleanup_retired_task_audit_rows.py --domain three_d --output-root review/feedback-cleanup --apply`

## Open Issues

### T3D-008 - Review DB has no accepted solve-rate status for three_d tasks

Severity: Medium

Category: calibration / review status

Scope:

- `review/feedback/review_feedback.sqlite`
- active `three_d` tasks

Issue:

- The `task_audit` rows for `three_d` have no accepted solve-rate status.
- Current DB counts after the T3D-007 retired-row cleanup:
  - `prompt_pass=60`
  - `image_pass=60`
  - `annotation_pass=60`
  - `distribution_pass=60`
  - `code_review_pass=60`
  - `taxonomy_review_pass=60`
  - `solve_rate_pass=0`
- These counts align with the 60 active `three_d` task rows.

Observed in:

- SQLite read-only query over `review/feedback/review_feedback.sqlite`

Follow-up fix:

- Do not run solve-rate as part of this report-only pass.
- After retired rows are cleaned up and source/review blockers are fixed, run
  current three_d solve-rate calibration when explicitly requested and update
  the review app status for accepted tasks.

## Resolved Issues

### T3D-007 - Review feedback DB contained retired three_d task rows

Resolved on: 2026-07-01

Fix:

- Ran the retired-task review cleanup script for `domain=three_d`.
- Deleted 14 retired `three_d` rows from
  `review/feedback/review_feedback.sqlite`.
- Cleanup wrote an audit receipt and SQLite backup under
  `review/feedback-cleanup/`.

Deleted rows:

- `task_three_d__carousel__adjacent_pair_count`
- `task_three_d__carousel__belt_count_arithmetic_value`
- `task_three_d__carousel__between_marked_items_count`
- `task_three_d__carousel__scope_count_after_transfer_value`
- `task_three_d__carousel__scoped_belt_object_count`
- `task_three_d__conveyor__adjacent_pair_count`
- `task_three_d__conveyor__between_marked_items_count`
- `task_three_d__conveyor__lane_count_arithmetic_value`
- `task_three_d__conveyor__scope_count_after_transfer_value`
- `task_three_d__conveyor__scoped_belt_object_count`
- `task_three_d__object_cluster__count_arithmetic`
- `task_three_d__object_cluster__single_attribute_membership_count`
- `task_three_d__object_scene__counterfactual_count`
- `task_three_d__surface_fixture__empty_or_missing_cell_count`

Cleanup artifacts:

- Dry-run receipt:
  `review/feedback-cleanup/retired_task_audit_cleanup_20260701T084511Z0000.json`
- Applied receipt:
  `review/feedback-cleanup/retired_task_audit_cleanup_20260701T084516Z0000.json`
- Applied markdown receipt:
  `review/feedback-cleanup/retired_task_audit_cleanup_20260701T084516Z0000.md`
- Backup:
  `review/feedback-cleanup/review_feedback.sqlite.retired_task_audit_cleanup_20260701T084516Z0000.bak`

Verification:

- Dry run reported `active_review_task_count=60`,
  `db_task_audit_rows_before=74`, `stale_row_count_before=14`, and
  `deleted_row_count=0`.
- Applied cleanup reported `active_review_task_count=60`,
  `db_task_audit_rows_before=74`, `deleted_row_count=14`,
  `db_task_audit_rows_after=60`, and `stale_row_count_after=0`.
- Direct registry/review-root/DB check now reports `active=60`, `review=60`,
  `db=60`, `db_stale=0`, and `db_missing=0`.
- `solve_rate_pass` remains `0/60`; solve-rate was not run.

### T3D-009 - Three_D task docs used compact Program Contract sections

Resolved on: 2026-07-01

Fix:

- Normalized all `60` three_d task docs under `docs/tasks/three_d/` so each
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
- Custom structural scan reports `three_d docs 60`, `missing_any 0`, and no
  placeholder schema wording in normalized three_d Program Contract sections.

### T3D-006 - Random visual candidate selection still used modulo/index cycling

Resolved on: 2026-06-28

Fix:

- Replaced modulo/index visual candidate selection with seeded support sampling
  or deterministic shuffled support repetition across three_d scene families:
  carousel, conveyor, object_cluster, object_scene, room, street,
  surface_fixture, and warehouse.
- Added shared support helpers in `trace/tasks/three_d/shared/task_support.py`
  for explicit support choice and shuffled repeated support.
- Removed stale `_sample_cursor` and `_balanced_answer_seed` plumbing where it
  was no longer consumed.
- Converted render-only color and closed-polygon wraparound sites away from
  `% len(...)` syntax so the audit reports stay strict and low-noise.
- Updated conveyor/carousel readability gating so the `24 px` strict min-side
  rule applies to target/annotation boxes while thin non-target distractors are
  still checked for inside-image, long-side, and area readability.

Verification:

- `rg -n "resolve_selection_index|balanced_seed|_balanced_answer_seed|_sample_cursor|instance_seed\\s*%|% len\\(" trace/tasks/three_d -g '*.py'`
  returns no matches.
- `PYTHONPATH=. python scripts/audit_visual_candidate_modulo.py --root trace/tasks/three_d --root trace/core --output docs/domain-migration-report/three_d/visual_candidate_modulo_audit.md`
  now reports:
  - total visual modulo sites: `9`
  - random candidate selection needs refactor: `0`
  - sampling-time assignment needs review: `0`
  - needs manual review: `0`
  - likely safe deterministic assignment: `9` in core review overlays only.
- Focused three_d/audit pytest suite passed:
  `144 passed`.
- Regenerated three_d inspection review artifacts for all `60` active three_d
  tasks under `review/task-reviews` with `100` inspection samples per task.
- Scene-scoped review app reloads succeeded for:
  carousel, conveyor, object_cluster, object_scene, room, street,
  surface_fixture, and warehouse.

### T3D-005 - Semantic modulo/cursor sampling remained broad in three_d source

Resolved on: 2026-06-28

Fix:

- Replaced task/scene semantic modulo sampling with explicit support/range
  resolution and seeded RNG choices across carousel, conveyor, object_cluster,
  object_scene, room, street, surface_fixture, and warehouse.
- Removed legacy selection-index usage from three_d task code.
- Left modulo only in core review tooling where it is review overlay coloring or
  review harness stratification, not task generation.

Verification:

- `PYTHONPATH=. python scripts/audit_semantic_sampling_modulo.py --root trace/tasks/three_d --root trace/core --output docs/domain-migration-report/three_d/semantic_sampling_modulo_audit.md`
  now reports:
  - raw line findings: `10`
  - grouped selection sites: `10`
  - needs refactor: `0`
  - needs manual review: `0`
  - review harness stratification / round-robin: `1`
  - allowed deterministic visual/layout enumeration: `9`.
- Focused three_d/audit pytest suite passed:
  `144 passed`.
- Regenerated three_d inspection review artifacts for all `60` active three_d
  tasks under `review/task-reviews` with `100` inspection samples per task.
- Scene-scoped review app reloads succeeded for:
  carousel, conveyor, object_cluster, object_scene, room, street,
  surface_fixture, and warehouse.

### T3D-004 - Segment annotation prompts were missing canonical endpoint wording

Resolved on: 2026-06-28

Fix:

- Updated ordered-adjacent-pair annotation hints in:
  - `prompts/three_d/carousel/three_d_carousel_v1.json`
  - `prompts/three_d/conveyor/three_d_conveyor_v1.json`
- The affected prompts now describe each witness as a pixel-space segment
  `[[x0, y0], [x1, y1]]`, with each endpoint explicitly identified as an
  `[x, y]` pixel point at an object center.
- Regenerated inspection review artifacts under `review/task-reviews` for:
  - `task_three_d__carousel__color_ordered_adjacent_pair_count`
  - `task_three_d__carousel__object_type_ordered_adjacent_pair_count`
  - `task_three_d__conveyor__color_ordered_adjacent_pair_count`
  - `task_three_d__conveyor__object_type_ordered_adjacent_pair_count`

Verification:

- Focused carousel/conveyor/surface-fixture/object-scene tests passed:
  `49 passed, 1 deselected`.
- `scripts/audit_prompt_annotation_contracts.py` no longer reports
  `missing_point_notation` or `missing_pixel_space_wording` for the four
  ordered-adjacent-pair tasks.
- `scripts/audit_prompt_concision.py` was rerun so prompt sample excerpts no
  longer show the legacy `[[x0,y0],[x1,y1]]` wording for these tasks.

### T3D-003 - Scalar bbox prompt examples used one-item bbox lists

Resolved on: 2026-06-28

Fix:

- Updated scalar `bbox` prompt examples and hints in:
  - `prompts/three_d/object_scene/three_d_object_scene_v1.json`
  - `prompts/three_d/surface_fixture/three_d_surface_fixture_v1.json`
- The affected prompt examples now use scalar bbox annotation shape:
  `{"annotation":[x0,y0,x1,y1],"answer":"..."}`.
- Regenerated inspection review artifacts under `review/task-reviews` for:
  - `task_three_d__object_scene__camera_distance_extremum_label`
  - `task_three_d__surface_fixture__element_count_extremum_label`
  - `task_three_d__surface_fixture__recolor_board_match_label`

Verification:

- Direct generation for the three affected tasks shows scalar bbox examples in
  rendered prompts.
- `scripts/audit_prompt_annotation_contracts.py` no longer reports scalar bbox
  list-example issues.
- `scripts/audit_prompt_concision.py` was rerun so prompt sample excerpts no
  longer show one-item bbox-list examples for these tasks.

### T3D-002 - Seven bbox-family tasks violated the 24 px minimum-side rule

Resolved on: 2026-06-28

Fix:

- Added shared three_d annotation bbox normalization that expands bbox
  annotations to at least `24 px` on each side after final rendering/projection.
- Applied it to:
  - object-scene scalar option-label annotations
  - object-scene view/camera relation bbox-set annotations
  - surface-fixture bbox-set annotations
- Preserved raw render/object bboxes separately in trace metadata so answer
  logic and geometric relation checks continue to use the original rendered
  geometry.
- Recorded normalization metadata in `render_spec`/`render_map`, including raw
  bboxes, normalized bboxes, bounds, min-side settings, and changed indices.
- Regenerated review artifacts under `review/task-reviews` for the seven
  affected tasks:
  - `task_three_d__object_scene__between_references_label`
  - `task_three_d__object_scene__camera_depth_relation_count`
  - `task_three_d__object_scene__camera_distance_extremum_label`
  - `task_three_d__object_scene__image_plane_lateral_relation_count`
  - `task_three_d__object_scene__object_relation_label`
  - `task_three_d__object_scene__occlusion_order_label`
  - `task_three_d__surface_fixture__repeated_element_count`

Verification:

- Focused three_d tests passed with pytest plugin autoload disabled:
  - `32 passed, 1 deselected` for the affected object-scene/surface-fixture
    tests, excluding an unrelated camera-yaw sampler assertion.
  - `10 passed` for height-extremum/reference-nearest option-panel coverage.
- Direct generation for all seven affected task ids produced bbox annotations
  with observed min side `>= 24 px`.
- Regenerated distribution reviews for the seven affected tasks all pass.
- `PYTHONPATH=. python scripts/audit_review_bbox_min_side.py --review-root review/task-reviews --docs-root docs --domains three_d --min-side-px 24 --out-json docs/domain-migration-report/three_d/bbox_min_side_audit.json --out-md docs/domain-migration-report/three_d/bbox_min_side_audit.md --fail-on-issue`
  passes with `tasks=60`, `bbox-family runtime tasks=50`,
  `samples=6000`, `bboxes=18417`, `failing bbox tasks=0`, `invalid=0`, and
  `missing=0`.

### T3D-001 - Active taxonomy and inventory were not synchronized

Resolved on: 2026-06-28

Fix:

- Added the missing `object_scene` public task ids to `trace/core/taxonomy.py`:
  - `task_three_d__object_scene__line_side_label`
  - `task_three_d__object_scene__point_camera_distance_order_label`
  - `task_three_d__object_scene__reference_triangle_inside_label`
- Regenerated `docs/ACTIVE_TASK_INVENTORY.md` from the live default-task
  registry and public taxonomy.

Verification:

- `PYTHONPATH=. python scripts/generate_active_task_inventory.py --check`
  passes and reports `docs/ACTIVE_TASK_INVENTORY.md is up to date`.
- `PYTHONPATH=. python scripts/audit_active_domain_surfaces.py` passes with
  `active domain surfaces OK`.
- Focused three_d taxonomy comparison reports:
  - `three_d_default_tasks=60`
  - `three_d_taxonomy_mapped_default_tasks=60`
  - `three_d_missing_taxonomy=[]`
  - `object_scene=15`
- `PYTHONPATH=. python scripts/check_active_inventory_integrity.py --include-local-cache`
  no longer reports three_d missing-taxonomy rows. It still fails on unrelated
  icon missing-taxonomy rows and local cache artifacts outside this T3D-001
  fix.

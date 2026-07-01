# Physics Post-Migration Audit Issues

Audit date: 2026-07-01

Scope: `physics` domain only. This report lists issues found by the post-migration checklist; it does not list passing checks.

Generated audit artifacts:

- `docs/domain-migration-report/physics/bbox_min_side_audit.md`
- `docs/domain-migration-report/physics/bbox_min_side_audit.json`
- `docs/domain-migration-report/physics/semantic_sampling_modulo_audit.md`
- `docs/domain-migration-report/physics/visual_candidate_modulo_audit.md`
- `docs/domain-migration-report/physics/prompt_concision_audit.md`
- `docs/domain-migration-report/physics/prompt_annotation_contracts/`
- `docs/domain-migration-report/physics/review_freshness_audit.md`
- `docs/domain-migration-report/physics/review_freshness_audit.json`

## PHYS-008 - Global active-inventory integrity gate is blocked by non-physics issues

Severity: Medium

Issue:

- The global active-inventory integrity check currently fails before it can be used as a clean acceptance signal for physics.
- The failures are outside physics, but they affect the repo-level post-migration gate.

Observed non-physics blockers:

- Missing puzzle taxonomy entries:
  - `task_puzzles__pipe_flow__misrotated_tile_label`
  - `task_puzzles__sheet_transform__fold_cut_result_label`
  - `task_puzzles__sheet_transform__fold_projection_result_label`
  - `task_puzzles__sheet_transform__overlay_union_result_label`
- With local-cache checking enabled, local cache artifacts are also reported, including `__pycache__` paths and `docs/domain-migration-report/charts/.ipynb_checkpoints`.

## PHYS-009 - Accepted solve-rate status is not recorded for active physics tasks

Severity: Follow-up

Issue:

- `review/feedback/review_feedback.sqlite` has task-audit rows for 50 active physics tasks.
- Prompt, image, annotation, distribution, code-review, and taxonomy-review flags are recorded as passed.
- `solve_rate_pass` is not accepted for any active physics task in that DB state.
- This is expected to remain open until solve-rate jobs are explicitly run and accepted.

Affected domain:

- `physics`: `0 / 50` accepted solve-rate statuses recorded.

## Resolved

### PHYS-001 - Semantic sampling still used modulo/cursor-style selection broadly

Resolved on: 2026-07-01

Fix:

- Replaced physics semantic support selection based on seed/hash/cursor modulo with seeded RNG choice over explicit supports or candidate lists.
- Added `resolve_support_choice` as the generic finite-support companion to the existing integer support helper.
- Removed the unused collision `selection_cursor` helper.

Verification:

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -B scripts/audit_semantic_sampling_modulo.py --root trace/tasks/physics --root trace/core --output docs/domain-migration-report/physics/semantic_sampling_modulo_audit.md`
- Result: `Needs refactor: 0`, `Needs manual review: 0`.

### PHYS-002 - Visual candidate selection still used modulo/index cycling

Resolved on: 2026-07-01

Fix:

- Replaced visual candidate selection for physics colors, option labels, palette offsets, meter/cylinder/thermometer fluids, and object fills with seeded RNG choice.
- Kept only deterministic assignment from already-selected palettes, currently gear-train per-gear fill cycling and review overlay colors.
- Regenerated affected physics task-review artifacts under `review/task-reviews`.

Verification:

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -B scripts/audit_visual_candidate_modulo.py --root trace/tasks/physics --root trace/core --output docs/domain-migration-report/physics/visual_candidate_modulo_audit.md`
- Result: `Random candidate selection needs refactor: 0`, `Sampling-time assignment needs review: 0`, `Needs manual review: 0`.
- Regenerated 34 affected task reviews; all affected task `distribution_review.json` files now pass.
- Review app reloads completed for the affected physics scenes. The final reload queue had no queued scenes; a separate stale `geometry/sector` entry was unrelated to this physics fix.

### PHYS-003 - `orbital_motion` migration-test status was blocked

Resolved on: 2026-07-01

Fix:

- Refreshed `review/task-reviews/physics/orbital_motion/migration_test_status.json` from `blocked` to `passed` after rerunning the listed scene checks.
- Confirmed the existing orbital task distribution reviews have no recorded failures.

Verification:

- `python -m json.tool prompts/physics/orbital_motion/physics_orbital_motion_v1.json >/tmp/physics_orbital_motion_v1.json`
- `PYTHONPATH=. python -m py_compile trace/tasks/physics/orbital_motion/*.py trace/tasks/physics/orbital_motion/shared/*.py`
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_physics_extension_tasks.py -k orbital`
- Result: `2 passed, 35 deselected`.
- `TRACE_SCENE_PACKAGE_REVIEW_SCENE=physics/orbital_motion PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_review_app.py tests/test_run_task_review.py tests/test_scene_package_migration_contracts.py tests/test_scene_package_review_candidate_contracts.py`
- Result: `94 passed`.

### PHYS-004 - Review artifacts were stale for most physics scenes

Resolved on: 2026-07-01

Fix:

- Added `scripts/audit_physics_review_freshness.py` to make physics review freshness auditable against generation/rendering inputs.
- Confirmed the current scene freshness marker is `scene_review_manifest.json`.
- Excluded `docs/domain-migration-report/physics/` from freshness inputs so editing the audit report does not make task-review artifacts stale.
- No review regeneration was needed after the all-physics inspection refresh for PHYS-006: the formal audit found 0 stale physics scenes and 0 missing scene manifests.

Verification:

- `PYTHONPATH=. python scripts/audit_physics_review_freshness.py`
- Result: `physics scenes checked: 36`, `stale scenes: 0`, `missing scene manifests: 0`, `scene workbooks present: 36`, `task workbooks present: 50`.
- `python -m json.tool docs/domain-migration-report/physics/review_freshness_audit.json >/tmp/physics_review_freshness_audit.json`
- `find review/task-reviews/physics -maxdepth 2 -name scene_review.xlsx | wc -l`
- Result: `36`.
- `find review/task-reviews/physics -maxdepth 3 -name 'task_physics__*.xlsx' | wc -l`
- Result: `50`.

### PHYS-005 - Segment annotation prompt hints missed canonical endpoint wording

Resolved on: 2026-07-01

Fix:

- Updated the affected segment and segment-set annotation prompt hints to use canonical endpoint-pair wording: `[[x0, y0], [x1, y1]]`.
- Added explicit `[x, y]` pixel-point endpoint wording where required by the annotation prompt audit.
- Normalized matching motion-graph task-doc annotation value wording.
- Regenerated affected task-review artifacts under `review/task-reviews`.

Affected tasks:

- `task_physics__analog_meter__meter_readout_value`
- `task_physics__collision__sticky_collision_direction_choice`
- `task_physics__collision__sticky_collision_speed_value`
- `task_physics__motion_graph__average_speed_value`
- `task_physics__motion_graph__interval_displacement_value`
- `task_physics__motion_graph__speed_change_state_choice`
- `task_physics__thermometer__temperature_conversion_value`
- `task_physics__wave_interference__path_difference_value`

Verification:

- `PYTHONPATH=. python scripts/audit_prompt_annotation_contracts.py --tasks <50 active physics task ids from review/task-reviews/physics> --samples-per-query-id 2 --workers 4 --output-dir docs/domain-migration-report/physics/prompt_annotation_contracts`
- Result: `audited 50 tasks, 74 expected query ids, 148 samples, 0 issues`.
- Focused affected-task audit result: `audited 8 tasks, 11 expected query ids, 22 samples, 0 issues`.
- Focused physics task tests passed: `21 passed`.
- Regenerated 8 affected task reviews; all regenerated distribution reviews passed.
- Review app scene reload queue completed with `status=succeeded`, `stale=false`, and no queued scenes.

### PHYS-006 - Physics task docs used compact one-line Program Contract sections

Resolved on: 2026-07-01

Fix:

- Added `scripts/normalize_physics_program_contract_docs.py`, an idempotent maintainer script for physics Program Contract doc sections.
- Normalized all 50 physics task docs under `docs/tasks/physics/` so each `## Program Contract` section exposes:
  - `Program:`
  - `Candidate set:`
  - `Operands:`
  - `Operation:`
  - `Output binding:`
  - `Annotation witnesses:`
  - `Query ids:`
- Preserved the existing concrete program expressions, task ids, query tables, Program Metadata, Answer Contract, Annotation Contract, prompt assets, configs, task source, and verifier behavior.
- Regenerated physics task-review inspection artifacts and scene workbooks under `review/task-reviews/physics` for all 50 active physics tasks across 36 scenes. Distribution artifacts and solve-rate were not rerun for this docs-only fix.

Verification:

- `PYTHONPATH=. python scripts/normalize_physics_program_contract_docs.py --root docs/tasks/physics --write`
- Result: `physics task docs scanned: 50`, `docs rewritten: 50`.
- `PYTHONPATH=. python scripts/normalize_physics_program_contract_docs.py --root docs/tasks/physics --check`
- Result: `physics task docs scanned: 50`, `docs requiring normalization: 0`.
- Custom structural scan confirmed all 50 physics task docs contain `Program:`, `Candidate set:`, `Operands:`, `Operation:`, `Output binding:`, `Annotation witnesses:`, and `Query ids:`.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -B scripts/run_task_review.py --tasks <50 physics task ids> --mode inspection --out-root review/task-reviews --workers 4`
- Result: regenerated 50 task inspection workbooks and 36 physics scene workbooks.
- Review app scene-scoped reloads were queued for all 36 physics scenes; final physics-only poll showed no active or queued physics reload scopes. The app subsequently moved on to unrelated non-physics stale scopes.

### PHYS-007 - Stale grounding terminology remained in a physics task doc

Resolved on: 2026-07-01

Fix:

- Replaced the stale grounding phrase with `selected stack region` in `docs/tasks/physics/stack_stability/task_physics__stack_stability__stability_status_label.md`.

Verification:

- `rg -n "<retired-grounding-term>" docs/tasks/physics prompts/physics trace/tasks/physics -S`
- Result: no matches.
- Review app reload completed after reloading `physics/stack_stability`; a separate stale `geometry/sector` entry was unrelated to this physics fix.

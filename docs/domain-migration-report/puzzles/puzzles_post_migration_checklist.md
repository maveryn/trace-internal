# Puzzles Post-Migration Audit Issues

Audit date: 2026-07-01

Scope: `puzzles` domain only. This report lists issues found by the post-migration checklist; it does not list passing checks.

Generated audit artifacts:

- `docs/domain-migration-report/puzzles/bbox_min_side_audit.md`
- `docs/domain-migration-report/puzzles/bbox_min_side_audit.json`
- `docs/domain-migration-report/puzzles/semantic_sampling_modulo_audit.md`
- `docs/domain-migration-report/puzzles/visual_candidate_modulo_audit.md`
- `docs/domain-migration-report/puzzles/prompt_concision_audit.md`
- `docs/domain-migration-report/puzzles/prompt_annotation_contracts/`
- `review/feedback-cleanup/retired_task_audit_cleanup_20260701T064806Z0000.md`
- `review/feedback-cleanup/retired_task_audit_cleanup_20260701T064806Z0000.json`

## Resolved

### PUZ-001 - Active taxonomy contained retired puzzle task ids

Resolved on: 2026-07-01

Fix:

- Deleted retired puzzle taxonomy entries from `trace/core/taxonomy.py`.
- Removed:
  - `task_puzzles__overlay__overlay_result_label`
  - `task_puzzles__paper_fold__paper_fold_result_label`
  - `task_puzzles__paper_fold_cut__paper_fold_cut_result_label`
  - `task_puzzles__pipe_flow__valve_toggle_label`

Verification:

- The retired puzzle ids are no longer present in the runtime registry.
- Current registry/review artifacts expose `60` active puzzle tasks.
- `docs/ACTIVE_TASK_INVENTORY.md` is currently stale from broader repo changes and should be refreshed separately; the current stale inventory state is not puzzle-specific.

### PUZ-002 - Review artifacts were stale for most puzzle scenes

Resolved on: 2026-07-01

Fix:

- Regenerated all active puzzle task-review artifacts under `review/task-reviews/`.
- Regenerated all 20 puzzle scene review workbooks.
- Reloaded every puzzle scene in the review app.

Verification:

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -B scripts/run_task_review.py --tasks <all-active-puzzle-task-ids> --mode inspection --out-root review/task-reviews --workers 4`
- Result: regenerated `60` active puzzle task reviews and scene workbooks for all `20` active puzzle scenes.
- `POST /api/reload/scene/puzzles/<scene_id>` for all active puzzle scenes.
- Final `GET /api/reload/status` result: `status=succeeded`, `in_progress=false`, `queued=false`, `stale_scenes=[]`.

### PUZ-003 - One bbox annotation was out of image bounds

Resolved on: 2026-07-01

Fix:

- Updated the Tents render-parameter resolver to fit sampled grid metrics to the configured canvas before rendering.
- Passed sampled `grid_rows` and `grid_cols` into Tents visual preparation so fit metadata is computed from the final board size.
- Regenerated the `tents` task-review artifacts under `review/task-reviews/`.

Verification:

- The previously invalid sample `review/task-reviews/puzzles/tents/task_puzzles__tents__violating_tent_label/data/single/0036.json` now has annotation `[161.0, 481.0, 221.0, 541.0]` within the 640x560 image.
- Its `render_spec.scene_bbox_px` is `[44.0, 4.0, 596.0, 556.0]` and `render_spec.unit_size_jitter.fit_to_canvas.enabled` is `true`.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -B scripts/audit_review_bbox_min_side.py --domains puzzles --min-side-px 24 --out-json docs/domain-migration-report/puzzles/bbox_min_side_audit.json --out-md docs/domain-migration-report/puzzles/bbox_min_side_audit.md --fail-on-issue`
- Result after current full puzzle review regeneration: `tasks=60`, `bbox_tasks=54`, `failures=0`, `invalid=0`, `missing=0`.

### PUZ-004 - Semantic and visual sampling used modulo/cursor selection

Resolved on: 2026-07-01

Fix:

- Replaced balance-scale semantic answer, panel-count, target-label, source-label, and repeated-label modulo selection with seeded RNG draws over explicit supports.
- Removed cursor-modulo option-label selection from voxel projection matching; explicit `answer_option_label` remains supported for pinned cases.
- Reworked cell-board cyclic filler color assignment and balance object-shape cycling so deterministic visual assignment no longer appears as random modulo candidate selection.
- Regenerated review artifacts for `balance_scale`, `cell_board`, and `voxel_cube` under `review/task-reviews/`.

Verification:

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -B scripts/audit_semantic_sampling_modulo.py --root trace/tasks/puzzles --root trace/core --output docs/domain-migration-report/puzzles/semantic_sampling_modulo_audit.md`
- Result: `Needs refactor: 0`, `Needs manual review: 0`.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -B scripts/audit_visual_candidate_modulo.py --root trace/tasks/puzzles --root trace/core --output docs/domain-migration-report/puzzles/visual_candidate_modulo_audit.md`
- Result: `Random candidate selection needs refactor: 0`, `Sampling-time assignment needs review: 0`, `Needs manual review: 0`.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest tests/test_puzzles_balance_scale_tasks.py tests/test_puzzles_cell_board_tasks.py tests/test_puzzles_voxel_cube_contracts.py`
- Result: `29 passed`.
- Reloaded `puzzles/balance_scale`, `puzzles/cell_board`, and `puzzles/voxel_cube` in the review app; `GET /api/reload/status` returned `status=succeeded`, `in_progress=false`, `queued=false`, and `stale_scenes=[]`.

### PUZ-007 - Puzzle prompt openings exposed renderer/style trivia

Resolved on: 2026-07-01

Fix:

- Rewrote Tents and Toggle Grid object descriptions so prompt openings describe the semantic puzzle surface rather than renderer treatments.
- Removed `card-style`, `blueprint-style`, `notebook-style`, and `console-style` from active prompt defaults.
- Regenerated the `tents` and `toggle_grid` task-review artifacts under `review/task-reviews/`.

Verification:

- `python -m json.tool prompts/puzzles/tents/puzzles_tents_v1.json`
- `python -m json.tool prompts/puzzles/toggle_grid/puzzles_toggle_grid_v1.json`
- `rg -n "blueprint-style|card-style|notebook-style|console-style" prompts/puzzles/tents prompts/puzzles/toggle_grid review/task-reviews/puzzles/tents review/task-reviews/puzzles/toggle_grid`
- Result: no remaining matches.

### PUZ-008 - Review feedback DB contained retired puzzle task-audit rows

Resolved on: 2026-07-01

Fix:

- Removed retired puzzle `task_audit` rows from `review/feedback/review_feedback.sqlite` with `scripts/cleanup_retired_task_audit_rows.py`.
- The cleanup wrote a SQLite backup to `review/feedback-cleanup/review_feedback.sqlite.retired_task_audit_cleanup_20260701T064806Z0000.bak`.

Deleted rows:

- `task_puzzles__arithmetic_panel__consecutive_window_sum_value`
- `task_puzzles__cell_board__minimum_color_set_distance_value`
- `task_puzzles__cell_board__scoped_attribute_count`
- `task_puzzles__counterfactual_board__board_dimension_count`
- `task_puzzles__counterfactual_board__board_line_count`
- `task_puzzles__polyomino_missing__rectangle_complement_piece`
- `task_puzzles__voxel_cube__cube_painted_face_count`

Verification:

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -B scripts/cleanup_retired_task_audit_rows.py --domain puzzles --apply`
- Result: `db_task_audit_rows_before=66`, `deleted_row_count=7`, `db_task_audit_rows_after=59`, `stale_row_count_after=0`.
- After the current full puzzle review regeneration, a direct registry/review-root/DB check reports `registry=60`, `review=60`, `db=60`, `db_stale=0`, and `db_missing=0`.

### PUZ-005 - Prompt/annotation contract audit reported broad active prompt defects

Resolved on: 2026-07-01

Fix:

- Tightened the prompt/annotation contract audit so it no longer reports duplicate or cosmetic issues as contract defects:
  - Missing `Example JSON:` is reported once, not again as invalid JSON.
  - Segment annotation prompts require the canonical endpoint form `[[x0, y0], [x1, y1]]`.
  - Bbox annotation prompts require the canonical box form `[x0, y0, x1, y1]`.
  - Body-level format prose is no longer treated as a defect when the prompt has canonical output sections.
- Normalized all active puzzle prompt output templates to named `Answer format`, `Annotation format`, and `Example JSON` sections.
- Fixed canonical bbox/segment wording for active cell-board, matchstick, and word-search annotation prompts.
- Regenerated all active puzzle task reviews and scene workbooks under `review/task-reviews/`.

Verification:

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -B scripts/audit_prompt_annotation_contracts.py --tasks <all-active-puzzle-task-ids> --output-dir docs/domain-migration-report/puzzles/prompt_annotation_contracts`
- Result: `audited 60 tasks, 65 expected query ids, 65 samples, 0 issues`.
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -B scripts/run_task_review.py --tasks <all-active-puzzle-task-ids> --mode inspection --out-root review/task-reviews --workers 4`
- Result: regenerated all `60` active puzzle task reviews and all `20` puzzle scene workbooks.
- Review app reload for all puzzle scenes completed with `status=succeeded`, `in_progress=false`, `queued=false`, and `stale_scenes=[]`.

### PUZ-006 - Puzzle task docs used compact Program Contract sections

Resolved on: 2026-07-01

Fix:

- Added `scripts/normalize_puzzle_program_contract_docs.py`, an idempotent maintainer script for puzzle Program Contract doc sections.
- Normalized all `60` active puzzle task docs under `docs/tasks/puzzles/` so each `## Program Contract` section exposes:
  - `Program:`
  - `Candidate set:`
  - `Operands:`
  - `Operation:`
  - `Output binding:`
  - `Annotation witnesses:`
  - `Query ids:`
- Preserved the existing compact program expression in each doc and expanded it into reviewable fields without changing task ids, runtime taxonomy, prompts, renderers, samplers, or verifiers.

Verification:

- `PYTHONDONTWRITEBYTECODE=1 python -B scripts/normalize_puzzle_program_contract_docs.py --check`
- Result: `puzzle task docs scanned: 60`, `docs requiring normalization: 0`.
- Custom structural scan confirmed all `60` puzzle task docs contain `Program:`, `Candidate set:`, `Operands:`, `Operation:`, `Output binding:`, `Annotation witnesses:`, and `Query ids:`.
- Additional spot check found no `unspecified`, `scalar`, or `unordered` placeholder schema wording in the normalized Program Contract sections.

## PUZ-009 - Accepted solve-rate status is not recorded for active puzzle tasks

Severity: followup

Category: distribution

Scope: all active puzzle tasks

Issue:

- `review/feedback/review_feedback.sqlite` has task-audit rows for all 60 active puzzle tasks.
- `solve_rate_pass` is not accepted for any active puzzle task in that DB state.
- This remains open until solve-rate jobs are explicitly run and accepted.

Affected domain:

- `puzzles`: `0 / 60` accepted solve-rate statuses recorded.

## PUZ-010 - Global active-inventory integrity gate is blocked by local cache artifacts

Severity: followup

Category: automated gate

Scope: repo-level gate

Issue:

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python -B scripts/check_active_inventory_integrity.py --include-local-cache` currently fails because local cache artifacts exist.
- The failure is not puzzle-specific, but it blocks using the global integrity gate as a clean acceptance signal.

Observed cache roots include:

- `docs/.ipynb_checkpoints`
- `docs/domain-migration-report/charts/.ipynb_checkpoints`
- `docs/domain-migration-report/physics/.ipynb_checkpoints`
- `docs/domain-migration-report/puzzles/.ipynb_checkpoints`
- `scripts/__pycache__`
- `tests/__pycache__`

Proposed follow-up fix:

- Clean or ignore local cache artifacts according to the repo policy, then rerun the integrity gate.

# Symbolic Post-Migration Checklist Issues

Audit date: 2026-06-29

Scope: `symbolic` domain only. This report records identified issues only.

Minimal provenance:

- Active symbolic tasks from `docs/ACTIVE_TASK_INVENTORY.md`: 50.
- Active symbolic scenes: 13.
- Scene migration status files: 13/13 scenes have
  `manual_code_audit_status.json`, `taxonomy_review_status.json`, and
  `migration_test_status.json` with `passed: true`; 0 scalar-annotation
  checklist misses.
- Review task folders under `review/task-reviews/symbolic`: 50 active, 0
  missing.
- Distribution reviews: 50 present, 0 failing, 0 warning-bearing. Three
  4-choice label tasks had marginal 100-sample answer-frequency failures during
  the stale-artifact refresh, then passed the required 300-sample supplemental
  validation and now have passing 300-sample distribution review artifacts.
- `bbox_min_side_audit.md`: 50 tasks checked, 43 bbox-family runtime tasks,
  0 failing bbox tasks.
- `semantic_sampling_modulo_audit.md`: 0 needs-refactor and 0 manual-review
  semantic modulo sites.
- `visual_candidate_modulo_audit.md`: 0 random visual candidate modulo sites.
  Two manual-review rows were triaged as deterministic notation/topology
  wraparound, not random candidate selection.
- `prompt_concision_audit.md`: 138 rendered prompts, 50 tasks covered, 69
  observed query ids covered, 0 incomplete query ids or generation errors.
- `prompt_annotation_contracts/prompt_annotation_contract_audit.md`: 69
  sampled query ids, 69 samples, 0 annotation-prompt issues.

Audit artifacts generated in this pass:

- `docs/domain-migration-report/symbolic/bbox_min_side_audit.json`
- `docs/domain-migration-report/symbolic/bbox_min_side_audit.md`
- `docs/domain-migration-report/symbolic/semantic_sampling_modulo_audit.md`
- `docs/domain-migration-report/symbolic/visual_candidate_modulo_audit.md`
- `docs/domain-migration-report/symbolic/prompt_concision_audit.md`
- `docs/domain-migration-report/symbolic/prompt_annotation_contracts/`
- `docs/domain-migration-report/symbolic/distribution_escalation_300/task_answer_distribution_report.json`

Commands run:

- `PYTHONPATH=. python scripts/generate_active_task_inventory.py --check`
- `PYTHONPATH=. python scripts/check_active_inventory_integrity.py --include-local-cache`
- `PYTHONPATH=. python scripts/audit_active_domain_surfaces.py`
- `PYTHONPATH=. python scripts/audit_review_bbox_min_side.py --review-root review/task-reviews --docs-root docs --domains symbolic --min-side-px 24 --out-json docs/domain-migration-report/symbolic/bbox_min_side_audit.json --out-md docs/domain-migration-report/symbolic/bbox_min_side_audit.md --fail-on-issue`
- `PYTHONPATH=. python scripts/audit_semantic_sampling_modulo.py --root trace/tasks/symbolic --root trace/core --output docs/domain-migration-report/symbolic/semantic_sampling_modulo_audit.md`
- `PYTHONPATH=. python scripts/audit_visual_candidate_modulo.py --root trace/tasks/symbolic --root trace/core --output docs/domain-migration-report/symbolic/visual_candidate_modulo_audit.md`
- `PYTHONPATH=. python scripts/audit_prompt_concision.py --tasks <50 symbolic task ids> --query-id-coverage --samples-per-query-id 1 --include-all-prompts --output docs/domain-migration-report/symbolic/prompt_concision_audit.md --workers 4 --max-attempts 200 --max-total-samples-per-task 1024`
- `PYTHONPATH=. python scripts/audit_prompt_annotation_contracts.py --tasks <50 symbolic task ids> --samples-per-query-id 1 --output-dir docs/domain-migration-report/symbolic/prompt_annotation_contracts --workers 4 --max-attempts 200 --max-total-samples-per-task 1024`
- `TRACE_SCENE_PACKAGE_REVIEW_SCENE=symbolic/<scene_id> PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_review_app.py tests/test_run_task_review.py tests/test_scene_package_migration_contracts.py tests/test_scene_package_review_candidate_contracts.py` for all 13 symbolic scenes.
- `PYTHONPATH=. python scripts/cleanup_retired_task_audit_rows.py --domain symbolic --output-root review/feedback-cleanup`
- `PYTHONPATH=. python scripts/cleanup_retired_task_audit_rows.py --domain symbolic --output-root review/feedback-cleanup --apply`
- `PYTHONPATH=. python scripts/run_task_review.py --tasks task_symbolic__clock__hand_angle_value,task_symbolic__clock__offset_readout,task_symbolic__organic_structure__bond_order_count,task_symbolic__agent_automaton__agent_final_pose_label,task_symbolic__agent_automaton__future_grid_label --mode inspection --out-root review/task-reviews --random-count 100 --max-attempts-per-instance 400 --workers 4 --skip-scene-workbooks`
- `POST /api/reload/scene/symbolic/clock`
- `POST /api/reload/scene/symbolic/organic_structure`
- `POST /api/reload/scene/symbolic/agent_automaton`
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_cleanup_retired_task_audit_rows.py tests/test_audit_prompt_annotation_contracts.py`
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_symbolic_clock_readout_tasks.py tests/test_symbolic_clock_readout_contracts.py tests/test_symbolic_clock_compare_tasks.py tests/test_symbolic_organic_structure_tasks.py tests/test_symbolic_automaton_tasks.py`
- Custom structural check over `docs/tasks/symbolic/**/task_symbolic__*.md` verifying all 50 `## Program Contract` sections have more than two nonblank lines and include `Program:`, `Candidate set:`, `Operands:`, `Operation:`, `Output binding:`, `Annotation witnesses:`, and `Query ids:`.
- `TRACE_SCENE_PACKAGE_REVIEW_SCENE=symbolic/<scene_id> PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_scene_package_migration_contracts.py tests/test_scene_package_review_candidate_contracts.py` for all 13 symbolic scenes.
- `PYTHONPATH=. python -B scripts/generate_active_task_inventory.py`
- `find . -path ./.git -prune -o \( -name '.ipynb_checkpoints' -o -name '__pycache__' \) -prune -exec rm -rf {} +`
- `PYTHONPATH=. python -B scripts/generate_active_task_inventory.py --check`
- `PYTHONPATH=. python -B scripts/check_active_inventory_integrity.py --include-local-cache`
- `PYTHONPATH=. python -B scripts/run_task_review.py --tasks <50 symbolic task ids> --mode full --out-root review/task-reviews --random-count 100 --count-per-query-id 100 --max-attempts-per-instance 400 --workers 4 --skip-scene-workbooks`
- `POST /api/reload/scene/symbolic/<scene_id>` for all 13 symbolic scenes.
- `GET /api/reload/status` returned `status=succeeded`, `in_progress=false`,
  and no `stale_scenes`.
- `PYTHONPATH=. python -B scripts/run_task_review.py --tasks task_symbolic__logic_gate_circuit__output_value_label,task_symbolic__logic_gate_circuit__satisfying_assignment_label,task_symbolic__morse_code__word_morse_match_label --mode distribution --out-root review/task-reviews --random-count 300 --count-per-query-id 300 --max-attempts-per-instance 800 --workers 4 --skip-scene-workbooks`
- `POST /api/reload/scene/symbolic/logic_gate_circuit`
- `POST /api/reload/scene/symbolic/morse_code`
- `PYTHONPATH=. python -B scripts/check_task_answer_distribution.py --tasks task_symbolic__logic_gate_circuit__output_value_label,task_symbolic__logic_gate_circuit__satisfying_assignment_label,task_symbolic__morse_code__word_morse_match_label --count-per-query-id 300 --max-attempts-per-instance 800 --workers 4 --out docs/domain-migration-report/symbolic/distribution_escalation_300`

## Open Issues

### SYM-004 - Review DB has no accepted solve-rate status for symbolic tasks

Severity: Medium

Category: calibration / review status

Scope:

- `review/feedback/review_feedback.sqlite`
- active `symbolic` tasks

Issue:

- The `task_audit` rows for symbolic have no accepted solve-rate status.
- Current DB counts from the read-only query after retired-row cleanup:
  - rows: `50`
  - active review tasks: `50`
  - stale rows: `0`
  - `prompt_pass=50`
  - `image_pass=50`
  - `annotation_pass=50`
  - `distribution_pass=50`
  - `code_review_pass=50`
  - `taxonomy_review_pass=50`
  - `solve_rate_pass=0`

Follow-up fix:

- Do not run solve-rate as part of this report-only pass.
- After retired rows are cleaned up and source/review blockers are fixed, run
  current symbolic solve-rate calibration when explicitly requested and update
  the review app status for accepted tasks.

## Resolved Issues

### SYM-001 - Review artifacts are stale for eight symbolic scenes

Resolved: 2026-06-29

Severity: Medium

Category: review artifacts / migration freshness

Scope:

- `review/task-reviews/symbolic/`
- 50 active symbolic task review folders across all 13 symbolic scenes.

Fix:

- Regenerated current review artifacts under `review/task-reviews` for all 50
  active symbolic tasks. The original stale set covered eight scenes, but the
  refresh was expanded to all 13 symbolic scenes because the `SYM-006` task-doc
  updates touched every symbolic task contract.
- Reloaded all 13 symbolic scenes in the review app with
  `POST /api/reload/scene/symbolic/<scene_id>`.
- Verified the review app reload status completed with `status=succeeded`,
  `in_progress=false`, and no `stale_scenes`.

Verification:

- Review task folders under `review/task-reviews/symbolic`: 50 active, 0
  missing.
- `bbox_min_side_audit.py` reports 50 tasks checked, 43 bbox-family runtime
  tasks, 0 failures, 0 invalid, and 0 missing.
- `audit_prompt_concision.py` regenerated 138 rendered prompts.
- `audit_prompt_annotation_contracts.py` reports 50 tasks, 69 expected query
  ids, 69 samples, and 0 issues.
- Fresh distribution reviews are present for all 50 active symbolic tasks. Three
  marginal 100-sample 4-choice answer-frequency failures were escalated and are
  tracked as resolved in `SYM-008`.
- No solve-rate job was run for this fix.

### SYM-008 - Fresh symbolic distribution reviews have three failing tasks

Resolved: 2026-06-29

Severity: Medium

Category: distribution / calibration freshness

Scope:

- `task_symbolic__logic_gate_circuit__output_value_label`
- `task_symbolic__logic_gate_circuit__satisfying_assignment_label`
- `task_symbolic__morse_code__word_morse_match_label`

Issue:

- Regenerating all symbolic task reviews for `SYM-001` surfaced three marginal
  100-sample answer-frequency failures in 4-choice label tasks.
- 100-sample failure details:
  - `task_symbolic__logic_gate_circuit__output_value_label`:
    `output_one_label` had `max_answer_frequency=0.35`, threshold
    `0.3333333333333333`.
  - `task_symbolic__logic_gate_circuit__satisfying_assignment_label`:
    `assignment_outputs_one_label` had `max_answer_frequency=0.34`, threshold
    `0.3333333333333333`.
  - `task_symbolic__morse_code__word_morse_match_label` had overall
    `max_answer_frequency=0.35`, threshold `0.3333333333333333`.

Fix:

- Treated the failures as required 4-choice distribution escalations rather
  than immediate sampler defects.
- Ran supplemental same-sampler validation at 300 samples per query id.
- Regenerated the official review distribution artifacts for the three affected
  tasks at 300 samples per query id so the review app reads the validated
  passing distribution state.
- Reloaded `symbolic/logic_gate_circuit` and `symbolic/morse_code` in the
  review app.

Verification:

- `task_symbolic__logic_gate_circuit__output_value_label`: 300-sample
  supplemental report passes; worst query `output_one_label` has
  `max_answer_frequency=87/300=0.29`.
- `task_symbolic__logic_gate_circuit__satisfying_assignment_label`: 300-sample
  supplemental report passes; worst query `assignment_outputs_one_label` has
  `max_answer_frequency=92/300=0.30666666666666664`.
- `task_symbolic__morse_code__word_morse_match_label`: 300-sample supplemental
  report passes with `max_answer_frequency=85/300=0.2833333333333333`.
- Task-level scan over `review/task-reviews/symbolic/*/*/distribution_review.json`
  reports 50 symbolic distribution reviews and 0 failures.

### SYM-002 - Segment annotation prompts use non-canonical endpoint wording

Resolved: 2026-06-29

Severity: High

Category: prompt / annotation contract

Scope:

- `prompts/symbolic/clock/symbolic_clock_v1.json`
- `prompts/symbolic/organic_structure/symbolic_organic_structure_v1.json`
- `task_symbolic__clock__hand_angle_value`
- `task_symbolic__clock__offset_readout`
- `task_symbolic__organic_structure__bond_order_count`

Fix:

- Normalized symbolic segment annotation hints to
  `[[x0, y0], [x1, y1]]`.
- Added explicit wording that each nested endpoint is an `[x, y]`
  pixel-space point.
- Regenerated affected inspection review artifacts under
  `review/task-reviews`.
- Reloaded `symbolic/clock` and `symbolic/organic_structure` in the review app.

Verification:

- `audit_prompt_annotation_contracts.py` now reports 50 tasks, 69 sampled
  query ids, 69 samples, and 0 annotation-prompt issues.
- `pytest` symbolic clock/organic/automaton task checks passed.

### SYM-003 - Review feedback DB contains retired symbolic task rows

Resolved: 2026-06-29

Severity: Medium

Category: review workspace state

Scope:

- `review/feedback/review_feedback.sqlite`

Fix:

- Ran the retired-task cleanup script for `domain=symbolic`.
- Deleted the two retired `music_staff` task rows from `task_audit`:
  - `task_symbolic__music_staff__chord_harmony_label`
  - `task_symbolic__music_staff__dominant_chord_count`
- Backup:
  `review/feedback-cleanup/review_feedback.sqlite.retired_task_audit_cleanup_20260629T044831Z0000.bak`
- Apply receipt:
  `review/feedback-cleanup/retired_task_audit_cleanup_20260629T044831Z0000.json`

Verification:

- Post-cleanup dry run:
  `review/feedback-cleanup/retired_task_audit_cleanup_20260629T045238Z0000.json`
- Current symbolic `task_audit` rows: 50.
- Current stale symbolic `task_audit` rows: 0.
- `tests/test_cleanup_retired_task_audit_rows.py` passed.

### SYM-005 - Agent automaton prompt template creates awkward capitalization

Resolved: 2026-06-29

Severity: Low

Category: prompt quality

Scope:

- `prompts/symbolic/agent_automaton/symbolic_agent_automaton_v1.json`
- `task_symbolic__agent_automaton__agent_final_pose_label`
- `task_symbolic__agent_automaton__future_grid_label`

Fix:

- Replaced the affected template variant from
  `{rule_instruction} After {steps} steps, {question_text}` to
  `{rule_instruction} After {steps} steps. {question_text}`.
- Regenerated both affected `agent_automaton` inspection review artifacts.
- Reloaded `symbolic/agent_automaton` in the review app.

Verification:

- `prompt_concision_audit.md` regenerated with 138 rendered prompts, 50 tasks,
  and 69 query ids covered.
- Search found no remaining rendered `After <n> steps, Which...` prompt in
  symbolic prompt assets or regenerated symbolic review artifacts.

### SYM-006 - Many Program Contract sections are schema-only placeholders

Resolved: 2026-06-29

Severity: Medium

Category: task docs / taxonomy review

Scope:

- `docs/tasks/symbolic/`

Fix:

- Expanded all 50 symbolic task-doc `## Program Contract` sections to expose
  the concrete program in the same reviewable shape:
  - `Program:`
  - `Candidate set:`
  - `Operands:`
  - `Operation:`
  - `Output binding:`
  - `Annotation witnesses:`
  - `Query ids:`
- The 37 originally short sections were expanded from schema-only placeholders.
- The 13 already-detailed sections were lightly normalized to the same labeled
  surface.
- Follow-up on 2026-07-01 added the missing `Candidate set:` labels to the two
  symbolic docs that still lacked one after later task-doc additions:
  `chemical_equation/missing_coefficient_value` and
  `truth_table/satisfying_row_count`.
- This was docs-only; task code, configs, prompts, review artifacts, and solve
  rate were not changed for this issue.

Verification:

- Custom structural check over all `60` symbolic task docs reports:
  - `short_sections=0`
  - `missing_required_labels=0`
- `PYTHONDONTWRITEBYTECODE=1 python -B scripts/normalize_reviewed_domain_program_contract_docs.py --check`
  reports `reviewed-domain task docs scanned: 444` and
  `docs requiring normalization: 0`.
- Scene-scoped migration tests passed for all 13 symbolic scenes.

### SYM-007 - Global active-inventory preflight fails outside symbolic

Resolved: 2026-06-29

Severity: Low

Category: global audit preflight

Scope:

- `docs/ACTIVE_TASK_INVENTORY.md`
- `trace/core/taxonomy.py`
- repo-local cache/checkpoint directories

Fix:

- Added missing explicit taxonomy entries for:
  - `task_geometry__regular_polygon_decomposition__marked_piece_area_value`
  - `task_geometry__regular_polygon_decomposition__wedge_area_from_side_apothem_value`
  - `task_icons__pair_grid__reference_color_pair_match_label`
  - `task_icons__pair_grid__reference_transform_match_label`
- Regenerated `docs/ACTIVE_TASK_INVENTORY.md`.
- Removed repo-local `.ipynb_checkpoints` and `__pycache__` directories.

Verification:

- `generate_active_task_inventory.py --check` reports
  `docs/ACTIVE_TASK_INVENTORY.md is up to date`.
- `check_active_inventory_integrity.py --include-local-cache` reports
  `active inventory integrity OK`.

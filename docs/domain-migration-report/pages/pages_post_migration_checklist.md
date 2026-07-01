# Pages Post-Migration Checklist Issues

Audit date: 2026-07-01

Scope: `pages` domain only. This report records identified issues only.

Audit artifacts generated in this pass:

- `docs/domain-migration-report/pages/bbox_min_side_audit.json`
- `docs/domain-migration-report/pages/bbox_min_side_audit.md`
- `docs/domain-migration-report/pages/semantic_sampling_modulo_audit.md`
- `docs/domain-migration-report/pages/visual_candidate_modulo_audit.md`
- `docs/domain-migration-report/pages/prompt_concision_audit.md`
- `docs/domain-migration-report/pages/prompt_annotation_contracts/`
- `docs/domain-migration-report/pages/text_legibility_audit.txt`

Commands run:

- `PYTHONPATH=. python scripts/generate_active_task_inventory.py --check`
- `PYTHONPATH=. python scripts/check_active_inventory_integrity.py --include-local-cache`
- `PYTHONPATH=. python scripts/audit_active_domain_surfaces.py`
- `PYTHONPATH=. python scripts/audit_review_bbox_min_side.py --domains pages --min-side-px 24 --out-json docs/domain-migration-report/pages/bbox_min_side_audit.json --out-md docs/domain-migration-report/pages/bbox_min_side_audit.md --fail-on-issue`
- `PYTHONPATH=. python scripts/audit_semantic_sampling_modulo.py --root trace/tasks/pages --root trace/core --output docs/domain-migration-report/pages/semantic_sampling_modulo_audit.md`
- `PYTHONPATH=. python scripts/audit_visual_candidate_modulo.py --root trace/tasks/pages --root trace/core --output docs/domain-migration-report/pages/visual_candidate_modulo_audit.md`
- `PYTHONPATH=. python scripts/audit_prompt_concision.py --tasks <80 active pages task ids> --query-id-coverage --samples-per-query-id 1 --include-all-prompts --output docs/domain-migration-report/pages/prompt_concision_audit.md --workers 4 --max-attempts 200 --max-total-samples-per-task 1024`
- `PYTHONPATH=. python scripts/audit_prompt_annotation_contracts.py --tasks <80 active pages task ids> --samples-per-query-id 1 --output-dir docs/domain-migration-report/pages/prompt_annotation_contracts --workers 4 --max-attempts 200 --max-total-samples-per-task 1024`
- `PYTHONPATH=. python scripts/audit_text_legibility.py --scan-root trace/tasks/pages --scan-root trace/tasks/pages/shared --runtime-coverage --runtime-domain pages --runtime-sample-count 1 --runtime-max-attempts 200 --fail-generation-errors`

## Open Issues

### PAGES-001 - Review feedback DB contains retired pages task rows

Severity: Medium

Category: review workspace state

Scope:

- `review/feedback/review_feedback.sqlite`
- retired `pages` task ids

Issue:

- The active registry and `review/task-reviews/pages` contain 80 pages tasks,
  but the feedback DB `task_audit` table contains 83 `task_pages__...` rows.
- Three rows are for retired task ids:
  - `task_pages__profile_card_grid__field_extremum_profile_label`
  - `task_pages__step_list__nth_step_detail_label`
  - `task_pages__step_list__nth_step_title_label`

Observed in:

- SQLite comparison of `task_audit` rows against active pages task ids.

Follow-up fix:

- Run the retired-task review cleanup script for `domain=pages` after the
  current domain review wave is complete.
- Keep the generated DB backup and cleanup receipt.

### PAGES-003 - Seventeen bbox-family annotation tasks violate the 24 px minimum-side rule

Severity: High

Category: annotation geometry / rendering

Scope:

- Existing pages task-review samples under `review/task-reviews/pages`
- Bbox-family annotation tasks

Issue:

- The bbox min-side audit inspected 8,200 samples and 21,052 bboxes.
- Seventeen pages tasks produced bbox witnesses with at least one side below
  24 px.
- Failing tasks:
  - `task_pages__calendar_event_grid__category_slot_day_count`: min side
    `13.866`, failures `394`
  - `task_pages__calendar_event_grid__date_filled_slot_count`: min side
    `13.866`, failures `152`
  - `task_pages__calendar_event_grid__date_for_category_slot_label`: min side
    `13.867`, failures `100`
  - `task_pages__calendar_event_grid__date_slot_category_label`: min side
    `13.867`, failures `100`
  - `task_pages__category_grid__category_item_count`: min side `8.422`,
    failures `250`
  - `task_pages__category_grid__category_slot_item_label`: min side `8.5`,
    failures `254`
  - `task_pages__mixed_infographic_page__module_condition_item_count`: min
    side `10.518`, failures `94`
  - `task_pages__mixed_infographic_page__module_field_ranked_item_label`: min
    side `9.0`, failures `100`
  - `task_pages__mixed_infographic_page__module_field_total_value`: min side
    `3.222`, failures `116`
  - `task_pages__mixed_infographic_page__module_field_value_label`: min side
    `8.0`, failures `35`
  - `task_pages__mixed_infographic_page__module_two_field_condition_item_label`:
    min side `10.0`, failures `100`
  - `task_pages__profile_card_grid__value_for_named_profile_field`: min side
    `6.0`, failures `100`
  - `task_pages__sectioned_infographic__section_filtered_item_label`: min side
    `14.0`, failures `13`
  - `task_pages__sectioned_infographic__section_item_count`: min side `15.0`,
    failures `80`
  - `task_pages__step_list__nth_step_field_label`: min side `9.0`, failures
    `99`
  - `task_pages__step_list__step_after_named_step_label`: min side `13.0`,
    failures `99`
  - `task_pages__step_list__step_for_detail_label`: min side `13.0`,
    failures `50`

Observed in:

- `docs/domain-migration-report/pages/bbox_min_side_audit.md`
- `docs/domain-migration-report/pages/bbox_min_side_audit.json`
- Follow-up regeneration removed the prior failures for
  `task_pages__navigation_flow__same_group_target_label` and
  `task_pages__schema__relationship_cardinality_label`; both now have observed
  min side `24.0`.

Follow-up fix:

- For each affected scene, expand the projected witness boxes only if the
  expanded box remains the same semantic witness.
- Otherwise, adjust the rendered target geometry or change the annotation
  schema to the correct point/segment family.
- Regenerate affected task reviews and rerun the bbox audit.

### PAGES-004 - Runtime text-legibility metadata reports failures in mixed infographic and profile-card scenes

Severity: High

Category: rendering / text legibility

Scope:

- `trace/tasks/pages/mixed_infographic_page`
- `trace/tasks/pages/profile_card_grid`

Issue:

- Runtime text-legibility coverage found required text failures on one sample
  per task.
- Failing tasks:
  - `task_pages__mixed_infographic_page__module_condition_item_count`:
    `failure_count=2`
  - `task_pages__mixed_infographic_page__module_field_ranked_item_label`:
    `failure_count=6`
  - `task_pages__mixed_infographic_page__module_field_total_value`:
    `failure_count=6`
  - `task_pages__mixed_infographic_page__module_two_field_condition_item_label`:
    `failure_count=4`
  - `task_pages__profile_card_grid__field_ranked_profile_label`:
    `failure_count=31`
  - `task_pages__profile_card_grid__profile_for_field_value`:
    `failure_count=25`
  - `task_pages__profile_card_grid__value_for_named_profile_field`:
    `failure_count=38`

Observed in:

- `docs/domain-migration-report/pages/text_legibility_audit.txt`

Follow-up fix:

- Inspect the rendered text-legibility metadata for these scenes.
- Fix text fitting, contrast, protected layout boxes, or annotation target
  sizing before regenerating affected task reviews.

### PAGES-005 - Semantic sampling still uses modulo/cursor-style selection broadly

Severity: Medium

Category: semantic sampling

Scope:

- `trace/tasks/pages/`
- `trace/tasks/pages/shared/`

Issue:

- The semantic sampling modulo audit reports:
  - raw line findings: `178`
  - grouped selection sites: `153`
  - needs refactor: `79`
  - needs manual review: `3`
- Affected areas include calendar, calendar_event_grid, concept_map,
  control_board, instruction_panel, mixed_infographic_page, navigation_flow,
  process_flow, profile_card_grid, schedule, schema, shared hierarchy and
  infographic helpers, step_list, timeline, web_action, and workspace.

Observed in:

- `docs/domain-migration-report/pages/semantic_sampling_modulo_audit.md`

Follow-up fix:

- Replace semantic support selection based on `% len(...)`,
  `resolve_selection_index(...) % len(...)`, hash modulo, or cursor cycling
  with explicit seeded RNG support draws and recorded support probabilities.
- Review the three manual-review sites before deciding whether they are
  semantic sampling or deterministic assignment.

### PAGES-006 - Visual candidate selection still uses modulo/index cycling

Severity: Medium

Category: visual sampling / rendering variation

Scope:

- `trace/tasks/pages/`
- `trace/tasks/pages/shared/`

Issue:

- The visual candidate modulo audit reports:
  - random candidate selection needs refactor: `26`
  - sampling-time assignment needs review: `45`
  - needs manual review: `20`
  - likely safe deterministic assignment: `23`
- Affected areas include calendar, calendar_event_grid, concept_map,
  hero_callout_infographic, profile_card_grid, schedule, schema, shared
  infographic helpers, timeline, web_action, and workspace.

Observed in:

- `docs/domain-migration-report/pages/visual_candidate_modulo_audit.md`

Follow-up fix:

- Refactor true random visual candidate selection away from modulo/index
  cycling.
- Leave only deterministic cycling over already-sampled style or palette lists,
  and document those as deterministic assignment when needed.

### PAGES-007 - Some pages annotation prompt hints miss canonical wording

Severity: Medium

Category: prompt / annotation contract

Scope:

- `prompts/pages/navigation_flow/`
- `prompts/pages/schema/`

Issue:

- Prompt/annotation contract audit found six annotation prompt warnings.
- Bbox prompts missing canonical `[x0, y0, x1, y1]` notation:
  - `task_pages__navigation_flow__navigation_path_target_label`
    - `menu_path_target_label`
    - `ribbon_group_command_label`
    - `sidebar_tree_target_label`
  - `task_pages__navigation_flow__same_group_target_label`
- Segment-set prompts missing explicit pixel-space wording:
  - `task_pages__schema__join_path_length_value`
  - `task_pages__schema__relationship_count`

Observed in:

- `docs/domain-migration-report/pages/prompt_annotation_contracts/annotation_prompt_audit.md`

Follow-up fix:

- Normalize active annotation hints to canonical bbox and segment wording.
- Regenerate affected prompt-review artifacts if prompt assets change.

### PAGES-008 - Legacy page style axes remain alongside shared information-scene styling

Severity: Medium

Category: rendering/style taxonomy

Scope:

- `configs/domains/pages/calendar_event_grid.yaml`
- `configs/domains/pages/process_flow.yaml`
- `configs/domains/pages/record_table.yaml`
- `configs/domains/pages/schedule.yaml`
- `configs/domains/pages/timeline.yaml`

Issue:

- These scenes still expose `style_variant_weights` and
  `balanced_style_variant_sampling` axes.
- Pages domain policy says structured pages should use the shared
  `information_scene` treatment/palette baseline and avoid parallel
  non-semantic theme axes for the same visual role.
- These axes may be legitimate structural variants in some scenes, but current
  names and metadata make them look like legacy parallel style samplers.

Observed in:

- Config/source scan for `style_variant_weights` and
  `balanced_style_variant_sampling`.

Follow-up fix:

- Review each listed scene and classify the axis as either structural scene
  variation or non-semantic styling.
- Move non-semantic style choices into the shared `information_scene` layer, or
  rename/record structural variants so they are not confused with style
  treatment/palette sampling.

### PAGES-009 - Global inventory gate fails during pages audit

Severity: Low

Category: global audit gate

Scope:

- `docs/ACTIVE_TASK_INVENTORY.md`
- active registry / taxonomy integrity checks

Issue:

- `scripts/generate_active_task_inventory.py --check` reports
  `docs/ACTIVE_TASK_INVENTORY.md is stale`.
- `scripts/check_active_inventory_integrity.py --include-local-cache` reports:
  - missing taxonomy for icon tasks:
    `task_icons__icon_grid__distinct_color_count`,
    `task_icons__icon_grid__distinct_type_count`
  - stale active inventory
  - existing local `__pycache__` artifacts
- A pages-specific comparison found `80` active pages tasks and `80` pages
  tasks in `docs/ACTIVE_TASK_INVENTORY.md`, with no pages missing/retired
  mismatch.

Observed in:

- Inventory gate commands listed above.

Follow-up fix:

- Handle this as a global cleanup after all domain review passes, not as a
  pages scene/task fix.

### PAGES-010 - Review DB has no accepted solve-rate status for active pages tasks

Severity: Medium

Category: calibration / review status

Scope:

- `review/feedback/review_feedback.sqlite`
- active `pages` tasks

Issue:

- Active pages task-audit rows currently show:
  - `prompt_pass=80`
  - `image_pass=80`
  - `annotation_pass=80`
  - `distribution_pass=80`
  - `code_review_pass=80`
  - `taxonomy_review_pass=80`
  - `solve_rate_pass=0`
- Solve-rate was not run as part of this report-only pass.

Observed in:

- SQLite read-only query over `review/feedback/review_feedback.sqlite`.

Follow-up fix:

- After source/review blockers are fixed and review artifacts are current, run
  current pages solve-rate calibration only when explicitly requested.

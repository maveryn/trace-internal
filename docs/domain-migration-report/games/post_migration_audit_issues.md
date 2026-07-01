# Games Post-Migration Audit Issues

Audit date: 2026-06-27

Scope: `games` domain only. This report records identified issues only.

## Resolved

### GM-009 - 3D Tic-Tac-Toe winning-line annotation remains a homogeneous `bbox_set`

Resolved on: 2026-06-27

Resolution:

- Re-reviewed `task_games__tic_tac_toe_3d__winning_move_cell_label` and kept
  its `bbox_set` annotation contract.
- The annotated witnesses are homogeneous under the intended contract: all
  three boxes are game-board cells that form the completed winning line. The
  selected move cell is not a separate external option panel; it is one of the
  board cells in the completed line.
- Updated the prompt hint and task doc to describe the annotation as the three
  board cells in the completed winning line, instead of describing separate
  selected-cell and support-cell roles.

Verification:

- This was a prompt/doc wording clarification only. No answer, annotation
  schema, renderer, sampling, verifier, or review-artifact regeneration was
  required.

### GM-008 - Retired games task audit rows removed from feedback DB

Resolved on: 2026-06-27

Fix:

- Added `scripts/cleanup_retired_task_audit_rows.py`, an explicit review
  workspace cleanup command that compares `task_audit` rows against active
  task-review manifests and removes rows for retired task ids only when run
  with `--apply`.
- Ran the cleanup for `domain=games` against
  `review/feedback/review_feedback.sqlite`.
- Deleted the five stale retired games task rows:
  - `task_games__2048__score_value`
  - `task_games__bingo__line_sum_extremum_value`
  - `task_games__darts__ring_count`
  - `task_games__dominoes__extendable_first_play_count`
  - `task_games__dots_and_boxes__capture_move_count`
- Wrote an auditable cleanup receipt and DB backup under
  `review/feedback-cleanup/`.

Verification:

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_cleanup_retired_task_audit_rows.py`
  passed.
- Dry-run command found exactly 5 stale games rows before deletion:
  `PYTHONPATH=. python scripts/cleanup_retired_task_audit_rows.py --domain games --output-root review/feedback-cleanup`
- Applied command deleted exactly 5 rows and produced zero stale rows after
  cleanup:
  `PYTHONPATH=. python scripts/cleanup_retired_task_audit_rows.py --domain games --output-root review/feedback-cleanup --apply`
- Applied cleanup receipt:
  `review/feedback-cleanup/retired_task_audit_cleanup_20260627T083416Z0000.json`
- Backup:
  `review/feedback-cleanup/review_feedback.sqlite.retired_task_audit_cleanup_20260627T083416Z0000.bak`

### GM-007 - Modulo/cursor-based games sampling audit is clean

Resolved on: 2026-06-27

Fix:

- Reran the semantic and visual modulo/cursor audits against the current games
  source after other-agent refactors.
- Updated the supporting audit reports under
  `docs/domain-migration-report/games/`.
- The remaining modulo sites are classified as deterministic render/review
  cycling or explicit review-harness round-robin, not task semantic sampling.

Verification:

- `PYTHONPATH=. python scripts/audit_semantic_sampling_modulo.py --root trace/tasks/games --root trace/core --output docs/domain-migration-report/games/semantic_sampling_modulo_audit.md`
  now reports:
  - `Needs refactor: 0`
  - `Needs manual review: 0`
- `PYTHONPATH=. python scripts/audit_visual_candidate_modulo.py --root trace/tasks/games --root trace/core --output docs/domain-migration-report/games/visual_candidate_modulo_audit.md`
  now reports:
  - `Random candidate selection needs refactor: 0`
  - `Sampling-time assignment needs review: 0`
  - `Needs manual review: 0`

### GM-006 - Dots-and-boxes option labels are visually ordered

Resolved on: 2026-06-27

Fix:

- Updated `task_games__dots_and_boxes__completable_box_label` generation so
  the six displayed option boxes are assigned labels after sorting by board
  row and column.
- Preserved balanced `target_label` sampling by choosing distractor boxes on
  both sides of the correct box's visual rank, so the requested answer label
  remains the correct option.
- Added a focused contract assertion that rendered option-label centers sort
  visually as `A, B, C, D, E, F`.
- Regenerated the full `dots_and_boxes` scene review artifacts under
  `review/task-reviews`.

Verification:

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_games_dots_and_boxes_contracts.py` passed with 9 tests.
- `PYTHONPATH=. python scripts/run_task_review.py --tasks task_games__dots_and_boxes__completable_box_label,task_games__dots_and_boxes__owned_box_count,task_games__dots_and_boxes__three_sided_box_count --mode full --out-root review/task-reviews` passed distribution review for all three tasks and regenerated the scene workbook.
- Focused artifact scan checked 100 regenerated
  `completable_box_label` samples and found zero visual-order violations.

### GM-005 - Games annotation prompt coordinate notation normalized

Resolved on: 2026-06-27

Fix:

- Normalized bbox prompt hints from `[x1, y1, x2, y2]` to
  `[x0, y0, x1, y1]`.
- Normalized segment prompt hints from `[[x1, y1], [x2, y2]]` to
  `[[x0, y0], [x1, y1]]`.
- Tightened segment prompt hints so endpoint points are explicitly described as
  `[x, y]` points.
- Removed negative annotation-format wording from:
  - `task_games__2048__merge_count`
  - `task_games__radial_hunt_board__marked_piece_destination_count`
  - `task_games__sixteen_soldiers__marked_piece_destination_count`
- Updated `canonical_annotation_coordinate_notation_audit.md` with the
  resolved source-scan result.
- Did not regenerate task-review artifacts because this was a prompt-only
  wording normalization with no answer, annotation, rendering, sampling, or
  verifier contract changes.

Verification:

- JSON validation passed for all 51 `prompts/games/**/*.json` prompt bundles.
- Source scan reports zero legacy coordinate prompt slots.
- Source scan reports zero negative annotation-format prompt slots.
- Source scan reports zero canonical segment hints missing explicit `[x, y]`
  endpoint wording.

### GM-004 - Simple category operands removed from query-id surfaces

Resolved on: 2026-06-27

Fix:

- Demoted simple color/player/state operands from query ids to sampled task
  parameters while preserving the public task ids.
- Updated the following tasks to expose only `query_id == "single"`:
  - `task_games__backgammon__point_state_count`
  - `task_games__checkers__piece_state_count`
  - `task_games__dots_and_boxes__owned_box_count`
  - `task_games__hex__candidate_neighbor_count`
  - `task_games__reversi__frontier_disc_count`
  - `task_games__tic_tac_toe_3d__layer_piece_count`
- Added explicit sampled operands:
  - Backgammon: `target_checker_color`, `target_stack_state`
  - Checkers: `target_player`, `piece_state_kind`
  - Dots-and-boxes: `target_owner`
  - Hex: `neighbor_target_state`
  - Reversi: `target_player`
  - 3D Tic-Tac-Toe layer count: `target_player`
- Updated prompt bundles, scene configs, task docs, and tests to use the new
  single-query contracts.
- Kept game-rule query ids where side/state changes the rule predicate rather
  than acting as a simple category operand.

Verification:

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_games_backgammon_board_contracts.py tests/test_games_checkers_move_count_contracts.py tests/test_games_dots_and_boxes_contracts.py tests/test_games_hex_board_contracts.py tests/test_games_reversi_move_count_contracts.py tests/test_games_reversi_move_count_scene_config.py tests/test_games_tic_tac_toe_3d_tasks.py` passed with 68 tests.
- `PYTHONPATH=. python scripts/run_task_review.py --tasks task_games__backgammon__point_state_count,task_games__checkers__piece_state_count,task_games__dots_and_boxes__owned_box_count,task_games__hex__candidate_neighbor_count,task_games__reversi__frontier_disc_count,task_games__tic_tac_toe_3d__layer_piece_count --mode full --out-root review/task-reviews` passed distribution review for all six tasks and regenerated their task/scene review artifacts.
- The review app rejected full reload as designed for the shared app, then
  accepted scene-scoped reloads for all six affected games scenes. Final reload
  status reported `succeeded`, `stale: false`, and no queued scopes.

### GM-003 - Bbox annotation minimum-side audit passes for games

Resolved on: 2026-06-27

Fix:

- Converted `task_games__sliding_block__sliding_block_move_result_label` from a
  heterogeneous `bbox_set` over moved source blocks plus the selected option
  panel to a role-keyed `bbox_map` with:
  - `source_board`
  - `selected_option`
- Updated the prompt annotation hint and example JSON for the new `bbox_map`
  contract.
- Updated the task doc annotation schema from `bbox_set` to `bbox_map`.
- Added a shared `bbox_map_annotation_artifacts` helper for role-keyed bbox
  annotations.
- Regenerated all `sliding_block` review artifacts and the scene workbook.

Verification:

- `PYTHONPATH=. python scripts/run_task_review.py --tasks task_games__sliding_block__block_orientation_count,task_games__sliding_block__movable_block_count,task_games__sliding_block__sliding_block_blocker_count,task_games__sliding_block__sliding_block_move_result_label --mode full --out-root review/task-reviews` passed distribution review for all four `sliding_block` tasks.
- Focused sample check confirms 100/100 `sliding_block_move_result_label`
  review samples now use `annotation_gt.type == "bbox_map"` with exactly
  `source_board` and `selected_option` keys.
- `PYTHONPATH=. python scripts/audit_review_bbox_min_side.py --domains games --min-side-px 24 --out-json docs/domain-migration-report/games/bbox_min_side_audit.json --out-md docs/domain-migration-report/games/bbox_min_side_audit.md --fail-on-issue` passes with zero failing bbox tasks across 160 games tasks.

### GM-002 - `sliding_block` and `sokoban` review samples record shared games style/noise metadata

Resolved on: 2026-06-27

Fix:

- Updated `sliding_block` and `sokoban` scene configs and scene defaults to use post-image noise `apply_prob: 0.5`.
- Added top-level `trace_payload.background` and `trace_payload.post_image_noise` to both scene output builders.
- Added `render_spec.panel_scene_style` for both scene output builders while preserving existing scene-local render metadata.
- Regenerated task-review artifacts for:
  - `task_games__sliding_block__block_orientation_count`
  - `task_games__sliding_block__movable_block_count`
  - `task_games__sliding_block__sliding_block_blocker_count`
  - `task_games__sliding_block__sliding_block_move_result_label`
  - `task_games__sokoban__box_goal_status_count`
  - `task_games__sokoban__closest_box_goal_label`
  - `task_games__sokoban__push_stand_cell_label`

Verification:

- `PYTHONPATH=. python scripts/run_task_review.py --tasks task_games__sliding_block__block_orientation_count,task_games__sliding_block__movable_block_count,task_games__sliding_block__sliding_block_blocker_count,task_games__sliding_block__sliding_block_move_result_label,task_games__sokoban__box_goal_status_count,task_games__sokoban__closest_box_goal_label,task_games__sokoban__push_stand_cell_label --mode full --out-root review/task-reviews` passed distribution review for all seven tasks and regenerated both scene workbooks.
- Focused metadata check confirms all regenerated samples expose `trace_payload.background.style_spec.kind == "panel_scene_style"`, `trace_payload.post_image_noise.apply_prob == 0.5`, and `render_spec.panel_scene_style`.

### GM-001 - Active games taxonomy/inventory is synchronized

Resolved on: 2026-06-27

Fix:

- Added taxonomy mappings for:
  - `task_games__minesweeper__forced_mine_cell_label`
  - `task_games__sliding_block__block_orientation_count`
- Removed stale retired games mappings for:
  - `task_games__match3__target_clear_swap_label`
  - `task_games__minecraft__reachable_ore_stack_count`
  - `task_games__minesweeper__reveal_outcome_label`
  - `task_games__minesweeper__satisfied_clue_count`
- Regenerated `docs/ACTIVE_TASK_INVENTORY.md`.

Verification:

- `PYTHONPATH=. python scripts/generate_active_task_inventory.py --check` passes.
- Focused games taxonomy check reports 160 active games review task ids, 160 games taxonomy entries, no games tasks missing from taxonomy, and no stale games taxonomy entries.
- `PYTHONPATH=. python scripts/check_active_inventory_integrity.py` still reports missing taxonomy mappings in other domains; no games tasks remain in that failure list.

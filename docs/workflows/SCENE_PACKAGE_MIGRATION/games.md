# Games Scene-Package Migration Roadmap

This is the tracked migration roadmap for migrating the `games` domain under
`docs/workflows/SCENE_PACKAGE_MIGRATION/README.md`.
Use `docs/workflows/SCENE_PACKAGE_MIGRATION/GAMES_SCENE_REFACTOR_GUIDELINES.md`
for scene-local source layout and helper-role boundaries.

Do not treat the current source layout as proof that the domain is migrated.
The games code has already been moved into scene packages, but much of it is a
shallow copy-split migration: sibling public task files often contain the same
entire old scene module and only one registered class differs.

## Status

- Domain: `games`
- Current static source inventory: 50 active scene folders, 161 public-looking
  task files under `trace/tasks/games/<scene_id>/`, plus one empty stale alias
  directory: `trace/tasks/games/twenty_forty_eight/`.
- Registry check status: structurally restored. `trace/tasks/__init__.py`
  imports games scene-package modules and `import trace.tasks` currently
  registers 161 default games tasks.
- Proposed task count: keep the current taxonomy unless a scene review finds a
  real task-contract merge/split. This roadmap is a structural migration plan,
  not a coverage expansion.
- Migration state: not complete. The whole domain is structurally routed, but
  objective-ownership completion must be explicit. Pending-scene tracking is an
  in-progress marker only; final completion requires the objective-complete
  registry and gates described in `README.md`.

## Non-Negotiable Gates

Before `games` can be marked migrated:

1. `trace.tasks` imports every active games scene-package task.
2. Registered/default games task count matches the domain inventory expected by
   the task docs and taxonomy.
3. Every active task id maps to
   `trace/tasks/games/<scene_id>/<objective_contract>.py`.
4. Every public task file defines exactly one registered public task class.
5. No public task file defines sibling public task ids or sibling public task
   classes.
6. No public task file is a wrapper around `_SourceTask`, `FixedQueryVariantTaskMixin`,
   `QuerySubsetTaskMixin`, or a shared full-output generator.
7. No sibling public task files are exact or near-exact copies.
8. Scene `shared/` modules do not return complete `TaskOutput` objects for
   multiple public objectives.
9. Scene `shared/` modules do not branch over public `task_id` or objective
   contracts to choose answer/annotation programs.
10. Scene `shared/` modules do not accept `task_id`, `query_id`,
    `supported_query_ids`, `objective_contract`, public task names, or public
    query names as routing inputs.
11. Public task files translate query-id branches into semantic arguments before
    calling scene shared helpers.
12. Scene `shared/` modules do not export `SUPPORTED_*_QUERY_IDS` routing
    tables or `sample_for_query(...)` style routers.
13. Domain `shared/` contains only cross-scene games helpers, not scene-local
    helpers.
14. Games code/config/docs use `annotation`, not `evidence`.
15. Games code/config/docs contain no active `task_group` routing or metadata
    references.
16. Configs are scene-keyed under `configs/domains/games/<scene_id>.yaml`.
17. Task-complexity config, helper calls, metadata fields, and docs are removed
    from migrated games scenes and are not replaced by a new
    difficulty/complexity proxy.
18. Task-coverage config, helper calls, metadata fields, generated active
    summaries, and docs are removed from migrated games scenes and are not
    replaced by a new coverage proxy.
19. Task-review artifacts are regenerated for changed active games tasks;
    stale folders for retired or renamed games task ids are purged.
20. Games scenes satisfy the shared scene-package prompt-asset, defaults-ownership, and
    no-query-weight gates defined in `README.md`.

## One-Pass Execution Model

This roadmap is designed for one complete games-domain migration pass. Do not
run a pilot and stop, and do not do a shallow path/layout pass before returning
later for objective ownership. The pass should proceed as:

1. Preflight the domain once.
2. Process every scene in the fixed order used by this roadmap.
3. For each scene, finish source cleanup, config/prompt/doc sync, complexity
   and task-coverage removal, task-review refresh/stale cleanup, and local
   checks before moving to the next scene.
4. After all scenes pass their local gates, do one domain-shared consolidation
   checkpoint.
5. Run whole-domain validation and only then mark `games` migrated.

The final domain-shared checkpoint is part of the same migration pass. It is
not permission to skip scene-local cleanup and it is not a separate future
refactor.

## Preflight Fixes Before Scene Loop

1. Demote `games` from any completed migration allowlist until the domain is
   actually complete. In the current repo state this means removing `games`
   from `MIGRATED_SCENE_PACKAGE_DOMAINS`. **Done in preflight.**
2. Keep the structurally routed games scenes in `MIGRATED_SCENE_PACKAGE_SCENES`
   only if runtime code needs scene-package routing before cleanup is done.
3. Add all games scenes to
   `SCENE_PACKAGE_OBJECTIVE_OWNERSHIP_PENDING_SCENES["games"]` at preflight,
   as an in-progress marker. A scene is complete only after it is added to the
   explicit objective-complete registry; do not infer completion merely from
   removal from pending. **Done in preflight.**
4. Extend enforcement tests so the current games failure modes are impossible:
   sibling exact-copy detection, sibling public task id detection, wrapper-only
   public task detection, shared full-output dispatcher detection, and
   `task_group` literal scrub after a domain is marked migrated.
5. Replace games import behavior in `trace/tasks/__init__.py` with a single
   scene-package import path. **Done in preflight to restore runtime registry;
   objective-ownership enforcement remains pending for all games scenes.**
6. Remove games task-complexity plumbing from migrated scenes: config knobs,
   helper calls, trace metadata, task docs, and public task-file dependencies.
7. Decide the global complexity ABI sequence before editing games task files.
   The repo currently still has core `TaskComplexity`/`task_complexity`
   surfaces. Games migration must remove games-owned complexity semantics, not
   add per-task dummy complexity builders. If a temporary compatibility shim is
   still needed before the core ABI is removed, keep it outside objective-owned
   public task files and mark it as global cleanup debt.
8. Do not start by moving duplicated scene code into `trace/tasks/games/shared/`.
   Fix objective ownership scene-by-scene first. Keep reusable scene mechanics
   in each scene's `shared/` package during this pass unless a helper is already
   a tiny, obvious cross-scene primitive.
9. Delete empty or stale scene aliases before the scene loop. In the current
   repo state, `trace/tasks/games/twenty_forty_eight/` is an empty stale alias
   for the public `2048` scene and should not become a compatibility scene.
   **Done in preflight.**
10. Remove or shrink `trace/tasks/games/shared/fixed_query_task.py`; migrated
    public tasks should not be implemented as fixed-query wrappers.
11. Remove games task-coverage plumbing from migrated scenes: config knobs,
    helper calls, trace metadata, task docs, generated active summaries, and
    public task-file dependencies. Historical coverage notes may remain only as
    clearly inactive project context outside active runtime/task docs.

Preflight should be done once. After that, the work moves through scenes in the
order below without returning to broad domain rewrites until the final
consolidation checkpoint.

## Domain Shared Boundary

Use a one-pass domain strategy with a final shared-code checkpoint:

1. Scene loop: fix each scene locally. Extract duplicated sibling-task code into
   `trace/tasks/games/<scene_id>/shared/`, and keep each public task file
   responsible for its own objective sampling, answer binding, annotation
   binding, dynamic prompt slots, and task trace.
2. Final checkpoint: after all scene packages are cleaned, compare scene-local
   helpers and promote only genuinely repeated, scene-neutral primitives into
   `trace/tasks/games/shared/` before final validation.

Keep these in `trace/tasks/games/shared/` only if they remain reused by two or
more scenes:

- `layout.py`: unit-size jitter, slack-based layout jitter, and coordinate
  projection helpers.
- `sampling.py`: generic named-axis and support sampling helpers.
- `scene_style.py`, `style_common.py`, `visual_defaults.py`: shared game canvas
  treatment and noise defaults.
- `text.py`: required game text rendering and legibility recording.
- `marking.py`: required semantic markers and marker legibility.
- `option_layout.py`: generic option-panel arrangement rules.
- `piece_board_renderer.py`, `piece_board_rules.py`: chess/checkers-like
  reusable piece-board primitives, if still used by multiple scenes.

Move out of domain shared:

- Any helper that mentions one scene id or one game's rule vocabulary.
- Any helper that constructs a full task sample for one scene only.
- Any shared helper whose only caller is one scene.
- Any mixin that pins one query id by wrapping a multi-objective base task.
- Any complexity scoring helper once migrated scenes no longer call it.

Do not promote helpers to domain shared during a scene migration just because
two dirty copy-split scenes currently look similar. First remove the copy-split
structure. Then decide whether the cleaned scene helpers are actually the same
abstraction.

Scene-local `shared/` should own board/rule dataclasses, legal move helpers,
scene renderers, style variants, annotation projection primitives, and
validation helpers for that scene. Public task files should own the objective:
target sampling, answer binding, annotation binding, dynamic prompt slots, and
task-specific trace payload.

## Current Debt Summary

Static AST/source checks found these issue classes:

- Exact copy-split scenes: many sibling files have identical byte size and
  define all sibling task ids/classes.
- Multi-task public files: many public task files define multiple public task
  ids for the same scene, with only one class registered.
- Missing literal task ids: several newer scenes use constants or inherited
  attributes that the static check cannot tie directly to a single public file.
- Legacy config naming: many games files still import
  `core.task_group_config` or pass variables named `task_group_defaults`.
- Retired complexity plumbing: games files and config still contain
  task-complexity helpers/weights/metadata that should be removed, not renamed
  or replaced by a new proxy.
- Task reviews: changed active games tasks need current `review/task-reviews`
  artifacts; only retired or renamed task-id folders should be purged.
- Registry gap: `trace/tasks/__init__.py` currently imports charts and many
  non-games modules, but not games scene packages.
- Empty stale alias: `trace/tasks/games/twenty_forty_eight/` exists but has no
  task files. Delete it rather than treating it as a public scene or leaving a
  compatibility alias.
- Prompt/default/query cleanup: legacy scenes may still violate the shared scene-package
  prompt-asset, defaults-ownership, or no-query-weight gates. Fix those during
  each scene migration rather than treating them as later cleanup.

## Scene Loop

Do the domain scene-by-scene in the order of the sections below. Each scene is a
complete migration unit. Do not move to the next scene while the current scene
still has copy-split files, wrapper-only task files, sibling public task ids, or
unclear objective ownership.

For each scene:

1. Confirm the task ids and current source files.
2. Decide whether the listed tasks remain separate or need a merge/split.
3. Extract scene mechanics into `trace/tasks/games/<scene_id>/shared/`.
4. Rewrite every public task file so it owns one objective program.
5. Remove sibling public task ids/classes from every public task file.
6. Move query-id resolution and objective branches into the public task files;
   pass only semantic arguments into scene shared helpers.
7. Remove `task_id`, `query_id`, `supported_query_ids`, public task names, and
   public query names from scene `shared/` function signatures and routing
   logic.
8. Delete retired modules or stale wrappers.
9. Replace `task_group` naming in scene-owned code/config with scene/task
   naming.
10. Apply the shared scene-package defaults-ownership gate to scene defaults and config.
11. Remove scene-owned task-complexity helpers, config, metadata, and docs.
12. Apply the shared scene-package no-query-weight gate to the migrated scene config.
13. Ensure prompts and payloads say `annotation`, not `evidence`.
14. Apply the shared scene-package prompt-asset gate, including prompt schema upgrades
    needed for static and required slots.
15. Update the scene config, prompt assets, task docs, taxonomy/imports, and
    review paths.
16. Purge stale task-review folders for retired or renamed task ids. Regenerate
    task-review artifacts for changed active task ids and reload the review app
    index.
17. Run cheap static checks for the scene, including an identity-free scan of
    the scene `shared/` package.
18. Mark the scene section complete in this roadmap before moving on.

The scene order is the roadmap order: `2048`, `backgammon`, `battleship`,
`bingo`, `bowling`, `brick_breaker`, `bubble_shooter`, `cards`, `checkers`,
`chess`, `chess_variant`, `circular_chess`, `connect_four`, `crossing`,
`darts`, `dominoes`, `dots_and_boxes`, `go`, `hex`, `irregular_link_board`,
`lane_runner`, `ludo_board`, `mancala_pit_board`, `marble_chain`, `match3`,
`minecraft`, `minesweeper`, `minigolf`, `nine_mens_morris`, `pacman`,
`pinball_table`, `platformer`, `pool`, `racing_track`, `radial_hunt_board`,
`reversi`, `rhythm`, `rule_override_board`, `sixteen_soldiers`,
`sliding_block`, `snake`, `snakes_ladders`, `sokoban`, `solitaire`,
`space_shooter`, `tetris`, `tic_tac_toe_3d`, `tower_defense`,
`tower_draughts_board`, `ultimate_tictactoe`.

## Per-Scene Completion Checklist

Add a short completion note under each scene while executing the pass:

```text
Completion note:
- source ownership:
- split/merge decision:
- scene shared helpers:
- domain shared candidates deferred:
- config/prompt/docs updated:
- defaults ownership cleaned:
- query weights removed:
- prompt wording/static slots externalized:
- complexity removed:
- task reviews regenerated/stale folders purged:
- checks:
- final post-migration review:
- identity-free shared-code scan:
- blockers:
```

This note is intentionally operational. It lets the pass continue scene by
scene without losing the reason a scene was considered complete.

## Per-Scene Roadmap

### 2048

- Tasks: `max_tile_value`, `merge_count`, `move_result_board_label`,
  `score_value`.
- Current risk: files are not exact-size copies, but share large chunks of
  objective and output construction. Review for near-duplicate code.
- Shared scene helpers: board representation, move simulation, merge tracing,
  result-board option rendering, tile style, annotation projection from cells.
- Public task ownership:
  - `merge_count.py`: choose move, compute merge source pairs, answer integer
    count, annotation `point_pair_set`.
  - `score_value.py`: choose move, compute score from merge events, answer
    integer value, annotation `point_pair_set`.
  - `max_tile_value.py`: choose move, compute resulting max tile, answer
    integer value, annotation result max-tile cell bboxes.
  - `move_result_board_label.py`: choose move, construct candidate result
    boards, answer option label, annotation selected result-board option bbox.
- Migration action: extract common simulation/rendering only; remove any shared
  base generator that binds answer/annotation for all four tasks.
- Completion note:
  - source ownership: complete. Each public task file owns target sampling,
    answer binding, annotation binding, and task-specific construction mode.
  - split/merge decision: kept all four tasks separate because the objective
    contracts and annotation types differ.
  - scene shared helpers: split by role under `2048/shared/`: `defaults.py`,
    `state.py`, `mechanics.py`, `sampling.py`, `rendering.py`, `prompts.py`,
    `annotations.py`, and `output.py`. The old broad `common.py`, `scene.py`,
    and `task_support.py` files were removed.
  - domain shared candidates deferred: visual option-board layout, panel
    background/style resolution, unit-size/layout jitter plumbing, and common
    scene-package `TaskOutput` assembly shape.
  - config/prompt/docs updated: active task docs and prompt metadata remain
    scene-keyed and annotation-based.
  - complexity removed: 2048 task output no longer emits task-complexity
    payloads.
  - task reviews regenerated/stale folders purged:
    `review/task-reviews/games/2048/` regenerated after the split-file
    cleanup; distribution checks passed for all four active tasks.
  - checks: `python -m compileall -q trace/tasks/games/2048`; registry
    generation smoke for all four 2048 tasks.
  - blockers: none.

### backgammon

- Tasks: `destination_count`, `point_state_count`.
- Status: migrated.
- Public task changes:
  - retired `task_games__backgammon__legal_move_count`;
  - retired `task_games__backgammon__blocked_destination_count`;
  - added `task_games__backgammon__destination_count`.
- Multi-query contracts:
  - `destination_count` owns the destination-point counting program with
    integer answers and `bbox_set` annotation. Its query ids are
    `legal_move_count`, `hit_move_count`, and `blocked_destination_count`.
  - `point_state_count` owns the checker-stack point-counting program with
    integer answers and `bbox_set` annotation. Its query ids are
    `black_single_checker_point_count`, `white_single_checker_point_count`,
    `black_two_or_more_checker_point_count`, and
    `white_two_or_more_checker_point_count`.
- Scene-local shared code now uses the split-file pattern:
  `defaults.py`, `state.py`, `mechanics.py`, `sampling.py`, `rendering.py`,
  `prompts.py`, `annotations.py`, and `output.py`.
- Complexity surface removed from task output/config for this migrated scene.
- Taxonomy, config, active task docs, inventory, and scene-package migration
  allowlist were updated with the two active public ids.
- Task reviews regenerated under `review/task-reviews/games/backgammon/`;
  retired task review folders were purged.
- Checks:
  - `python -m compileall -q trace/tasks/games/backgammon`;
  - registry generation smoke for both tasks and all seven query ids;
  - full default-task taxonomy scan;
  - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q
    tests/test_scene_package_migration_contracts.py tests/test_run_task_review.py`.
- Final post-migration review: checked the final backgammon package after
  validation for stale public ids, wrapper-only task files, duplicated
  objective-level output logic in shared files, prompt/annotation terminology,
  retired task-review folders, and domain-shared promotion candidates.
- Blockers: none.

### battleship

- Tasks: `last_ship_cell_label`, `ship_cell_status_count`,
  `ship_status_count`.
- Status: migrated.
- Public task changes: no task-id rename was needed; all three public ids
  already match their objective contracts.
- Public task ownership:
  - `ship_status_count.py` owns sunk/partial ship counting, integer answer, and
    `keyed_point_set_map` annotation. It resolves the public query branch and
    target answer locally before calling shared placement/render helpers.
  - `ship_cell_status_count.py` owns named-ship hit/unhit cell counting,
    integer answer, and `point_set` annotation. It translates the public branch
    into the semantic `target_cell_status` locally.
  - `last_ship_cell_label.py` owns the single missing-cell option-label task,
    string answer, selected-cell `point_set` annotation, target ship sampling,
    and option-label assignment.
- Scene-local shared code now uses the split-file pattern:
  `defaults.py`, `state.py`, `mechanics.py`, `sampling.py`, `rendering.py`,
  `annotations.py`, and `output.py`. Shared code is identity-free: it receives
  semantic values and scene state, not public `task_id` / `query_id` routing
  arguments.
- Complexity surface removed from task output/config/helper export for this
  migrated scene.
- Taxonomy, config, active task docs, tests, and scene-package migration
  allowlist were updated with the three active public ids.
- Task reviews regenerated under `review/task-reviews/games/battleship/`;
  distribution checks passed for all three active tasks.
- Checks:
  - `python -m compileall -q trace/tasks/games/battleship`;
  - identity-free shared-code scan:
    `rg -n "task_id|query_id|supported_query_ids|SUPPORTED_.*QUERY|objective_contract|TaskOutput|register_task|sample_.*query|sample_.*axes"
    trace/tasks/games/battleship/shared -g '*.py'` returned no matches;
  - registry generation smoke for all three tasks and all five query ids;
  - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q
    tests/test_games_battleship_grid_contracts.py
    tests/test_games_battleship_grid_scene_config.py
    tests/test_scene_package_migration_contracts.py tests/test_run_task_review.py`.
- Final post-migration review: checked the final Battleship package after
  validation for stale public ids, wrapper-only task files, duplicated
  objective-level output logic in shared files, prompt/annotation terminology,
  retired task-review folders, and domain-shared promotion candidates.
- Blockers: none.

### bingo

- Tasks: `called_number_mark_count`, `completed_line_count`,
  `line_sum_extremum_value`, `near_complete_line_count`.
- Current risk: exact copy-split.
- Shared scene helpers: bingo card generation, call/mark state, line
  enumeration, strikethrough/highlight rendering.
- Public task ownership:
  - completed/near-complete line count own line predicates and line/cell
    annotation.
  - called-number mark count owns called-number predicate and marked-cell
    annotation.
  - line-sum extremum owns rank/extremum line selection and numeric answer.
- Migration action: extract card/line primitives; keep each line/count/sum
  objective local.

### bowling

- Tasks: `first_pin_hit_label`, `spare_path_label`.
- Current risk: not an exact-size copy-split in the static inventory, but must
  still pass wrapper and shared-dispatch checks before it can be marked clean.
- Shared scene helpers: lane geometry, pin placement, path collision helpers,
  lane renderer.
- Public task ownership:
  - `first_pin_hit_label.py`: target first collision and pin bbox annotation.
  - `spare_path_label.py`: candidate path construction, selected path label,
    annotation path endpoints or selected path witness.
- Migration action: remove `FixedQueryVariantTaskMixin` usage if present; task
  files must own their own objective sampling.

### brick_breaker

- Tasks: `hit_row_remaining_count`, `next_hit_label`, `paddle_catch_label`.
- Current risk: exact copy-split.
- Shared scene helpers: playfield geometry, brick grid, straight trajectory
  simulation, paddle/catch-lane renderer.
- Public task ownership:
  - next hit label owns first-hit target and brick annotation.
  - paddle catch label owns catch lane/option target and annotation.
  - hit row remaining count owns post-hit row predicate and remaining-brick
    annotation.

### bubble_shooter

- Tasks: `drop_count`, `pop_color_label`, `pop_count`.
- Current risk: exact copy-split.
- Shared scene helpers: hex/packed bubble grid, same-color component search,
  support/drop computation, launcher/options renderer.
- Public task ownership:
  - pop count owns landed color/component and popped bubble annotation.
  - drop count owns post-pop unsupported bubble computation.
  - pop color label owns candidate color/options and selected color target.

### cards

- Tasks: `blackjack_best_hand_label`, `exact_triple_count`,
  `higher_than_reference_count`, `longest_run_length`,
  `missing_card_to_complete_hand_label`, `poker_best_hand_label`,
  `poker_draw_card_label`, `same_suit_as_reference_count`,
  `trick_taking_winner_label`, `trick_winning_play_label`.
- Current risk: exact copy-split across ten files.
- Shared scene helpers: card dataclasses, deck helpers, hand layout, card
  renderer, poker/blackjack/trick primitives, annotation projection.
- Public task ownership:
  - reference-count tasks own reference card selection and counted-card
    annotation.
  - multiplicity/run tasks own rank/run predicates and card-set annotation.
  - poker/blackjack/trick tasks own their game-specific evaluator and selected
    hand/play annotation.
  - missing/draw tasks own candidate-option construction and selected option
    annotation.
- Migration action: split card evaluator helpers from task objectives. Do not
  keep one `cards` base generator with a task-id switch.

### checkers

- Tasks: `max_capture_chain_length`, `move_count`, `piece_mobility_count`,
  `piece_state_count`.
- Current risk: exact copy-split.
- Shared scene helpers: board/piece state, legal move/capture enumeration,
  capture-chain search, renderer.
- Public task ownership:
  - move count owns legal/capture destination predicate and landing-cell
    annotation.
  - piece mobility owns source-piece set and mobility predicate.
  - piece state owns visible piece predicate.
  - max capture chain owns selected king/piece and path-length computation.

### chess

- Tasks: `checkmate_move_label`, `colored_piece_kind_count`,
  `king_escape_square_count`, `marked_piece_blocker_count`,
  `marked_piece_destination_count`, `piece_kind_count`,
  `player_capture_piece_count`, `target_square_attacker_count`.
- Current risk: exact copy-split across eight large files.
- Shared scene helpers: chess piece dataclasses, material-plausible placement,
  attack/move primitives, board renderer, option encoding.
- Public task ownership:
  - piece count tasks own target kind/color and counted-piece annotation.
  - marked-piece destination owns selected piece and legal destination set.
  - player capture owns side-wide capture-piece set.
  - target-square attacker owns target square and attacker set.
  - king escape owns king and safe-square computation.
  - blocker/checkmate tasks own line/checkmate-specific construction and keyed
    annotation where roles matter.
- Migration action: keep rule primitives shared; task files must own which
  board constraints are sampled and what answer/annotation contract is used.

### chess_variant

- Tasks: `marked_piece_destination_count`, `target_square_reacher_count`.
- Current risk: exact copy-split.
- Shared scene helpers: chess-like board renderer, variant rule card, nonstandard
  movement primitives.
- Public task ownership:
  - marked-piece task owns selected piece and destination set.
  - target-square task owns selected target and source-piece reacher set.

### circular_chess

- Tasks: `marked_piece_destination_count`, `target_cell_reacher_count`.
- Current risk: exact-size siblings and missing literal task-id declaration in
  the static check.
- Shared scene helpers: circular board geometry, ring/sector coordinate system,
  circular move primitives, renderer.
- Public task ownership: same split as chess variant, but point annotation over
  annular cells.
- Migration action: make task ids literal class attrs, one class per file.

### connect_four

- Tasks: `safe_move_count`, `winning_move_column_label`,
  `winning_move_count`.
- Current risk: exact copy-split.
- Shared scene helpers: board state, gravity/drop simulation, connect-line
  evaluation, column/cell renderer.
- Public task ownership:
  - winning/safe move counts own qualifying drop predicate and landing-cell
    annotation.
  - winning column label owns candidate option construction and selected landing
    cell annotation.

### crossing

- Tasks: `moving_object_count`, `moving_object_direction_count`.
- Current risk: exact copy-split.
- Shared scene helpers: lane layout, object motion direction, route cell
  geometry, renderer.
- Public task ownership:
  - moving-object count owns route-intersection predicate.
  - direction count owns direction predicate over visible moving objects.

### darts

- Tasks: `ring_count`, `threshold_score_count`, `total_score_option_label`.
- Current risk: exact copy-split.
- Shared scene helpers: board geometry, sector/ring scoring, dart renderer,
  score-option renderer.
- Public task ownership:
  - ring/threshold counts own dart predicate and dart-point annotation.
  - total score option owns one-dart scoring answer and selected dart/option
    annotation contract.

### dominoes

- Tasks: `double_count`, `extendable_first_play_count`,
  `higher_sum_than_reference_count`, `matching_end_count`,
  `second_play_candidate_count`, `sum_to_target_count`.
- Current risk: exact copy-split across six files.
- Shared scene helpers: domino tile dataclass, chain ends, pip-sum helpers,
  chain/table layout, renderer.
- Public task ownership:
  - property count tasks own the predicate over loose tiles.
  - matching/extendable/second-play tasks own chain-play simulation and
    counted candidate tile annotation.
- Migration action: keep chain and tile primitives shared; do not combine all
  predicates into one shared task-id dispatcher.

### dots_and_boxes

- Tasks: `capture_move_count`, `owned_box_count`, `three_sided_box_count`.
- Current risk: exact copy-split.
- Shared scene helpers: dot grid, edge/box state, capture opportunity helpers,
  renderer.
- Public task ownership:
  - capture move count owns candidate edge set.
  - owned box count owns owner predicate.
  - three-sided box count owns box-side predicate.

### go

- Tasks: `group_adjacent_enemy_count`, `group_liberty_count`,
  `stone_group_count`.
- Current risk: exact copy-split.
- Shared scene helpers: Go grid, connected components, liberties, adjacency,
  renderer.
- Public task ownership: each task owns the selected group/player predicate and
  annotation witness set.

### hex

- Tasks: `candidate_neighbor_count`, `connection_gap_count`,
  `winning_move_cell_label`.
- Current risk: exact copy-split.
- Shared scene helpers: hex grid geometry, neighbor enumeration, connection
  path/gap helpers, renderer.
- Public task ownership:
  - neighbor count owns selected reference cell and neighbor predicate.
  - connection gap count owns player connection gap computation.
  - winning move label owns candidate winning cell construction.

### irregular_link_board

- Tasks: `capture_move_count`, `marked_piece_destination_count`.
- Current risk: exact-size siblings and missing literal task-id declaration in
  the static check.
- Shared scene helpers: irregular graph board, piece placement, move/capture
  primitives, renderer.
- Public task ownership: destination count vs capture count are separate
  objective files with different predicates over the same legal-neighbor graph.

### lane_runner

- Tasks: `path_coin_count`, `safe_path_label`.
- Current risk: missing literal task-id declaration in static check.
- Shared scene helpers: lane grid/path encoding, hazard/coin renderer, option
  path rendering.
- Public task ownership:
  - path coin count owns one drawn path and collected-coin answer/annotation.
  - safe path label owns candidate path options and selected safe option.

### ludo_board

- Tasks: `capture_roll_option_label`, `move_result_option_label`,
  `winning_roll_value`.
- Current risk: exact-size siblings and missing literal task-id declaration in
  static check; current files appear to include whole scene code.
- Shared scene helpers: Ludo path topology, home lanes, dice sequence helpers,
  board/option renderer.
- Public task ownership:
  - winning roll owns player finish-distance sampling and integer answer.
  - capture roll option owns capture-distance options and selected roll label.
  - move result option owns dice sequence and destination option construction.

### mancala_pit_board

- Tasks: `post_sow_pit_count_value`, `sowing_landing_pit_label`.
- Current risk: exact-size siblings and missing literal task-id declaration in
  static check.
- Shared scene helpers: pit layout, sowing simulation, stone count renderer.
- Public task ownership:
  - landing pit label owns selected pit after sowing.
  - post-sow pit count owns target pit/count answer after sowing.

### marble_chain

- Tasks: `max_pop_direction_label`, `shot_effect_value`,
  `target_pop_direction_label`.
- Current risk: exact copy-split.
- Shared scene helpers: chain geometry, shooter direction options, insertion and
  pop simulation, renderer.
- Public task ownership:
  - direction-label tasks own candidate direction selection by target/max pop.
  - shot effect owns numeric result after a fixed shot.

### match3

- Tasks: `gem_count`, `max_clear_swap_label`, `target_clear_swap_label`.
- Current risk: exact copy-split; file content currently duplicates dataclasses,
  samplers, renderer, and all query constants.
- Shared scene helpers: board generation, swap enumeration, clear/run
  evaluation, gem rendering, option drawing.
- Public task ownership:
  - gem count owns grid/row/column color predicate and counted cell annotation.
  - max clear swap owns candidate swap options and max-clear selection.
  - target clear swap owns target-clear construction and selected swap option.

### minecraft

- Tasks: `reachable_ore_stack_count`, `resource_route_cost`,
  `stack_height_condition_count`, `top_ore_stack_count`.
- Current risk: exact copy-split.
- Shared scene helpers: isometric stack renderer, material palette, route/height
  helpers, stack annotation projection.
- Public task ownership:
  - stack height condition owns height predicate over stacks.
  - top ore stack owns top-material predicate.
  - reachable ore stack owns left-to-right reachability constraint.
  - resource route cost owns path/route cost program.

### minesweeper

- Tasks: `forced_cell_count`, `remaining_mine_count_value`,
  `reveal_outcome_label`, `satisfied_clue_count`.
- Current risk: exact copy-split.
- Shared scene helpers: mine/clue grid generation, clue consistency, reveal
  outcome calculation, renderer.
- Public task ownership:
  - forced cell count owns forced mine/safe predicate.
  - remaining mine count owns residual mine-count computation.
  - reveal outcome label owns selected hidden cell and outcome options.
  - satisfied clue count owns clue-satisfaction predicate.

### minigolf

- Tasks: `first_obstacle_label`, `shot_path_label`.
- Current risk: exact copy-split.
- Shared scene helpers: course geometry, path/collision primitives, obstacle
  renderer.
- Public task ownership:
  - first obstacle label owns first-intersection target.
  - shot path label owns visible cue path option selection and annotation.

### nine_mens_morris

- Tasks: `mill_completion_point_count`, `pieces_in_mill_count`.
- Current risk: exact copy-split.
- Shared scene helpers: board graph, mill lines, piece placement, renderer.
- Public task ownership:
  - pieces in mill owns existing mill-membership count.
  - mill completion point owns empty completion-point set.

### pacman

- Tasks: `next_item_label`, `path_pellet_count`, `pellet_count_before_ghost`,
  `route_score_value`.
- Current risk: exact copy-split.
- Shared scene helpers: maze grid, route tracing, pellets/ghost/items, score
  table renderer.
- Public task ownership:
  - next item label owns route-order target.
  - pellet count variants own route/prefix pellet predicates.
  - route score owns scoring aggregation with visible route.

### pinball_table

- Tasks: `first_hit_object_label`, `path_score_value`.
- Current risk: not an exact-size copy-split in the static inventory, but it
  uses a shared query-id base pattern that must not become a wrapper or
  full-output dispatcher.
- Shared scene helpers: playfield object placement, path geometry, ricochet
  renderer, scoring primitives.
- Public task ownership:
  - first hit label owns first object collision.
  - path score owns full drawn trajectory and sum of hit scores.

### platformer

- Tasks: `collectible_count`, `jump_collectible_score_value`,
  `jump_landing_label`.
- Current risk: exact copy-split.
- Shared scene helpers: side-scroller tiles, jump arc/path construction,
  collectible scoring, renderer.
- Public task ownership:
  - collectible count owns visible predicate.
  - jump landing owns candidate landing selection.
  - jump collectible score owns score aggregation along a visible jump path.

### pool

- Tasks: `blocking_ball_count`, `group_ball_count`.
- Current risk: not an exact-size copy-split in the static inventory, but must
  still pass wrapper and shared-dispatch checks before it can be marked clean.
- Shared scene helpers: table/ball renderer, group definitions, line-of-sight
  obstruction helpers.
- Public task ownership:
  - blocking ball count owns cue/path obstruction set.
  - group ball count owns solids/stripes predicate over visible balls.

### racing_track

- Tasks: `ahead_object_count`, `finish_distance_extremum_label`.
- Current risk: missing literal task-id declaration in static check.
- Shared scene helpers: track/lane geometry, car placement, distance-to-finish
  helpers, renderer.
- Public task ownership:
  - ahead count owns reference car and ahead-car predicate.
  - finish-distance extremum owns nearest/farthest car selection.

### radial_hunt_board

- Tasks: `capture_move_count`, `marked_piece_destination_count`.
- Current risk: exact-size siblings and missing literal task-id declaration.
- Shared scene helpers: radial board graph, piece placement, move/capture
  primitives, renderer.
- Public task ownership: same split as irregular-link board but with radial
  topology.

### reversi

- Tasks: `frontier_disc_count`, `legal_destination_count`,
  `marked_move_flip_count`.
- Current risk: exact copy-split.
- Shared scene helpers: Reversi board, legal move/flipping algorithm, frontier
  predicate, renderer.
- Public task ownership:
  - legal destination count owns player and legal empty-cell set.
  - marked move flip count owns selected move and flipped-disc set.
  - frontier disc count owns frontier predicate over visible discs.

### rhythm

- Tasks: `earliest_hit_lane_label`, `lane_color_hit_count`,
  `lane_hit_count`, `most_hits_lane_label`.
- Current risk: exact copy-split.
- Shared scene helpers: lane/timing grid, hit-note placement, lane/color
  renderer.
- Public task ownership:
  - lane hit count owns selected lane predicate.
  - lane color hit count owns lane+color predicate.
  - most/earliest label tasks own rank/extremum selection.

### rule_override_board

- Tasks: `line_result_count`, `piece_result_count`.
- Current risk: exact copy-split.
- Shared scene helpers: small board renderer, rule text/predicate helpers,
  winner/lower-count override computations.
- Public task ownership:
  - line result count owns noncanonical line-rule predicate.
  - piece result count owns noncanonical piece-count rule predicate.

### sixteen_soldiers

- Tasks: `marked_piece_capture_count`, `marked_piece_destination_count`.
- Current risk: exact-size siblings and missing literal task-id declaration.
- Shared scene helpers: board graph, soldier piece placement, movement/capture
  rules, renderer.
- Public task ownership: destination vs capture predicate split.

### sliding_block

- Tasks: `movable_block_count`, `sliding_block_blocker_count`,
  `sliding_block_move_result_label`.
- Current risk: exact-size siblings and missing literal task-id declaration.
- Shared scene helpers: block grid, motion constraints, result-option rendering.
- Public task ownership:
  - movable block count owns block-mobility predicate.
  - blocker count owns blockers along movement direction.
  - move result label owns candidate result boards/options.

### snake

- Tasks: `path_outcome_option_label`, `safe_direction_count`,
  `shortest_food_path_length`.
- Current risk: exact copy-split.
- Shared scene helpers: snake grid, collision/path search, food placement,
  option rendering.
- Public task ownership:
  - safe direction count owns one-step safe direction predicate.
  - shortest food path owns path length program.
  - path outcome option owns candidate path outcome selection.

### snakes_ladders

- Tasks: `best_roll_value`, `move_outcome_value`, `special_square_count`.
- Current risk: exact copy-split.
- Shared scene helpers: board path, snakes/ladders mapping, dice roll outcome,
  renderer.
- Public task ownership:
  - move outcome value owns one roll and resulting square.
  - best roll owns choice over dice outcomes.
  - special square count owns snake/ladder/special-square predicate.

### sokoban

- Tasks: `box_target_manhattan_rank_label`, `nearest_counterpart_label`,
  `path_validity_sequence_label`, `shortest_path_sequence_label`.
- Current risk: exact-size siblings and missing literal task-id declaration in
  static check.
- Shared scene helpers: grid, walls/boxes/targets/player, path encoding,
  shortest-path and validity helpers, renderer.
- Public task ownership:
  - nearest/rank label tasks own object-pair distance selection.
  - path validity owns candidate sequence checking.
  - shortest path owns candidate sequence optimality/selection.

### solitaire

- Tasks: `foundation_ready_count`, `move_legality_label`,
  `same_suit_run_length_value`, `tableau_sequence_count`.
- Current risk: exact copy-split.
- Shared scene helpers: tableau/foundation state, card move rules, card/tableau
  renderer.
- Public task ownership:
  - foundation readiness count owns top-card-to-foundation predicate.
  - move legality label owns candidate move options.
  - same-suit run length owns marked column/run computation.
  - tableau sequence count owns sequence predicate over visible columns.

### space_shooter

- Tasks: `clear_shot_count`, `clear_shot_score_value`,
  `highest_threat_label`, `projectile_intercept_count`, `safe_lane_count`.
- Current risk: exact copy-split.
- Shared scene helpers: lane/object geometry, projectile line checks, threat
  score helpers, renderer.
- Public task ownership:
  - clear shot count owns unobstructed enemy set.
  - clear shot score owns score aggregation over clear targets.
  - projectile intercept count owns path/intersection set.
  - highest threat label owns rank/extremum target.
  - safe lane count owns lane safety predicate.

### tetris

- Tasks: `drop_collision_time_value`, `drop_result_label`,
  `edge_occupied_row_cell_count`, `line_clear_count`,
  `row_occupancy_status_count`.
- Current risk: exact copy-split; files include a legacy base task id in static
  declarations.
- Shared scene helpers: well/board state, tetromino definitions, drop
  simulation, line-clear logic, option-board renderer.
- Public task ownership:
  - line clear count owns placement/rotation allowance and cleared rows.
  - drop result label owns fixed falling piece and candidate result boards.
  - row occupancy status count owns top/bottom occupied/empty row predicate.
  - drop collision time owns fixed falling piece collision steps.
  - edge occupied row cell count owns left/right row occupancy predicate.
- Migration action: delete any legacy `games_tetris_base` public class or keep
  it purely private and unregistered without public task id.

### tic_tac_toe_3d

- Tasks: `layer_piece_count`, `winning_move_cell_label`.
- Current risk: exact copy-split.
- Shared scene helpers: 3D board/layer layout, 3-in-a-row line enumeration,
  renderer.
- Public task ownership:
  - layer piece count owns layer/player predicate.
  - winning move cell label owns candidate winning empty-cell selection.

### tower_defense

- Tasks: `covered_path_segment_count`, `tower_coverage_count`.
- Current risk: missing literal task-id declaration in static check.
- Shared scene helpers: path segments, tower ranges, coverage geometry,
  renderer.
- Public task ownership:
  - covered path segment count owns selected tower/range and segment set.
  - tower coverage count owns selected path segment and covering tower set.

### tower_draughts_board

- Tasks: `controlled_stack_count`, `marked_stack_capture_count`,
  `marked_stack_destination_count`.
- Current risk: exact-size siblings and missing literal task-id declaration.
- Shared scene helpers: stack board, stack control/capture/destination rules,
  renderer.
- Public task ownership:
  - controlled stack count owns player/top-piece control predicate.
  - marked stack destination owns movement destination set.
  - marked stack capture owns capture destination/target set.

### ultimate_tictactoe

- Tasks: `line_completion_move_label`, `macro_threat_board_count`,
  `small_board_status_count`.
- Current risk: exact copy-split.
- Shared scene helpers: small-board status evaluator, macro-board lines,
  move-option renderer.
- Public task ownership:
  - small board status count owns won/drawn/open status predicate.
  - macro threat board count owns macro line-threat predicate.
  - line completion move label owns candidate move that completes a line.

## Final Shared-Code Checkpoint

Run this only after every scene in the scene loop has clean objective-owned task
files.

1. Compare scene-local `shared/` helpers for true repeated primitives.
2. Promote only narrow scene-neutral helpers to `trace/tasks/games/shared/`.
3. Do not promote any helper that knows a single game scene, accepts public
   task ids/objective contracts, or returns complete `TaskOutput` objects.
4. Update imports after promotion.
5. Rerun scene-package enforcement tests to make sure consolidation did not
   recreate wrappers or dispatchers.

Examples of acceptable promotion: generic layout jitter, generic option-grid
layout, generic text/marker legibility wrappers, generic named-axis sampling.

Examples that must stay scene-local: chess attack rules, 2048 merge logic,
Tetris drop simulation, Battleship fleet placement, Ludo path topology, card
hand evaluators unless they are deliberately reused by multiple card-like
scenes.

## Validation Plan

Per-scene cheap checks should run before leaving each scene:

```bash
SCENE=2048
python - <<'PY'
from pathlib import Path
import ast
import os

domain = "games"
scene = os.environ["SCENE"]
scene_dir = Path("trace/tasks") / domain / scene
files = sorted(path for path in scene_dir.glob("*.py") if path.name != "__init__.py")
sizes = {}
errors = []
for path in files:
    sizes.setdefault(len(path.read_bytes()), []).append(path.name)
for names in sizes.values():
    if len(names) > 1:
        errors.append(f"exact-size sibling task files in {scene}: {names}")
for path in files:
    tree = ast.parse(path.read_text())
    ids = []
    registered = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            is_registered = any(
                (isinstance(dec, ast.Name) and dec.id == "register_task")
                or (
                    isinstance(dec, ast.Call)
                    and isinstance(dec.func, ast.Name)
                    and dec.func.id == "register_task"
                )
                for dec in node.decorator_list
            )
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    for target in stmt.targets:
                        if (
                            isinstance(target, ast.Name)
                            and target.id == "task_id"
                            and isinstance(stmt.value, ast.Constant)
                        ):
                            task_id = str(stmt.value.value)
                            ids.append(task_id)
                            if is_registered:
                                registered.append(task_id)
    expected = f"task_{domain}__{scene}__{path.stem}"
    if ids != [expected]:
        errors.append(f"{path.name}: expected only {expected}, got {ids}")
    if registered != [expected]:
        errors.append(f"{path.name}: expected one registered class for {expected}, got {registered}")
if errors:
    raise SystemExit("\n".join(errors))
print(f"{scene}: source ownership check passed for {len(files)} task files")
PY
if rg -n "task_group|evidence|complexity" \
  "trace/tasks/games/${SCENE}" \
  "configs/domains/games/${SCENE}.yaml" \
  docs/tasks --glob "task_games__${SCENE}__*.md"; then
  echo "Forbidden games migration terms found for ${SCENE}" >&2
  exit 1
fi
```

Run full domain validation after the final shared-code checkpoint:

```bash
PYTHONPATH=. python - <<'PY'
import trace.tasks
from trace.tasks.registry import list_task_ids, list_default_task_ids

ids = sorted(tid for tid in list_task_ids() if tid.startswith("task_games__"))
default_ids = sorted(tid for tid in list_default_task_ids() if tid.startswith("task_games__"))
print("registered_games", len(ids))
print("default_games", len(default_ids))
for tid in default_ids:
    print(tid)
PY
```

Static enforcement checks to add or run:

```bash
PYTHONPATH=. pytest -q tests/test_scene_package_migration_contracts.py
if rg -n "task_group|evidence|complexity" trace/tasks/games configs/domains/games docs/domains/GAMES_TASK_SETUP.md docs/tasks --glob 'task_games__*.md'; then
  echo "Forbidden games migration terms found" >&2
  exit 1
fi
```

The scene-package enforcement tests must cover these games failure modes before
the domain is marked migrated:

- normalized-AST or token-level near-duplicate sibling task files, not only
  exact byte-size duplicates;
- public task files importing `FixedQueryVariantTaskMixin`,
  `QuerySubsetTaskMixin`, `_SourceTask`, or a multi-objective base generator;
- public task files defining sibling public task ids/classes;
- scene `shared/` modules importing `TaskOutput`;
- scene `shared/` modules containing public task ids, branching by public
  objective, or constructing final prompt/answer/annotation triples for several
  objectives;
- domain `shared/` helpers that mention one scene id or return full task
  outputs.

Until those checks exist as tests, run ad hoc source scans during migration:

```bash
rg -n "FixedQueryVariantTaskMixin|QuerySubsetTaskMixin|_SourceTask|_BaseTask" trace/tasks/games
rg -n "TaskOutput|task_games__|objective_contract|task_id" trace/tasks/games/*/shared trace/tasks/games/shared
```

After registry imports are fixed, run active-task smoke generation:

```bash
GAMES_TASKS="$(
  PYTHONPATH=. python - <<'PY'
import trace.tasks  # noqa: F401
from trace.tasks.registry import list_default_task_ids
print(",".join(sorted(tid for tid in list_default_task_ids() if tid.startswith("task_games__"))))
PY
)"
PYTHONPATH=. python scripts/audit_active_tasks.py \
  --tasks "$GAMES_TASKS" \
  --smoke-seeds 2 \
  --max-attempts 80 \
  --fail-on-blocked \
  --output-json docs/workflows/SCENE_PACKAGE_MIGRATION/games_active_task_audit.json \
  --output-md docs/workflows/SCENE_PACKAGE_MIGRATION/games_active_task_audit.md
```

Run inventory, docs, and taxonomy sync checks after smoke passes:

```bash
PYTHONPATH=. python scripts/generate_active_task_inventory.py --check
PYTHONPATH=. python scripts/check_active_inventory_integrity.py
PYTHONPATH=. python - <<'PY'
import trace.tasks  # noqa: F401
from trace.core.taxonomy import missing_taxonomy_task_ids
from trace.tasks.registry import list_default_task_ids
missing = missing_taxonomy_task_ids(list_default_task_ids())
if missing:
    raise SystemExit("missing taxonomy task ids:\n" + "\n".join(missing))
print("taxonomy coverage ok")
PY
test ! -e trace/tasks/games/twenty_forty_eight
```

Task-review artifacts are required for this migration:

```bash
PYTHONPATH=. python scripts/run_task_review.py --tasks "$GAMES_TASKS" --mode full --out-root review/task-reviews
curl -X POST http://127.0.0.1:7860/api/reload || true
find review/task-reviews/games -maxdepth 3 -type d | sort
```

Use that inventory to confirm changed active task artifacts exist and to delete
stale folders for retired or renamed task ids. If the review app is not running,
start it or reload the index before handing off browser inspection.

## Completion Criteria

The games domain is complete only when:

1. every scene section above has been migrated and checked;
2. `registered_games` and `default_games` match the intended active inventory;
3. every games scene is listed in the explicit objective-complete registry;
4. no games scene remains in objective-ownership pending;
5. enforcement tests reject wrapper/copy-split regressions;
6. task-complexity config/helper/metadata/doc surfaces are removed, with no
   replacement difficulty/complexity proxy;
7. current task-review artifacts exist for changed active games tasks, and
   stale folders for retired or renamed task ids are purged;
8. docs/tasks/configs/taxonomy/imports are synchronized;
9. each migrated scene has a final post-migration review note covering stale
   ids, wrapper-only task files, duplicated objective logic in shared files,
   prompt/annotation terminology, retired artifact folders, and domain-shared
   promotion candidates;
10. no active games-owned file uses `task_group`, prompt-facing `evidence`, or
   task `complexity`.

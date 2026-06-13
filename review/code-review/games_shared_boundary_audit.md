# Games Shared-Boundary Audit

Date: 2026-06-12

Purpose: define what belongs in `trace/tasks/games/shared/` before more games
scene-package migration work continues. This is a source-boundary report, not a
scene acceptance record, and no scene should be marked migrated from this file
alone.

## Boundary Rule

`trace/tasks/games/shared/` is for scene-neutral games-domain primitives. It may
contain helpers for layout jitter, option-panel layout, readable text wrappers,
marker wrappers, domain panel-style adapters, and approved multi-scene artifact
families.

`trace/tasks/games/<scene_id>/shared/` is for one scene's reusable primitives:
state, rules, sampling, rendering, annotation projection, prompt-asset assembly,
and output payload helpers. Scene shared code may know the scene grammar and
game rules, but it must not route behavior by public task id, query id,
objective contract, registered task class, or supported-query list.

Public task files own the objective contract: query selection and validation,
target/candidate construction, answer binding, annotation binding, dynamic
prompt slots, task trace fields, retry behavior, and final `TaskOutput`
construction.

## Domain Shared Decisions

| Module | Decision | Action |
|---|---|---|
| `layout.py` | Keep domain-shared. | Scene-neutral layout jitter, unit-size scaling, and bbox offset helpers are valid domain primitives. |
| `marking.py` | Keep domain-shared. | Keep as a thin semantic marker wrapper. It must stay independent of scene/task identity. |
| `option_layout.py` | Keep domain-shared. | Visual MCQ option-grid sizing and placement are reused across games. |
| `scene_style.py` | Keep domain-shared. | Keep as games adapter over repo-global panel/canvas style. |
| `text.py` | Keep domain-shared. | Keep readable-text wrappers and traced text drawing. Do not add scene prompt wording here. |
| `visual_defaults.py` | Split or narrow. | Domain fallback builders are fine. Scene-id based loaders should be reviewed because identity-aware loading is not a clean domain primitive. Prefer scene `defaults.py` ownership after migration. |
| `sampling.py` | Split. | Keep only neutral numeric/default helpers. Retire `resolve_games_query_id`, `query_id_weights`, and balanced query sampling from games domain shared. Query selection belongs in public task files through repo-global helper code. |
| `piece_board_rules.py` | Rename/narrow. | This is chess-family logic, not generic piece-board logic. Rename after chess-family migration, for example `chess_board_rules.py`, or move to a clearer chess-family domain helper. |
| `piece_board_renderer.py` | Rename/narrow. | This is chess-family board/piece rendering. Rename with the rules module or demote if only one chess-family scene remains dependent. |
| `style.py` | Keep only as facade after audit. | Do not let it export one-scene themes as if they were domain primitives. |
| `style_common.py` | Keep or fold. | Tiny common probability helper. It can stay if style-family modules continue using it, otherwise fold into the caller. |
| `style_card_table.py` | Split by reusable family. | Card face/table style can stay if shared by cards and solitaire. Domino style should move scene-local unless a second scene uses it. |
| `style_node_boards.py` | Split by reusable family. | Shared node-board palette primitives can stay. Scene-specific Morris, Go, and Hex themes should move local unless the exact helpers are reused. |
| `style_number_grids.py` | Split by reusable family. | Battleship/Bingo/Minesweeper themes should not all live together by default. Keep only genuinely shared number-grid primitives. |
| `style_square_boards.py` | Split by reusable family. | Keep shared square-board palette primitives; demote scene-specific chess, checkers, reversi, connect-four, and dots-and-boxes themes as each scene migrates. |
| `style_table_surfaces.py` | Split. | Pool-only or darts-only surface themes should be scene-local. Keep only true table/playfield primitives reused by multiple migrated scenes. |

## Scene Shared Target

Games scenes should converge on this shape when the role is needed:

```text
trace/tasks/games/<scene_id>/
  <objective_contract>.py
  _lifecycle.py          # optional scene-level plumbing, no objective logic
  shared/
    state.py             # passive state/dataclasses/constants
    defaults.py          # scene-level fallback defaults only
    rules.py             # legal moves, scoring, transitions, constraints
    sampling.py          # scene sample construction primitives
    rendering.py         # drawing/projection/render parameter helpers
    annotations.py       # annotation projection helpers
    prompts.py           # prompt asset keys/slot assembly helpers
    output.py            # generic payload helpers, no final public output
    styles.py            # optional scene-local visual theme helpers
    layout.py            # optional scene-local geometry/layout helpers
    labels.py            # optional label placement only
    option_rendering.py  # optional visual option panels/boards
```

Avoid broad names like `scene.py`, `common.py`, and `assembly.py` in migrated
scenes. If a broad file currently exists, split it by role during that scene's
migration. Rename `mechanics.py` to `rules.py` during migration so games scenes
use one term for game rules and state transitions.

## Promotion Rules

1. Keep helper code scene-local first.
2. Record a promotion candidate only after the same helper pattern appears in
   at least two migrated scenes or is clearly an approved game-family primitive.
3. Promote candidates in a separate cleanup pass, not while migrating a scene.
4. Promoted domain helpers must be identity-free: no public task ids, query ids,
   objective names, scene ids, registered class names, or final `TaskOutput`.
5. Never import from sibling scenes. Cross-scene reuse goes through
   `trace/tasks/games/shared/` or repo-global `trace/tasks/shared/`.

## Current Scene Inventory

| Scene | Current shared shape | Boundary action before or during migration |
|---|---|---|
| `2048` | Target-shaped shared files plus optional `_lifecycle.py`. | Use as reference. Recheck any dependency on `visual_defaults.py` policy before final acceptance. |
| `backgammon` | Target-shaped shared files. | Use as reference. Keep destination-count simplification separate from shared-boundary work. |
| `battleship` | Target-shaped shared files. | Use as reference after current task redesign settles. Watch `style_number_grids.py` dependency. |
| `bingo` | Target-shaped shared files. | Still needs task-level annotation/task redesign verification; do not treat as complete until review app accepts it. |
| `bowling` | Uses `mechanics.py`. | Rename to `rules.py`; keep trajectory/scoring helpers scene-local unless reused by pinball/minigolf/pool after they migrate. |
| `brick_breaker` | Uses `mechanics.py`. | Rename to `rules.py`; keep brick physics/rendering scene-local. |
| `bubble_shooter` | Mostly target-shaped, no `annotations.py`. | Add annotation helpers if repeated in tasks; keep bubble/path sampling scene-local. |
| `cards` | Target-like but has `card_face_rendering.py` and very large `sampling.py`. | Keep card face renderer local for now; promote only after solitaire migration proves reuse. |
| `checkers` | Uses `mechanics.py`. | Rename to `rules.py`; keep move/capture rules scene-local. |
| `chess` | Uses `mechanics.py` and chess-family domain helpers. | Rename local `mechanics.py` to `rules.py`; later rename domain `piece_board_*` to chess-family names. |
| `chess_variant` | Uses `mechanics.py` and chess-family helpers. | Same chess-family cleanup; no new domain helper names during scene migration. |
| `circular_chess` | Uses scene-local `rules.py` and chess-family helpers. | Same chess-family cleanup. Circular board mapping stays scene-local. |
| `connect_four` | Has `common.py`. | Split `common.py` into `state.py`, `rules.py`, and/or `layout.py`; keep board renderer scene-local. |
| `crossing` | Uses `mechanics.py`. | Rename to `rules.py`; keep traffic route construction scene-local. |
| `darts` | Has `assembly.py`. | Split into annotation/output/payload helpers by role. Darts scoring geometry stays scene-local. |
| `dominoes` | Has `assembly.py`. | Split by role. Domino tile drawing can be scene-local unless shared by another domino-like scene. |
| `dots_and_boxes` | Has `assembly.py` and `mechanics.py`. | Split assembly and rename mechanics to rules. Board-line rules stay scene-local. |
| `go` | Has `assembly.py` and `mechanics.py`. | Split assembly and rename mechanics to rules. Shared node-board style use should be audited. |
| `hex` | Has `assembly.py` and `mechanics.py`. | Split assembly and rename mechanics to rules. Hex coordinate layout stays scene-local unless reused. |
| `irregular_link_board` | One large `scene.py`. | Split into state/rules/sampling/rendering/annotations/prompts/output. Consider later node-link board primitive promotion. |
| `lane_runner` | Has `common.py` and `rendering.py`. | Split common into state/rules/sampling/output as needed. Path/coin rules remain scene-local. |
| `ludo_board` | One large `scene.py`. | Full split required. Ludo path indexing and die-sequence rules stay scene-local. |
| `mancala_pit_board` | One large `scene.py`. | Full split required. Pit/stone rendering may later become table/row primitive only if reused. |
| `marble_chain` | One large `scene.py`. | Full split required. Spiral/track rendering is scene-local unless pinball/path primitives converge later. |
| `match3` | One large `scene.py`. | Full split required. Shared square-grid visual primitives are candidates, but swap/run logic stays scene-local. |
| `minecraft` | `common.py`, `rendering.py`, and large `scene.py`. | Split scene/common. Cube stack rendering might later promote to domain or repo shared only if other games use it. |
| `minesweeper` | `common.py`, `rendering.py`, and large `scene.py`. | Split scene/common. Minefield rules stay scene-local; number-grid styles need demotion/promotion decision. |
| `minigolf` | `common.py`, `rendering.py`, and large `scene.py`. | Split scene/common. Trajectory helpers may become promotion candidates with pool/pinball only after all migrate. |
| `nine_mens_morris` | `common.py`, `rendering.py`, and `scene.py`. | Split by role. Node-board style helper use should be audited. |
| `pacman` | `common.py`, `rendering.py`, and large `scene.py`. | Split by role. Maze/grid movement stays scene-local. |
| `pinball_table` | `common.py`, `rendering.py`, and large `scene.py`. | Split by role. Trajectory/bumper scoring stays scene-local unless reused after pool/minigolf migration. |
| `platformer` | `common.py`, `rendering.py`, and large `scene.py`. | Split by role. Platform/path state stays scene-local. |
| `pool` | `common.py`, `rendering.py`, and `scene.py`. | Split by role. Table-surface style should move local unless reused. |
| `racing_track` | `common.py`, `output.py`, `rendering.py`. | Split common into state/rules/sampling; keep racing geometry scene-local. |
| `radial_hunt_board` | One large `scene.py`. | Full split required. Radial graph geometry stays scene-local. |
| `reversi` | `common.py`, `rendering.py`, and `scene.py`. | Split by role; demote scene-specific square-board style if no other exact reuse. |
| `rhythm` | `common.py`, `rendering.py`. | Split common into state/sampling/rules/output as needed. Timing-lane rendering stays scene-local. |
| `rule_override_board` | No shared folder. | Build target structure during migration; avoid routing by rule name in shared. |
| `sixteen_soldiers` | `common.py`, `rendering.py`. | Split common. Board graph rules stay scene-local. |
| `sliding_block` | No shared folder. | Build target structure during migration. Consider square-grid option rendering only after second consumer. |
| `snake` | `common.py`, `rendering.py`. | Split common into state/rules/sampling/output. Snake movement stays scene-local. |
| `snakes_ladders` | `common.py`, `rendering.py`. | Split common. Track numbering/path rules stay scene-local. |
| `sokoban` | Large `rendering.py` only. | Add state/rules/sampling/output/prompt helpers as needed; renderer may remain one file if scoped and commented. |
| `solitaire` | No shared folder. | Build target structure; inspect possible card face renderer reuse with `cards`. |
| `space_shooter` | `common.py`, `rendering.py`. | Split common. Projectile/path rules stay scene-local. |
| `tetris` | No shared folder. | Build target structure. Board and tetromino rules stay scene-local. |
| `tic_tac_toe_3d` | No shared folder. | Build target structure. Layer rendering and line rules stay scene-local. |
| `tower_defense` | `common.py`, `rendering.py`. | Split common. Range/path rules stay scene-local. |
| `tower_draughts_board` | No shared folder. | Build target structure. Stack rendering could later inform shared component helpers but starts local. |
| `ultimate_tictactoe` | No shared folder. | Build target structure. Nested-board layout stays scene-local unless reused later. |

## Promotion Candidate Backlog

Do not promote these during the next scene migration. Record actual duplicate
use first, then handle in a separate cleanup pass.

| Candidate | Potential scenes | Notes |
|---|---|---|
| Chess-family board/rules/rendering | `chess`, `chess_variant`, `circular_chess` | Rename current `piece_board_*` if kept. |
| Card face and card table rendering | `cards`, `solitaire` | Promote only after solitaire proves it can consume the same renderer cleanly. |
| Square/cell board layout and option panels | `match3`, `minesweeper`, `tetris`, `sokoban`, `sliding_block`, `connect_four`, `lane_runner` | Keep task/game rules local; only visual/layout primitives are promotion candidates. |
| Node-link board rendering | `go`, `hex`, `nine_mens_morris`, `irregular_link_board`, `sixteen_soldiers`, `radial_hunt_board` | Shared line/node style may be useful, but graph topology and capture rules stay local. |
| Path/track indexing helpers | `ludo_board`, `snakes_ladders`, `racing_track` | Promote only if indexing helpers are genuinely identical. |
| Trajectory/intersection primitives | `bowling`, `brick_breaker`, `minigolf`, `pool`, `pinball_table` | Geometry helpers can be shared later; scoring/object rules stay local. |
| Arcade grid movement helpers | `pacman`, `snake`, `sokoban`, `platformer`, `lane_runner`, `crossing` | Avoid a generic game engine. Promote only tiny coordinate/path primitives. |

## Immediate Pre-Migration Fixes

1. Remove query routing from `trace/tasks/games/shared/sampling.py` as migrated
   scenes stop using it. New scenes must use repo-global task-query selection
   from the public task file only.
2. Standardize scene-local `mechanics.py` to `rules.py` during migration.
3. Split `scene.py`, `common.py`, and `assembly.py` during each scene migration.
4. Treat style family modules as provisional. Demote one-scene themes to the
   owning scene's `shared/styles.py` unless a second migrated scene uses them.
5. Keep promotion decisions separate from scene migration. The scene migration
   deliverable is a clean scene package, not a broad domain-shared refactor.

## Checks Used For This Audit

- Listed all direct files under `trace/tasks/games/shared/`.
- Listed every games scene's current task count and scene `shared/` modules.
- Scanned `trace/tasks/games/shared/` for task/query routing terms.

No task reviews, solve-rate jobs, or scene migrations were run for this audit.

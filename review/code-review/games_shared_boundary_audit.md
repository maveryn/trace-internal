# Games Shared-Boundary Audit

Date: 2026-06-12

Purpose: define what belongs in `trace/tasks/games/shared/` before more games
scene-package migration work continues. This is a source-boundary audit, not a
scene acceptance record.

## Boundary Rule

`trace/tasks/games/shared/` is for scene-neutral games-domain primitives. It may
contain helpers for rendering style, layout jitter, text/marker legibility,
option layout, visual defaults, and approved multi-scene artifact families.

`trace/tasks/games/<scene_id>/shared/` is for one scene's reusable primitives:
state, rules, sampling, rendering, annotation projection, prompt-asset assembly,
and output payload helpers. It must not route by public task/query identity or
build final public `TaskOutput`.

Public task files own objective/query selection, target construction, answer
binding, annotation binding, prompt slots, task trace fields, retry behavior,
and final `TaskOutput` construction.

## Current Domain Shared Classification

| Module | Current role | Classification | Required action |
|---|---|---|---|
| `layout.py` | Layout jitter, unit-size scaling, bbox offsets | Keep | Keep as scene-neutral placement helper. |
| `scene_style.py` | Games adapter over global panel-scene style | Keep | Keep thin over `trace/tasks/shared/visual_style`. |
| `text.py` | Games readable-text wrapper | Keep | Keep as domain wrapper over global text-legibility logic. |
| `marking.py` | Games semantic-marker wrapper | Keep | Keep as domain wrapper over global marker-legibility logic. |
| `option_layout.py` | Visual option-grid sizing/positioning | Keep | Keep for visual MCQ panels across games. |
| `visual_defaults.py` | Domain visual default/noise loader | Keep | Keep. |
| `style.py` | Public style facade over style family files | Keep, audit exports | Keep facade; remove one-scene-only theme exports during scene migration. |
| `style_common.py` | Common style probability helpers | Keep | Keep if used by style family modules. |
| `style_card_table.py` | Card/domino/table style family | Keep family shared | Keep only for card/table/domino scenes that actually share it. |
| `style_node_boards.py` | Node/hex board style family | Keep family shared | Keep only for Go/Hex/Morris-style scenes that actually share it. |
| `style_number_grids.py` | Number-grid style family | Split as needed | Keep multi-scene styles; move Bingo-only styling to `bingo/shared/styles.py` if it remains single-scene. |
| `style_square_boards.py` | Square-board style family | Keep family shared | Keep if reused by chess/checkers/battleship/board scenes; move one-scene themes local during migration. |
| `style_table_surfaces.py` | Table/playfield surface style family | Keep family shared | Keep if reused by multiple table/playfield scenes. |
| `sampling.py` | Integer/range helpers plus legacy query/axis sampling | Split | Keep simple parameter/range helpers; replace `resolve_games_query_id` with task-owned/global query selection. |
| `piece_board_rules.py` | Chess-piece state, square names, movement helpers | Rename/narrow | Treat as chess-family shared, not generic piece-board. Rename/split after chess-family scenes are reworked. |
| `piece_board_renderer.py` | Chess-board/piece renderer helpers | Rename/narrow | Treat as chess-family shared glyph/board helpers. Non-chess board geometry stays scene-local. |

## Scene-Local Shared Pattern

Migrated examples (`2048`, `backgammon`, `battleship`, `bingo`) use this target
shape:

```text
trace/tasks/games/<scene_id>/
  <objective_contract>.py
  _lifecycle.py          # optional neutral scene plumbing
  shared/
    state.py
    sampling.py
    rendering.py
    prompts.py
    output.py
    defaults.py
    rules.py
    annotations.py
```

Scene-local files may call domain helpers, but they should not become generic
multi-scene utility dumps. If the same scene-local helper pattern appears in two
or more migrated scenes, record it as a promotion candidate before moving it.

## Promotion Rules

1. Keep new helper code scene-local first.
2. Mark a helper as a promotion candidate only after it appears in at least two
   scenes or is clearly an approved game-family primitive.
3. Promote in a separate cleanup pass, not in the middle of objective migration.
4. Promoted domain helpers must be identity-free: no public task ids, query ids,
   objective names, scene ids, registered class names, or final `TaskOutput`.
5. Do not import from sibling scenes. Cross-scene reuse goes through
   `trace/tasks/games/shared/` or repo-global `trace/tasks/shared/`.

## Current Risks

- `sampling.py` mixes safe parameter helpers with legacy query-id selection. New
  migrated scenes should use `trace.tasks.shared.fixed_query.select_task_query_id`
  in public task files instead.
- Chess-family shared code is named too broadly. It is reusable, but only for
  chess-like scenes. The naming should reflect that family boundary.
- Style family modules may contain single-scene themes. Those should be demoted
  during the owning scene migration if no second scene uses them.

## Enforcement Added Now

The scene-package migration tests now prevent scalar difficulty helper files and
domain-local `fixed_query_task.py` adapters from reappearing anywhere under
`trace/tasks/`. Review-candidate games scenes are also blocked from importing
`resolve_games_query_id` from `trace.tasks.games.shared.sampling`.

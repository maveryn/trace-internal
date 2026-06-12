# Games Shared Boundary

Use this with `SCENE_MIGRATION_GUIDE.md` when migrating a games scene.

## Domain Shared

`trace/tasks/games/shared/` is for scene-neutral games-domain primitives:

- layout jitter and unit-size scaling
- shared panel/style adapters
- readable text wrappers
- semantic marker wrappers
- visual option-grid layout
- visual defaults
- approved artifact-family helpers reused by multiple scenes

Domain shared code must not know public task ids, query ids, objective
contracts, registered task classes, or scene-specific generation programs. It
must not construct final public `TaskOutput`.

## Scene Shared

`trace/tasks/games/<scene_id>/shared/` owns one scene's reusable primitives:

- passive state/dataclasses
- scene rules/mechanics
- scene sampling primitives
- rendering/layout/projection
- annotation projection helpers
- prompt-asset assembly helpers
- output payload helpers that do not own final public output

Scene shared code may know the scene's visual grammar and game rules. It must
not route behavior by public task/query identity.

## Public Task Files

Public task files own the objective contract:

- supported local query ids
- query selection and validation
- target/candidate construction
- answer binding
- annotation binding
- dynamic prompt slots
- task trace fields
- retry/final `TaskOutput`

## Promotion Workflow

Start with helper code in the owning scene. Record a promotion candidate when
the same helper pattern appears in at least two migrated scenes, or when the
helper is an approved artifact-family primitive such as chess-family piece
glyphs. Promote candidates in a separate cleanup pass after the scene migration
is review-ready.

Never import from a sibling scene. Cross-scene reuse goes through
`trace/tasks/games/shared/` or repo-global `trace/tasks/shared/`.

## Retired Helpers

Scalar difficulty helper files and domain-local `fixed_query_task.py` adapters
are removed repo-wide. Do not recreate them during scene migration. If a public
task has internal query branches, use the repo-global query-selection helper in
the public task file and pass only semantic arguments into scene/shared or
domain/shared helpers.

Migrated games scenes must also not import `resolve_games_query_id` from
`trace.tasks.games.shared.sampling`; query selection belongs in the public task
file.

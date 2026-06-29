# Puzzles Shared Boundary

Use this with `SCENE_MIGRATION_GUIDE.md` when migrating a puzzles scene.

## Domain Shared

`trace/tasks/puzzles/shared/` is for scene-neutral puzzles-domain primitives
that are reused across multiple migrated puzzle scenes:

- repeated-cell board layout, unit-size jitter, and canvas placement utilities
- shared puzzle panel/style adapters and visual defaults
- low-level symbol, color, marker, and option-panel rendering helpers
- generic bbox/point/segment projection helpers
- solver-independent grid, coordinate, and neighborhood utilities
- prompt artifact and output-slot assembly that only receives scene/task-owned
  prompt keys and dynamic slots

Domain shared code must not know public task ids, query ids, objective
contracts, registered task classes, or one scene's puzzle-generation program.
It must not construct final public `TaskOutput`.

Existing broad modules such as `*_scene.py`, `*_common.py`, and legacy helper
families under `trace/tasks/puzzles/shared/` are not automatically approved
domain-shared surfaces. During migration, keep or promote only the pieces that
are genuinely scene-neutral and reused; move scene grammar into the owning
scene's `shared/` package.

## Scene Shared

`trace/tasks/puzzles/<scene_id>/shared/` owns one puzzle grammar's reusable
primitives:

- passive state/dataclasses/enums
- scene rules, constraints, and validation
- scene solvers or local reasoning primitives
- neutral sampling primitives
- rendering, layout, and projection
- annotation projection helpers
- prompt-asset assembly helpers
- output payload helpers that do not own final public output
- scene-local transforms, topology/path helpers, and metrics when needed

Recommended scene-shared role files are direct files such as `state.py`,
`sampling.py`, `rendering.py`, `annotations.py`, `prompts.py`, `output.py`,
`defaults.py`, `styles.py`, `layout.py`, `rules.py`, `constraints.py`,
`solver.py`, `transforms.py`, `topology.py`, `metrics.py`, `symbols.py`, and
`option_rendering.py`. A scene only uses the files it needs.

Scene shared may know the scene's visual grammar and puzzle rules. It must not
route behavior by public task/query identity.

## Public Task Files

Public task files own the objective contract:

- literal public `TASK_ID`
- supported local query ids
- query selection and validation
- objective-specific sampling constraints
- target/candidate construction when objective-specific
- answer binding
- annotation binding
- dynamic prompt slots
- task-specific trace fields
- retry/final `TaskOutput`

The public task file may call scene-shared and domain-shared primitives, but it
must not delegate objective behavior to a shared runtime that chooses the
answer, annotation, query branch, or final output.

## Promotion Workflow

Start with helper code in the owning scene. Record a promotion candidate when
the same helper pattern appears in at least two migrated scenes, or when a
family boundary has been explicitly approved for puzzle artifacts such as
cell-board rendering, option panels, or cube/net projection.

Promote candidates in a separate cleanup pass after the scene migration is
review-ready. Do not use a scene migration as a broad domain-shared cleanup.

Never import from a sibling scene. Cross-scene reuse goes through
`trace/tasks/puzzles/shared/` or repo-global `trace/tasks/shared/`.

## Retired Legacy Layout

Do not reintroduce legacy routing folders such as `logic/`, `spatial/`,
`topology/`, `word/`, or broad single-file task bundles. Puzzle source should
stay organized around taxonomy-v0 scene packages for the actual visual grammar,
for example `cell_board`, `nonogram`, `pipe_flow`, `word_search`, or
`rubiks_net`.

When decomposing old shared files:

- keep puzzle-wide rendering/layout primitives only if they are truly
  scene-neutral;
- move puzzle-specific rules, solvers, transforms, and sampling recipes into
  the owning scene;
- do not preserve compatibility aliases or disabled legacy task ids;
- do not hide task/query routing in renamed shared files.

## Retired Patterns

Migrated puzzle scenes must not use task groups, task-family routing, task
complexity helpers, config-level query weights, or domain-local fixed-query
adapters. If a public task has internal query branches, use the repo-global
query-selection helper in the public task file and pass only resolved semantic
arguments into shared helpers.

# Physics Shared Boundary

Use this with `SCENE_MIGRATION_GUIDE.md` when migrating a physics scene.

## Purpose

Physics currently has 53 default-enabled public tasks across 36 public scenes.
The public scene ids are finer grained than the current source folders, which
are still organized as broad legacy families such as `circuits`, `mechanics`,
`optics`, and `waves`.

This document defines helper ownership for:

- `trace/tasks/physics/shared/`
- `trace/tasks/physics/<scene_id>/shared/`
- `trace/tasks/physics/<scene_id>/<objective_contract>.py`

It is not an acceptance or completion record. Use
`docs/ACTIVE_TASK_INVENTORY.md` and the task registry for current active task
ids.

## Current Public Scene Inventory

Current source folders group multiple public scenes. During migration, public
scene ids are the target packages.

| Legacy source family | Public scenes |
|---|---|
| `circuits` | `analog_meter`, `bridge_circuit`, `bulb_circuit`, `circuit_equivalent`, `circuit_state_change` |
| `switch_circuit` | `switch_circuit` |
| `electrostatic_field` | `electrostatic_field` |
| `buoyancy_density` | `buoyancy_density` |
| `manometer` | `manometer` |
| `hydraulic` | `hydraulic` |
| `graduated_cylinder` | `graduated_cylinder` |
| `electromagnetic_induction` | `electromagnetic_induction` |
| `free_body_forces` | `free_body_forces` |
| `gear_train` | `gear_train` |
| `magnetic_force` | `magnetic_force` |
| `wire_magnetism` | `wire_magnetism` |
| `vernier_caliper` | `vernier_caliper` |
| `collision` | `collision` |
| `lever` | `lever` |
| `mechanics` | `motion_graph`, `orbital_motion` |
| `stack_stability` | `stack_stability` |
| `spring` | `spring` |
| `pulley` | `pulley` |
| `lens_optics` | `lens_optics` |
| `ray_optics` | `ray_optics` |
| `refraction_layers` | `refraction_layers` |
| `shadow_cause` | `shadow_cause` |
| `thermal_mixing` | `thermal_mixing` |
| `thermometer` | `thermometer` |
| `thermodynamics` | `piston_cylinder`, `pv_diagram` |
| `wave_interference` | `wave_interference` |
| `waveform_panel` | `waveform_panel` |

## Domain Shared

`trace/tasks/physics/shared/` is for scene-neutral primitives reused by
multiple physics scenes.

Allowed domain-shared categories:

- technical-diagram style, background, noise, font, and legibility adapters
- neutral label tags, option-card layout, and vector-arrow geometry
- reusable units, exact arithmetic, formula helpers, and support sampling
- scene-neutral quantity, direction, bbox, point, and metadata helpers
- reusable renderer fragments only after they are identity-free and genuinely
  used by more than one public scene

Domain shared code must not know or branch on:

- public task ids
- public query ids
- objective contracts
- registered task classes
- sibling scene identities
- task-specific answer schemas
- task-specific prompt wording

Domain shared code must not construct final public `TaskOutput`.

Physics technical-diagram adapters should default to the same analytical theme
pool as analytical geometry scenes: 20 light themes plus 5 dark themes. The
graph-paper theme pool is an explicit opt-in for scenes whose task contract
requires reading plotted axes or grid measurements, currently `motion_graph`
and `pv_diagram`. Scene-local helper grids or guide marks should be rendered by
the scene and must not select the graph-paper style profile by accident.

## Scene Shared

`trace/tasks/physics/<scene_id>/shared/` owns one public scene's physical system
grammar and scene-specific reusable primitives.

Approved scene-shared role files:

- `state.py`
- `defaults.py`
- `sampling.py`
- `formulas.py`
- `mechanics.py`
- `circuitry.py`
- `ray_model.py`
- `layout.py`
- `rendering.py`
- `projection.py`
- `annotations.py`
- `prompts.py`
- `output.py`

Use only the role files that fit the scene. Avoid broad `runtime.py`,
`task_common.py`, `scene_common.py`, or task-named shared modules.

Scene shared code may know the scene's visual grammar, apparatus components,
physical constraints, projection rules, and scene-specific annotation roles. It
must not route behavior by public task id, query id, objective contract, public
task name, or registered class.

## Public Task Files

Each public task file owns its objective behavior:

- literal public `TASK_ID`
- `SUPPORTED_QUERY_IDS`
- query selection and validation
- objective-specific sampling constraints
- target, operand, option, and candidate construction when objective-specific
- answer binding
- `annotation_gt` binding
- dynamic prompt slots
- task-specific trace fields
- retry and final `TaskOutput`

The public task file may call scene-shared and approved domain-shared
primitives. It must not delegate objective behavior to a shared generator that
selects answers or annotations from public task/query identity.

## Prompt And Config Boundary

Current physics prompts and configs are still grouped by broad families for
unmigrated scenes:
`circuits`, `magnetism`,
`mechanics`, `optics`, `thermodynamics`, and `waves`.

During scene migration:

- move prompt assets to the public scene package, for example
  `prompts/physics/<scene_id>/physics_<scene_id>_v1.json`
- move scene defaults to `configs/domains/physics/<scene_id>.yaml`
- keep generation/rendering defaults in config, not public task routing
- remove config-level query weights or balanced query routing for migrated
  scenes
- keep prompt prose out of task modules

## Annotation And Query Policy

Physics annotation should mark minimal visible physical witnesses:

- force arrows, motion arrows, field arrows, rays, and path segments
- objects, masses, bulbs, resistors, switches, meters, pistons, and supports
- distance, level, tick, readout, angle, or label regions when they are
  operands
- selected visual option cards only when the option itself is the answer
  witness

Use map annotation when physical roles matter, such as input/output force,
left/right piston, source/target ray, known/unknown component, or before/after
state. Use scalar `point`, `bbox`, or `segment` when the task guarantees exactly
one witness. Use sets or sequences only for variable or ordered homogeneous
witnesses.

Query ids are semantic only. Valid physics query ids may encode mirrored
operators such as clockwise/counterclockwise, before/after, left/right, source
versus target, or input versus output when that role is user-facing. Do not use
query ids for renderer style, label values, numeric supports, target values,
layout variants, option letters, or sampled apparatus variants.

## Existing Cleanup Risks

These patterns must be removed from a scene before it becomes review-ready:

- `FixedPhysicsQueryVariantTaskMixin` or public-output rewriting adapters
- shared helpers that accept `query_id` only to change objective behavior
- shared helpers that branch on public task id, query id, class name, or
  objective contract
- broad legacy modules that register multiple public scenes from one source
  file
- config keys such as `query_id_weights` and `balanced_query_id_sampling`
- one-item set annotation for guaranteed single-witness tasks

Resolved example: the ray-optics renderer belongs to
`trace/tasks/physics/ray_optics/shared/rendering.py` and receives semantic
render arguments rather than public task or query identity.

Resolved example: the refraction-layers renderer belongs to
`trace/tasks/physics/refraction_layers/shared/rendering.py`; the public task
owns the option-letter answer, bend annotation binding, and `single` public
query id.

## Recommended Pilot

Start with `vernier_caliper`.

Rationale:

- one active public task
- one public scene
- isolated current source module
- limited renderer and annotation surface
- good test case for scene-local prompt/config split without cross-scene
  formula reuse decisions

After the pilot is review-ready, migrate one scene at a time. Do not migrate a
whole legacy source family in one pass unless every public scene inside it is
individually source-audited, taxonomy-audited, smoke-generated, gated, and
review-artifact-ready.

## Migration Procedure

For each physics scene:

1. Inventory active public tasks, query ids, source files, configs, prompt
   bundles, task docs, tests, and review artifacts.
2. Decide split/merge/delete status before moving code.
3. Move physical-system grammar into scene `shared/` role files.
4. Keep formulas and renderer fragments domain-shared only when reused across
   scenes and identity-free.
5. Rewrite each public task file to own query selection, answer binding,
   annotation binding, prompt slots, trace fields, retry, and final output.
6. Remove retired aliases, wrapper files, stale configs, stale prompt bundles,
   and stale review folders for that scene.
7. Smoke-generate every task and every supported query branch.
8. Add the scene to `SCENE_PACKAGE_REVIEW_CANDIDATE_SCENES` only after source
   boundaries are ready for migration gates.
9. Run scene-scoped migration/review gates.
10. Write manual source audit, taxonomy review, and migration test status files
    only after those gates really pass.
11. Generate review artifacts under `review/task-reviews/physics/<scene_id>/`.
12. Reload the review app index for that scene.
13. Commit the scene migration before starting another physics scene.

Do not call a physics scene migrated until human review in the browser app has
accepted it.

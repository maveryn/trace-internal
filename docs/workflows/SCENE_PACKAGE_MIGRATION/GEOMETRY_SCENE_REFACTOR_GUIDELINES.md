# Geometry Scene Refactor Guidelines

This is the geometry-domain companion to
`SCENE_REFACTOR_GUIDELINES.md`. It applies while migrating scenes under:

```text
trace/tasks/geometry/<scene_id>/
configs/domains/geometry/<scene_id>.yaml
review/task-reviews/geometry/<scene_id>/
```

Use it as the target structure for the first cleaned geometry scene, then apply
the same role boundaries scene-by-scene where they fit.

## Geometry Scene Package Shape

Most geometry scenes should use this structure:

```text
trace/tasks/geometry/<scene_id>/
  <objective_contract>.py
  ...
  shared/
    defaults.py
    state.py
    construction.py
    relations.py
    sampling.py
    rendering.py
    annotations.py
    prompts.py
    output.py
```

Only create files that are useful for the scene. A one-task scene can omit
`output.py` or `annotations.py` if the public task file is clearer without
them.

## File Responsibilities

### `defaults.py`

Scene-local code fallbacks only. YAML remains source of truth.

Geometry examples:

- answer support fallback tuples;
- angle/length/area support values;
- candidate option-count fallback tuples;
- canvas and diagram-size fallback values.

Do not keep broad `_TaskDefaults` dataclasses in public task files or in
catch-all shared modules when a small constant tuple or resolver is clearer.
Do not keep user-facing prompt text, static slots, examples, or required slot
declarations in `defaults.py`.

### `state.py`

Scene state, typed contracts, stable ids, and validation.

Geometry examples:

- point, segment, ray, circle, polygon, solid, panel, or option dataclasses;
- symbolic scene specs before rendering;
- final scene/sample dataclasses after target construction;
- stable entity-id helpers such as point ids, side ids, region ids, and option
  ids;
- sample validation that checks geometry consistency but does not choose task
  answers.

State must not render images, assemble prompts, or construct `TaskOutput`.

### `construction.py`

Reusable diagram construction primitives.

Geometry examples:

- build a right-triangle altitude layout;
- construct a circle with chord/secant/tangent points;
- create a coordinate-grid object set;
- place a regular polygon and its decomposition pieces;
- create visual options or panels before an objective picks the answer.

Construction may create candidate objects and relation inputs. It must not bind
the final answer or decide public annotation witnesses across several tasks.

### `relations.py`

Pure geometry formulas, theorem relations, classifiers, and validators.

Geometry examples:

- Pythagorean, tangent/secant, sector, similarity, congruence, proportionality,
  volume, and area formulas;
- angle-chase equation solvers;
- coordinate transforms and classifiers;
- polygon/solid measurement functions.

Relations must be deterministic and side-effect free. They must not import PIL,
build prompts, return `TaskOutput`, or branch by public task id.

### `sampling.py`

Axis resolution and neutral construction helpers.

Geometry examples:

- resolve scene/style/query axes;
- sample a supported answer value;
- choose safe diagram dimensions;
- build distractor candidates without choosing the public objective;
- select labels, font roles, and nonsemantic style axes through shared
  samplers.

Sampling may expose helpers such as `sample_circle_pair_inputs(...)` or
`build_endpoint_options(...)`. It must not expose a
`generate_<objective>_output(...)` function or a broad
`sample_for_query(query_id)` dispatcher that owns multiple public task
contracts.

### `rendering.py`

Diagram renderer, render params, style variants, and render maps.

Geometry examples:

- draw diagrams, grids, panels, solids, measurement tools, and option boards;
- place readable labels and measurement annotations;
- apply final layout jitter and scene rotation;
- return a render map that connects entity ids to final pixel points/bboxes.

Rendering must update entity geometry consistently with final placement,
rotation, scale, and label-layout changes. Public annotation must always be
projected from the final render map, never from hardcoded pre-jitter
coordinates.

### `annotations.py`

Scene-local annotation projection helpers.

Geometry examples:

- map point ids to `point_set` or `keyed_point_map`;
- map region/side/option ids to `bbox_set` or `keyed_bbox_map`;
- build point-pair witnesses for segments or routes;
- expose role-key helpers where operand roles matter.

This file may project witnesses from render maps, but public task files still
decide which witnesses are correct for the objective.

### `prompts.py`

Prompt loading and thin prompt artifact assembly around external prompt assets.

Geometry examples:

- prompt bundle lookup;
- merge prompt-asset static slots with task-provided dynamic slots;
- prompt template key rendering;
- prompt trace metadata;
- common task-neutral slot formatting such as label quoting.

Prompt text, JSON examples, static slots, and required slot declarations must
come from prompt assets, not task code or ordinary config. New text must use
`annotation`, not historical terminology.

### `output.py`

Common geometry scene output assembly, only if objective-neutral.

Allowed:

- assemble common trace sections;
- include rendered entities, render map, prompt metadata, answer, annotation,
  background/noise metadata, and task versions;
- accept already-bound answer and annotation artifacts from the public task.

Forbidden:

- branching by public task id, objective contract, or top-level query id;
- choosing target objects;
- computing the task answer;
- selecting annotation witnesses;
- replacing public task files with shared full-output functions.

If `output.py` starts deciding what theorem, metric, option, or target is being
asked, move that code back to the public task file.

## Public Geometry Task Files

Each `trace/tasks/geometry/<scene_id>/<objective_contract>.py` must:

- define exactly one registered public task class;
- set `domain = "geometry"` and `scene_id = "<scene_id>"`;
- own objective-specific sampling and semantic constraints;
- bind final `answer_gt`;
- bind final `annotation_gt`;
- call shared construction/rendering/prompt/output helpers only after the
  objective is already determined;
- expose `query_id` only for narrow operand variants inside the same objective
  contract.

Do not use fixed-query wrappers, query-subset mixins, copied sibling modules,
or a shared theorem dispatcher that hides answer/annotation binding.

## Geometry Annotation Rules

Geometry annotation should mark minimal visual witnesses.

Use:

- `point_set` for homogeneous point witnesses where roles do not matter;
- `keyed_point_map` when point roles matter, such as `start`, `end`,
  `target_angle_vertex`, `known_point_a`;
- `bbox_set` for homogeneous object/region/side witnesses where roles do not
  matter;
- `keyed_bbox_map` when object roles matter, such as `outer_region`,
  `shaded_region`, `known_side`, `target_side`;
- point-pair schemas for line/segment/path witnesses when the visible witness
  is naturally a segment rather than a filled region.

Do not annotate prompt-only labels, numeric answer text, or option letters
unless the task is a true visual option-image task and the selected option
image is the visual answer.

## Geometry-Specific Scene Patterns

### Single Diagram Theorem Scenes

Examples: `circle_pair_tangents`, `right_triangle_altitude_theorem`,
`concentric_chord`, `paper_fold`.

Recommended split:

- `state.py`: symbolic points/segments/circles and target roles.
- `relations.py`: theorem formulas.
- `construction.py`: build a valid diagram input.
- `rendering.py`: draw the diagram and final render map.
- public task file: select the theorem target, bind answer and annotation.

### Algebraic Marked-Diagram Scenes

Examples: `marked_polygon_equation`, `parallel_segment_proportion`,
`special_quadrilateral`, `angle_relations`.

Recommended split:

- `state.py`: marked sides/angles and expression specs.
- `relations.py`: equation setup/solver.
- `construction.py`: choose consistent numeric values and expression forms.
- `rendering.py`: render marks/expressions with readout-safe fonts.
- public task file: choose target variable/value and annotation roles.

### Option / Panel Scenes

Examples: `function_panels`, `coordinate_panels`, `shape_gallery`,
`coordinate_plane` option-label tasks.

Recommended split:

- `state.py`: panel/option ids and candidate specs.
- `construction.py`: build correct and distractor candidates.
- `relations.py`: property/classifier/transform functions.
- `rendering.py`: option grid or panel rendering.
- `annotations.py`: selected option bbox or keyed source/reference witnesses.
- public task file: choose target condition, construct unique correct option,
  bind label answer and selected visual option annotation.

### Graph-Paper / Coordinate Scenes

Examples: `graph_paper`, `coordinate_plane`, `coordinate_composite`.

Recommended split:

- `state.py`: coordinate entities and object ids.
- `relations.py`: slope, area, perimeter, transformation, relation, and
  classifier functions.
- `construction.py`: grid object sampling and uniqueness constraints.
- `rendering.py`: grid/axis/object renderer and coordinate-to-pixel mapping.
- `annotations.py`: projected point/bbox witnesses.
- public task file: choose target measurement/count/comparison objective and
  bind answer/annotation.

### Composite / Solid Measurement Scenes

Examples: `composite_shape`, `rectangular_solid`, `solid_formula`,
`solid_revolution`, `volume_equivalence_conversion`.

Recommended split:

- `state.py`: shape/solid component specs and dimension ids.
- `relations.py`: area/perimeter/volume/surface formulas.
- `construction.py`: choose dimensions and build a uniquely solvable diagram.
- `rendering.py`: draw 2D/3D schematic, labels, and dimension guides.
- `annotations.py`: region, side, dimension, or object witnesses.
- public task file: own the target metric and final formula path.

## Starter Exemplar: `area_partition`

Use `area_partition` as the first cleaned geometry exemplar:

```text
trace/tasks/geometry/area_partition/
  total_area_value.py
  shared/
    defaults.py
    state.py
    construction.py
    relations.py
    rendering.py
    annotations.py
    prompts.py
    output.py  # optional; only if objective-neutral
```

Expected placement:

- `state.py`: partition region specs, entity ids, sampled scene contract.
- `relations.py`: area arithmetic.
- `construction.py`: valid partition/known-target region construction.
- `rendering.py`: draw outer/inner/shaded regions and final bbox map.
- `annotations.py`: keyed region annotation projection.
- `prompts.py`: scene/task prompt artifact builder.
- `total_area_value.py`: target relation, numeric answer, keyed annotation
  binding, task trace.

## Starter Exemplar: `bearing_route`

Use `bearing_route` as the first multi-task geometry exemplar:

```text
trace/tasks/geometry/bearing_route/
  endpoint_position_label.py
  final_bearing_value.py
  shared/
    defaults.py
    state.py
    construction.py
    relations.py
    sampling.py
    rendering.py
    annotations.py
    prompts.py
    output.py  # optional; only if objective-neutral
```

Expected placement:

- `state.py`: station/route/segment/candidate ids and scene dataclasses.
- `relations.py`: bearing normalization, turn/bearing math, endpoint
  projection.
- `construction.py`: route and candidate endpoint construction.
- `rendering.py`: polyline/label/candidate renderer and final point map.
- `annotations.py`: route point/segment/candidate witness projection.
- `endpoint_position_label.py`: construct unique candidate answer and selected
  candidate annotation.
- `final_bearing_value.py`: compute final bearing and bind route/target
  direction annotation.

## Domain Shared Promotion Candidates

During the scene loop, record possible promotions but do not move new code into
`trace/tasks/geometry/shared/` immediately.

Likely geometry-domain candidates:

- point/vector/segment/circle/polygon formula primitives;
- scene rotation/layout-jitter with annotation projection;
- readout-safe label placement helpers;
- keyed point/bbox annotation builders;
- visual option-panel layout;
- dimension-guide rendering primitives;
- simple solver utilities reused by several theorem scenes.

Keep scene-local:

- one-scene theorem builders;
- scene-specific renderers;
- scene-specific dynamic prompt slots;
- shape/solid specs used by only one scene;
- formula dispatchers whose names depend on one scene vocabulary;
- `TaskOutput` assembly that is not strictly objective-neutral.

At the final geometry-domain checkpoint, compare all recorded candidates and
promote only narrow primitives reused by at least two cleaned geometry scenes.

## Geometry Scene Completion Note

Each completed geometry scene section in `geometry.md` should include:

```text
Completion note:
- source ownership:
- split/merge decision:
- scene shared helpers:
- domain shared candidates deferred:
- config/prompt/docs updated:
- task reviews regenerated/stale folders purged:
- checks:
- final post-migration review:
- blockers:
```

# Geometry Shared Boundary

Use this with `SCENE_MIGRATION_GUIDE.md` when migrating a geometry scene.

## Purpose

Geometry has many scenes that share low-level geometry, diagram, annotation,
and rendering primitives, but public task ownership must stay in the public
task files. This document defines the boundary for:

- `trace/tasks/geometry/shared/`
- `trace/tasks/geometry/<scene_id>/shared/`
- `trace/tasks/geometry/<scene_id>/<objective_contract>.py`

Use `docs/ACTIVE_TASK_INVENTORY.md` for current geometry task counts. This
document defines helper ownership only.

## Domain Shared

`trace/tasks/geometry/shared/` is for scene-neutral geometry primitives reused
by multiple scenes or approved geometry families.

Allowed domain-shared categories:

- vector, distance, bbox, and point serialization helpers
- public annotation artifact normalization helpers
- readout, dimension-line, label, and marker drawing primitives
- geometry diagram style, background, noise, font, and shape-style adapters
- graph-paper, coordinate-frame, panel-grid, and option-layout primitives
- polygon, conic, angle, length, slope, transformation, and quadrilateral math
- single-object whole-diagram transform helpers
- JSON-ready metadata serialization helpers

Domain shared code must not know or branch on:

- public task ids
- public query ids
- objective contracts
- registered task classes
- sibling scene identities
- task-specific answer schemas
- task-specific prompt wording

Domain shared code must not construct final public `TaskOutput`.

## Scene Shared

`trace/tasks/geometry/<scene_id>/shared/` owns one scene's visual grammar and
scene-specific reusable primitives.

Allowed scene-shared role files:

- `state.py`
- `defaults.py`
- `sampling.py`
- `construction.py`
- `geometry.py`
- `measurements.py`
- `layout.py`
- `rendering.py`
- `projection.py`
- `annotations.py`
- `prompts.py`
- `output.py`

Scene shared code may know the scene's visual grammar, construction rules,
layout conventions, diagram entities, and scene-specific annotation roles. It
must not route behavior by public task id, query id, objective contract, public
task name, or registered class.

Avoid generic `runtime.py` in migrated scenes. Existing runtime files should be
split into the role files above during scene migration.

## Public Task Files

Public task files own objective behavior:

- literal public `TASK_ID`
- supported local query ids
- query selection and validation
- objective-specific sampling constraints
- answer binding
- `annotation_gt` binding
- dynamic prompt slots
- task-specific trace fields
- retry and final `TaskOutput`

The public task file may call scene-shared and domain-shared primitives, but it
must not delegate the objective to a shared runtime that chooses answer or
annotation behavior from public identity.

## Domain-Shared Guidance

Use this as a boundary guide before geometry scene migrations.

### Keep Domain-Shared

These modules are approved domain-shared helpers in their role, subject to
normal API cleanup:

| Module | Boundary |
|---|---|
| `annotation_values.py` | Public annotation artifact normalization and JSON-ready point/bbox payload helpers. |
| `background_defaults.py` | Geometry background default loading. |
| `coordinate_panel_grid.py` | Coordinate panel layout and graph-to-pixel projection primitives. |
| `diagram_style.py` | Geometry diagram style/background/readability adapters. |
| `graph_panel_layout.py` | Graph panel layout and coordinate-frame helpers. |
| `graph_paper.py` | Lattice/grid sizing and graph-paper sampling primitives. |
| `graph_rendering.py` | Graph-paper style, scaling, and coordinate-frame rendering primitives. |
| `measurement_rendering.py` | Bbox/readout/dimension-line/right-angle drawing helpers. Labels remain plain by default; backplates are opt-in. |
| `metadata_serialization.py` | Geometry trace metadata JSON normalization. |
| `noise_defaults.py` | Geometry post-image noise default loading. |
| `option_count.py` | Geometry visual option-count and panel-grid shape helpers. |
| `quadrilateral_prototypes.py` | Neutral quadrilateral prototype construction and classification. |
| `scene_transform.py` | Whole-scene transform and annotation projection support. |
| `shape_style.py` | Geometry shape-style sampling and background contrast adapters. |
| `vector2d.py` | Point/vector math and point serialization. |

### Keep Domain-Shared As Approved Families

These modules are valid domain-shared surfaces when kept identity-free. During
scene migration, do not add task/query dispatch to them.

| Module | Family |
|---|---|
| `comparison.py` | Multi-object spatial clearance/comparison geometry primitives. |
| `labeled_point_annotation.py` | Graph-point annotation artifacts. |
| `multi_polygon_scene.py` | Multi-polygon scene object drawing primitives. |
| `point_labels.py` | Neutral point-label drawing helpers. |
| `polygon_scene_helpers.py` | Pixel/graph polygon conversion and reference polygon drawing. |
| `polygon_transformations.py` | Neutral polygon transformations and vertex mapping. |
| `pythagorean.py` | Integer right-triangle enumeration and validation for scenes that need Pythagorean case pools. |
| `render_variation.py` | Small scene-neutral render parameter sampling. |
| `single_object_scene.py` | Graph-scene canvas/finalization helpers shared by graph-style scenes. |

### Retired During Scene Migration

These were removed as final domain-shared ownership surfaces. Do not reintroduce
them during scene migration.

| Module | Target |
|---|---|
| `angle_geometry.py` | Removed after migration because no active geometry scene referenced it. |
| `composite_measurement_cases.py` | Removed. The remaining angle-relations primitives live in `angle_relations/shared/spatial_primitives.py`; concrete case builders belong to owning scenes. |
| `composite_measurement_task.py` | Removed. Public task files own final `TaskOutput`, prompt slots, answer binding, and annotation binding. |
| `consolidated_source.py` | Removed. Migrated scenes must not rewrite source-task outputs. |
| `consolidated_sampling.py` | Removed. Use task-owned query selection or repo-global neutral sampling helpers. |
| `conic_geometry.py` | Removed after migration because no active geometry scene referenced it. |
| `length_geometry.py` | Removed after migration because no active geometry scene referenced it. |
| `multi_angle_scene.py` | Removed after migration because no active geometry scene referenced it. |
| `multi_shape_scene.py` | Removed after migration because no active geometry scene referenced it. |
| `polygon_geometry.py` | Removed after migration because no active geometry scene referenced it. |
| `prompt_text.py` | Removed. Prompt prose belongs in prompt assets. |
| `slope_geometry.py` | Removed after migration because no active geometry scene referenced it. |

## Family Promotion Candidates

Promotion candidates should be handled as separate cleanup after the relevant
scene migration is review-ready, unless the scene is blocked without the shared
family.

| Family | Candidate shared surface | Scenes to compare |
|---|---|---|
| Circle diagrams | circle centers, radii, chords, tangents, secants, arcs, circle labels | `circle_theorem`, `circle_pair_tangents`, `circle_centerline_overlap`, `concentric_chord`, `incircle_tangents`, `circle_polygon_composite` |
| Similarity/proportion | proportional segment equations, corresponding side maps, scale factors, marked correspondence | `similar_figure_measure_transfer`, `triangle_congruence_correspondence`, selected `triangle_relations` |
| Polygon equation marks | equal-side/equal-angle marks, expression labels, variable solution setup | `polygon_equation_diagram`, `special_quadrilateral`, `triangle_congruence_correspondence`, selected `triangle_relations` |
| Solid/volume diagrams | prism/cylinder/cone dimensions, volume-transfer layouts, orthographic panels | `rectangular_solid`, `solid_formula`, `solid_cross_section`, `solid_revolution`, `container_volume_transfer`, `volume_equivalence_conversion`, `cuboid_views` |
| Curvilinear composites | sector/semicircle/quarter-circle cutouts and caps | `composite_shape`, `sector`, `circle_polygon_composite`, `tangent_packing` |
| Graph-coordinate scenes | graph canvas, labels, options, point/shape projection | `graph_paper`, `coordinate_plane`, `coordinate_panels`, `coordinate_composite`, `function_graph`, `function_panels` |

## Per-Scene Audit Guidance

Do not maintain a scene-by-scene migration inventory in this document. Before
migrating a geometry scene, inspect the live source, active inventory, prompt
bundle, config, tests, and review artifacts for that scene. Record scene-local
findings in the scene review artifacts or migration handoff, not in this
shared-boundary policy.

## Migration Procedure

For each future geometry scene migration:

1. Inventory public tasks, query ids, current shared files, prompts, configs,
   tests, and review artifacts.
2. Move only scene grammar into scene `shared/`; use approved domain helpers
   for neutral primitives.
3. Keep query selection, answer binding, annotation binding, prompt slots,
   trace fields, retry, and final `TaskOutput` in public task files.
4. Record but do not immediately promote new cross-scene helper candidates.
5. Run scene-scoped migration/review gates.
6. Generate review artifacts only after gates pass.
7. Reload the review app index.
8. Commit the scene migration before starting another scene.

Do not update scene migration status based only on file movement or passing
imports. The source boundary must match this document and the scene migration
guide.

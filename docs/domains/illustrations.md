# Illustrations Domain Contract

Use this document for illustration-domain rules. Exact active scenes and tasks
live in `docs/ACTIVE_TASK_INVENTORY.md` and `docs/tasks/illustrations/`.

## Scope
Illustrations covers synthetic drawings of recognizable objects, environments,
object parts, and derived visual-composition tasks built from those scenes. It
does not cover natural images, pure icon grids, or arbitrary caption/OCR tasks.

Use `illustrations` when semantic object/part records and their rendered pixel
geometry are the source of truth. Use `icons` for abstract reusable icon fields
and `pages` for document-like layouts.

## Scene Boundary
A scene is the stable illustration grammar: object catalog, environment type,
part vocabulary, reference/cutout/option scaffold, or scene-comparison layout.
Visual styles such as vector, top-down pixel, isometric pixel, palette, and
background treatment may vary inside a scene when the same verifier records are
available.

Derived composition scenes, such as cutout reconstruction or missing patch
options, are valid scenes when the public task is about the composition
interface rather than the source illustration category. Record the source scene
or renderer as metadata, not as a public task identity layer.

## Task And Query Boundary
Split tasks when the objective changes between object count, part count,
visible-part reasoning, spatial relation, scene difference, missing patch,
cutout matching, or option selection. Object category or style variation may
remain a parameter when the answer/annotation/program contract is stable.

Avoid broad tasks that collapse rich illustrations into icon-like collections.
If a task can be represented equally well as an icon-field count, either move it
to `icons` or make the illustration scene provide richer object/context
grounding.

## Annotation Policy
Prompt-facing annotation should mark visible object bboxes, semantic part
bboxes, paths, regions, source/candidate panels, or other decisive witnesses in
final-image coordinates. Use keyed annotation when source and target,
before/after, reference/candidate, or object/part roles matter.

Do not annotate decorative sky/sun/cloud elements unless a task explicitly
promotes them to foreground semantic objects.

## Rendering
Objects and parts must be drawn from the same trace records used by verifiers.
Environment scenes should keep placements natural, such as sky-capable objects
in sky bands, vehicles on roads, water objects in water, and land objects on
valid ground/surface regions.

Style and background variation must remain non-semantic unless queried. Dense
scenes should cap foreground object counts to preserve readable object and part
bboxes.

## Shared Code
Reusable object catalogs, scene grammars, environment layout, part metadata, and
renderer/style helpers belong under `trace/tasks/illustrations/shared/`.
Scene-local shared modules should own scaffolds tied to one illustration scene.

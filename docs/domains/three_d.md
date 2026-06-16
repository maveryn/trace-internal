# Three-D Domain Contract

Use this document for three_d-domain rules. Exact active scenes and tasks live
in `docs/ACTIVE_TASK_INVENTORY.md` and `docs/tasks/three_d/`.

## Scope
`three_d` covers rendered 3D scenes with explicit camera pose, world-space
geometry, projection metadata, and metadata-grounded verifiers. Tasks reason
over spatial relations, camera distance, height, occlusion, support surfaces,
multi-view correspondence, object counts, fixtures, streets, rooms, or warehouse
layouts.

Use `three_d` for perspective 3D environments. Use `geometry` for abstract
geometric solids and `puzzles` for abstract 3D puzzle boards.

## Scene Boundary
A three_d scene is the stable 3D environment grammar: object scene, object
cluster, surface fixture, room, street, warehouse, or another camera-projected
world. Scene variants may vary room/platform type, camera orbit band, surface
style, object profiles, lighting, or palette when the same projection and
verifier contract holds.

Create a new scene when the environment grammar, camera/view interface,
candidate option surface, or world-coordinate verifier changes materially.

## Task And Query Boundary
Split tasks when the program changes between object count, attribute count,
distance/rank selection, relation, occlusion order, height extremum, multi-view
matching, fixture count, route/lane relation, or warehouse path reasoning.

Valid `query_id` axes include closest/farthest, left/right, in-front/behind,
same/different support, target attribute choice, or bounded relation direction
inside one stable program. Object profile, camera pose, room style, and surface
style are metadata/style axes unless directly queried.

## Annotation Policy
Prompt-facing annotation should mark projected visible objects, fixtures,
reference surfaces, candidate markers, option panels, or route/path witnesses in
final-image coordinates. Use keyed annotation when reference/candidate,
source/target, before/after, left/right view, or operand roles matter.

Answers must come from finalized 3D metadata such as world coordinates, camera
distances, support assignment, projected bboxes, or occlusion ordering, not from
pixel inference.

## Rendering And Assets
Object profiles should be visually recognizable enough for prompt names and
should expose stable projected bboxes or point markers. Semantic color, size,
height, depth, support, and relation predicates must be recorded in trace
metadata when queried.

Three_d scenes should render from one of the canonical source-canvas presets by
default: `1200x800` landscape, `800x1200` portrait, or `960x960` square. The
sampled preset is render metadata, not a query axis or task split. If a task
composes multiple panels/options, each source panel should use the same sampled
canonical preset unless the task has a documented reason to override it; the
final composed image may be downscaled to stay under the domain pixel cap while
projecting all answer/evidence coordinates after final placement.

Prompt-facing named colors must use the repo-wide canonical 10-color palette
from `trace.tasks.shared.named_colors` and should be rendered in prompts as
`<color name> [#RRGGBB]`. Scene-specific palettes are acceptable only for
unnamed visual/style variation that is not sampled as a named answer or prompt
predicate.

Use the 3D object review surfaces for object-fidelity audits. Style, lighting,
camera, and object-palette variation must not encode answer value, query id,
correct option, relation truth, or construction order unless explicitly queried.

## Shared Code
Reusable camera, projection, object-profile, room, street, warehouse, and
fixture helpers belong under `trace/tasks/three_d/shared/` when reused across
scenes. Scene-local shared modules should own environment-specific construction,
rendering, and annotation projection.

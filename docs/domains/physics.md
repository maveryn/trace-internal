# Physics Domain Contract

Use this document for physics-domain rules. Exact active scenes and tasks live
in `docs/ACTIVE_TASK_INVENTORY.md` and `docs/tasks/physics/`.

## Scope
Physics covers diagram-grounded mechanics, circuits, optics, and related
formula tasks where the operative quantities, directions, components, and
geometry are visible or explicitly implied by the diagram.

Use `physics` when physical relationships are the semantic source of truth. Use
`geometry` for purely geometric constructions and `pages` for document-like
explanatory diagrams.

## Scene Boundary
A physics scene is the stable physical system grammar: free-body diagram,
incline, pulley, circuit, ray/optics setup, fluid/pressure layout, motion path,
or measurement panel. Visual style, font, component palette, orientation, and
non-semantic distractor labels may vary inside a scene.

Create a new scene when the physical system, component grammar, or diagram
scaffold changes enough that a different formula/program or annotation contract
is needed.

## Task And Query Boundary
Split tasks by formula/program schema: force balance, torque, work/energy,
circuit equivalent value, optical path, motion time/distance, pressure, or
component selection should be distinct when operand roles or final operators
differ.

Valid `query_id` axes include mirrored directions, input/output unknown choice
inside the same formula, component target choice, or threshold/rank direction
when the program and annotation roles stay stable.

## Annotation Policy
Annotation should mark visible physical witnesses: force arrows, masses,
components, nodes, rays, target points, distances, angles, surfaces, or
measurement labels. Use keyed annotation for role-bound operands such as input
force and output force, resistor A and resistor B, source ray and reflected ray,
or object and support.

Do not annotate decorative apparatus parts unless they are operands or queried
witnesses.

## Prompt And Rendering
All required values must be visible or diagram-implied by explicit labels.
Avoid hidden constants or physical assumptions unless the prompt and task
contract make them part of the visible setup.

Early mechanics tasks should keep vectors axis-aligned unless vector
decomposition is the objective. Labels and arrows must be legible and
collision-aware.

## Shared Code
Reusable physical formulas, component sampling, diagram projection, rendering,
and annotation helpers belong under `trace/tasks/physics/shared/`. Scene-local
shared modules should own helpers tied to one physical system grammar.

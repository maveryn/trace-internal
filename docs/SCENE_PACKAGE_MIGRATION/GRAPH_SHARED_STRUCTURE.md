# Graph Shared Boundary

This is the graph-domain companion to `SCENE_MIGRATION_GUIDE.md`. It defines
where graph algorithms, renderers, and scene-local helpers should live during
scene-package migration. It is not an active task inventory; use
`docs/ACTIVE_TASK_INVENTORY.md` for current graph scenes and task ids.

## Core Rule

One public graph task file owns one public objective contract. The task file
owns:

- literal public `TASK_ID`
- local `SUPPORTED_QUERY_IDS`
- query validation and semantic argument selection
- objective-specific candidate or target construction
- answer binding and `annotation_gt` binding
- task-specific prompt slots and trace fields
- final `TaskOutput` construction

Graph shared code may provide primitives. It must not accept or branch on
public `task_id`, `query_id`, objective names, registered class names, or sibling
task identity.

## Shared Layers

Use the narrowest layer that fits.

### Cross-Domain Shared

Use `trace/tasks/shared/graph_algorithms.py` only for representation-neutral
algorithms over plain adjacency structures, such as BFS distances, connected
components, unique shortest paths, topological order, bridges, or articulation
points.

These helpers must not depend on graph-domain sample records, prompt labels,
render params, visual roles, or task ids.

### Graph-Domain Shared

Use `trace/tasks/graph/shared/` for reusable graph-domain primitives used by
multiple graph scenes:

- graph label assets and label pools
- graph style, font, palette, and visual defaults
- generic graph sample dataclasses
- shared node/edge geometry and projection helpers
- shared graph render components
- graph-domain prompt JSON example helpers when reused across scenes

Domain-shared modules must stay scene-neutral and identity-free. If a helper is
only used by one scene, move or keep it under that scene's `shared/`.

### Scene-Local Shared

Use `trace/tasks/graph/<scene_id>/shared/` for one-scene reusable code.
Approved role files are:

- `state.py`
- `defaults.py`
- `sampling.py`
- `algorithms.py`
- `metrics.py`
- `layout.py`
- `rendering.py`
- `annotations.py`
- `prompts.py`
- `output.py`
- `option_rendering.py`

Avoid names such as `scene_common.py`, `task_common.py`, `instance.py`,
`runtime.py`, or objective-named shared modules. A root `_lifecycle.py` is
allowed only for neutral scene plumbing and must not assemble public objective
outputs.

## Scene Notes

These notes identify likely ownership risks, not completion status.

| Scene | Migration concern |
| --- | --- |
| `adjacency` | Ensure root lifecycle code does not assemble final public outputs. |
| `automaton` | Keep DFA/NFA simulation primitives in shared code, but task files own option answer binding. |
| `binary_tree` | Keep traversal/tree algorithms scene-local unless reused by another graph scene. |
| `flow_network` | Split broad instance builders into sampling, algorithms, rendering, annotations, and task-owned output binding. |
| `graph_options` | Keep visual option rendering reusable, but option correctness and answer binding belong in public task files. |
| `metro` | Remove query routing from shared instance/scene helpers; pass semantic route arguments instead. |
| `node_link` | Repair any shared lifecycle/runtime that centralizes task/query plumbing before generating review artifacts. |
| `pedigree_chart` | Replace `scene_common.py` / `task_common.py` style files with role files and task-owned output binding. |
| `phylogeny_tree` | Keep tree construction/rendering scene-local; public tasks own relationship or path objectives. |
| `pipe_network` | Split route simulation from final answer binding; shared code should receive semantic flow/path arguments. |

## Node-Link Repair Checklist

`node_link` is the highest-risk graph scene because many objectives share the
same visual scaffold. Before review artifacts are generated:

1. Remove shared code that branches on public task or query identity.
2. Move node-link-only sampling recipes into `node_link/shared/sampling.py`.
3. Move pure node-link algorithms into `node_link/shared/algorithms.py` or
   `node_link/shared/metrics.py`.
4. Keep genuinely reusable renderer/projection components in
   `trace/tasks/graph/shared/`.
5. Rewrite each public task file so it owns query selection, answer binding,
   annotation binding, prompt slots, trace fields, and final output.
6. Smoke-generate every task and supported query branch.
7. Run the scene-scoped migration gate from `ENFORCEMENT_TESTS.md`.
8. Generate review artifacts only after taxonomy review, manual source audit,
   and migration tests pass.

## Review-Ready Definition

A graph scene is review-ready only when:

- public task files own objective behavior;
- scene shared files are role-named and identity-free;
- algorithms live at the narrowest reusable layer;
- prompt prose comes from prompt assets;
- answer and annotation come from the same execution trace;
- every supported query branch smoke-generates;
- scene-scoped migration tests pass;
- fresh review artifacts exist under `review/task-reviews/`;
- the review app index has been reloaded.

Human acceptance in the browser app is still required before calling the scene
migrated.

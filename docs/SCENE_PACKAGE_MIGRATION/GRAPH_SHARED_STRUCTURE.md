# Graph Scene-Package Migration Plan

This document is the graph-domain companion plan for scene-package migration.
It is intentionally more specific than `SCENE_MIGRATION_GUIDE.md` because graph
has several scenes that share graph algorithms, graph renderers, label assets,
and topology dataclasses.

The immediate migration target is `graph/node_link`. The plan is written so
later scenes can follow the same ownership boundaries instead of repeating the
same mistakes.

## Current Domain Inventory

The graph domain currently has 10 active scenes and 61 active public tasks.

| Scene | Active tasks | Current migration state | Main source-boundary issue |
|---|---:|---|---|
| `adjacency` | 5 | Review-candidate shape, mostly aligned | Scene root `_lifecycle.py` still assembles some final outputs for component-count tasks. Shared role files are otherwise close to target. |
| `automaton` | 4 | Review-candidate shape, partially aligned | Acceptance tasks use `_lifecycle.py`; state-simulation tasks are more task-owned. Shared role files are close to target. |
| `binary_tree` | 7 | Review-candidate shape, migrated to contract | Scene-local role modules own identity-free state, sampling, algorithms, rendering, annotations, prompts, and output fragments; public files own task ids, query ids, and semantic objective plans consumed by a private lifecycle. |
| `flow_network` | 2 | Not migrated to contract | `shared/instance.py` is a scene builder/orchestrator. |
| `graph_options` | 2 | Not migrated to contract | `shared/structure_match.py` is one large mixed sampler/renderer/task helper. |
| `metro` | 4 | Not migrated to contract | `shared/instance.py` branches on `query_id`; `shared/scene_common.py` mixes algorithms, sampling, rendering, and projection. |
| `node_link` | 27 | Registered as review-candidate but not correctly migrated | `shared/lifecycle.py` is invalid: it is a disallowed shared filename and centralizes query/task plumbing, annotation projection, trace payload, and final output construction. |
| `pedigree_chart` | 2 | Not migrated to contract | `shared/scene_common.py` and `shared/task_common.py` are disallowed role names and include task-facing logic. |
| `phylogeny_tree` | 4 | Not migrated to contract | `shared/scene_common.py` and `shared/task_common.py` are disallowed role names; builder classes hide task behavior. |
| `pipe_network` | 4 | Not migrated to contract | `shared/instance.py` branches on `query_id`; `shared/scene_common.py` mixes algorithms, sampling, rendering, and projection. |

Only `adjacency`, `automaton`, and `node_link` are currently in the
review-candidate registry. `node_link` must be repaired before review artifacts
are regenerated.

## Core Ownership Rule

One public task file owns one public objective contract.

Public task files must own:

- literal `TASK_ID`
- `SCENE_ID`
- local `SUPPORTED_QUERY_IDS`
- query selection and query validation
- objective-specific semantic arguments
- objective-specific target/candidate construction when it is not purely
  scene-generic
- answer binding
- `annotation_gt` binding
- dynamic prompt slots and prompt/query key selection
- task-specific trace fields
- final `TaskOutput` construction

Public task files may call shared primitives. They must not hand an objective
plan to a shared runtime that chooses query behavior or builds the final
`TaskOutput`.

## Graph Shared Layers

Graph code should be placed at the narrowest reusable layer that fits.

### Cross-Domain Shared

Use `trace/tasks/shared/graph_algorithms.py` only for representation-agnostic
algorithms over plain adjacency mappings. These helpers should not depend on
graph-domain sample types, render types, prompt labels, or visual semantics.

Good candidates:

- BFS distances and shortest-path counts
- connected components over adjacency maps
- unique shortest-path reconstruction
- unique topological order
- future pure algorithms if reused across domains, such as bridges or
  articulation points over a plain undirected adjacency map

### Graph-Domain Shared

Use `trace/tasks/graph/shared/` for utilities reused by multiple graph scenes.
These helpers may depend on graph-domain concepts such as graph labels,
`GraphTopologySample`, graph render params, graph fonts/styles, or graph-scene
metadata, but must not depend on a specific public task id.

Keep or promote these categories here:

- graph-domain labels and label pools
- graph-domain readable style/defaults/noise/background helpers
- shared node-link-style renderer used by multiple graph scenes
- graph render dataclasses and projection helpers used by node-link,
  automaton, flow-network, metro, pipe-network, or tree-style scenes
- graph-domain prompt JSON example helpers when reused across graph scenes
- graph-domain sample types that represent generic labeled topology

Current graph-domain shared files that are legitimately reused across scenes:

- `label_assets.py`
- `style.py`
- `visual_defaults.py`
- `task_support.py` where helpers are genuinely graph-domain-wide
- `graph_sample_types.py`
- `graph_topology_helpers.py` when used by several scenes
- `graph_scene.py` and `graph_renderer.py`
- `graph_render_context.py`
- `graph_render_edges.py`
- `graph_render_geometry.py`
- `graph_render_layout.py`
- `graph_render_nodes.py`
- `graph_render_panel.py`
- `graph_render_projection.py`
- `graph_render_types.py`

Current graph-domain shared files that appear node-link-specific and should be
re-homed during the `node_link` migration unless another scene has a concrete
need for them:

- `graph_bridge_articulation_sampling.py`
- `graph_common_neighbor_sampling.py`
- `graph_component_sampling.py`
- `graph_degree_sampling.py`
- `graph_edge_path_label_sampling.py`
- `graph_edge_sampling.py`
- `graph_feasibility.py`
- `graph_isolation_sampling.py`
- `graph_label_color_sampling.py`
- `graph_mst_sampling.py`
- `graph_node_degree_sampling.py`
- `graph_path_order_sampling.py`
- `graph_profile_sampling.py`
- `graph_reachability_sampling.py`
- `graph_source_sink_sampling.py`

The old broad `graph_sampling.py` facade has been removed. Graph scenes must
import concrete graph-shared modules or scene-local role modules such as
`graph/node_link/shared/sampling.py`; do not recreate a facade that hides
ownership.

### Scene-Local Shared

Use `trace/tasks/graph/<scene_id>/shared/` for code reused by tasks in exactly
one graph scene.

Allowed graph scene-shared role files are:

- `state.py`
- `sampling.py`
- `algorithms.py`
- `rendering.py`
- `annotations.py`
- `prompts.py`
- `output.py`
- `defaults.py`
- `layout.py`
- `styles.py`
- `labels.py`
- `metrics.py`
- `topology.py`
- `projection.py`
- `option_rendering.py`

Scene shared must not:

- accept or branch on public `task_id`
- accept or branch on public `query_id`
- accept or branch on public objective-contract names
- export public query-id routing tables
- build final `TaskOutput`
- register tasks
- contain task-named runtime files
- hide copied public task bodies

If shared code needs to know which query branch is running, the public task file
must resolve the semantic value first and pass neutral arguments instead.

Example:

- Bad shared argument: `query_id="directed_max_in_degree_value"`
- Good shared arguments: `directed=True`, `degree_mode="in_degree"`,
  `extremum="max"`

## Role File Responsibilities

Use these role boundaries consistently in graph scenes.

### `state.py`

Scene-local dataclasses and stable scene constants.

Allowed:

- `SCENE_ID`
- scene sample dataclasses
- rendered-scene dataclasses
- resolved visual/semantic axis dataclasses when they are scene-wide
- stable enum-like support constants that are scene grammar, not public query
  ids

Not allowed:

- public `TASK_ID`
- public `SUPPORTED_QUERY_IDS`
- query-routing maps
- task-specific answer contracts

### `defaults.py`

Scene-level fallback defaults and config loading adapters.

Allowed:

- scene default dataclasses
- default ranges
- small helpers that resolve domain/scene default sections

Not allowed:

- query weights
- task coverage metadata
- public task ids as routing selectors

### `algorithms.py`

Pure scene-local graph algorithms.

Allowed:

- graph computations over finalized scene topology
- path, component, degree, relation, cycle, or tree computations specific to
  the scene representation
- validation of finalized graph properties

Not allowed:

- image rendering
- prompt assembly
- config loading
- public task/query branching
- final answer formatting

Promote algorithms from this file to `trace/tasks/graph/shared/` or
`trace/tasks/shared/graph_algorithms.py` when a second scene needs the same
algorithm with the same abstraction.

### `metrics.py`

Small numeric summaries or answer-range helper metrics when they are
scene-specific.

Allowed:

- degree summaries
- density summaries
- answer-range helper metrics

Do not put full sampling recipes here.

### `sampling.py`

Scene-local graph construction and support resolution.

Allowed:

- deterministic axis support selection
- semantic target support helpers
- scene graph construction recipes
- retry helpers that take neutral semantic arguments

Not allowed:

- public query-id dispatch
- public task-id dispatch
- final answer binding
- final annotation binding

### `rendering.py`

Scene-local rendering orchestration and drawing.

Allowed:

- render a scene sample to image/render dataclasses
- scene-specific visual style application
- text legibility and layout metadata

Not allowed:

- deciding task answers
- deciding annotation witnesses
- prompt text

### `annotations.py`

Projection from symbolic witnesses to public annotation values.

Allowed:

- node center to `point_set` / `point_sequence`
- edge endpoint pairs to `point_pair_set`
- visible label bboxes to `bbox_set`
- keyed maps when witness roles matter
- `AnnotationArtifacts` helpers

Not allowed:

- answer computation unrelated to annotation witness selection
- prompt text
- final `TaskOutput`

### `prompts.py`

Prompt-template assembly helpers only.

Allowed:

- prompt bundle constants
- helper wrapping `render_scene_prompt_variants`
- JSON example construction

Not allowed:

- hardcoded user-facing prompt prose outside prompt assets
- public task/query routing
- answer or annotation computation

### `output.py`

Trace payload fragments and reusable entity/relations builders.

Allowed:

- `scene_ir` fragments without public task identity
- `render_spec` fragments
- `query_spec` body fragments after public task selected prompt artifacts
- entity serialization helpers

Not allowed:

- final `TaskOutput`
- inserting public `task_id` unless the public task passes it directly into a
  fragment assembler that does not branch on it
- selecting query branches

### `option_rendering.py`

Only for scenes with true visual option panels.

Allowed:

- option grid layout
- option panel bboxes
- option panel rendering

## Immediate Target: `graph/node_link`

`node_link` currently has 27 active public tasks:

1. `task_graph__node_link__articulation_point_count`
2. `task_graph__node_link__bridge_count`
3. `task_graph__node_link__common_related_node_count`
4. `task_graph__node_link__component_size_after_edge_edit`
5. `task_graph__node_link__cross_color_edge_count`
6. `task_graph__node_link__degree_after_removal_filter_count`
7. `task_graph__node_link__degree_extremum_value`
8. `task_graph__node_link__degree_value_filter_count`
9. `task_graph__node_link__edge_between_nodes_label`
10. `task_graph__node_link__edge_color_count`
11. `task_graph__node_link__edge_text_count`
12. `task_graph__node_link__hamiltonian_cycle_neighbor_label`
13. `task_graph__node_link__isolated_after_removal_count`
14. `task_graph__node_link__largest_chordless_cycle_size`
15. `task_graph__node_link__largest_component_size`
16. `task_graph__node_link__longest_path_length`
17. `task_graph__node_link__mst_weight`
18. `task_graph__node_link__named_node_degree_value`
19. `task_graph__node_link__node_color_count`
20. `task_graph__node_link__reachable_count`
21. `task_graph__node_link__reachable_count_after_edge_edit`
22. `task_graph__node_link__same_component_count`
23. `task_graph__node_link__shortest_path_first_edge_label`
24. `task_graph__node_link__shortest_path_length`
25. `task_graph__node_link__topological_endpoint_node_label`
26. `task_graph__node_link__unique_cycle_size`
27. `task_graph__node_link__unique_related_node_label`

The current `node_link/shared/lifecycle.py` must be removed. Its contents need
to be redistributed into approved role files and public task files.

### Node-Link Role File Target

Create:

- `trace/tasks/graph/node_link/shared/state.py`
- `trace/tasks/graph/node_link/shared/defaults.py`
- `trace/tasks/graph/node_link/shared/algorithms.py`
- `trace/tasks/graph/node_link/shared/metrics.py`
- `trace/tasks/graph/node_link/shared/sampling.py`
- `trace/tasks/graph/node_link/shared/annotations.py`
- `trace/tasks/graph/node_link/shared/prompts.py`
- `trace/tasks/graph/node_link/shared/output.py`

Optional only if needed:

- `trace/tasks/graph/node_link/shared/styles.py`
- `trace/tasks/graph/node_link/shared/layout.py`
- `trace/tasks/graph/node_link/shared/projection.py`

Do not create:

- `shared/lifecycle.py`
- task-named `*_runtime.py`
- one-file `scene_common.py`
- one-file `task_common.py`
- one-file `instance.py`

### Node-Link Code Placement

Keep graph-domain shared:

- generic graph renderer and render dataclasses
- generic graph label/style/default helpers
- generic graph sample dataclasses
- generic topology helper if used by automaton/flow/metro/pipe scenes

Move or rewrite into `node_link/shared/`:

- node-link objective construction recipes
- node-link target-count feasibility helpers
- node-link-only sampling recipes for bridges, articulation points, common
  neighbors, degree predicates, edge edits, cycle/path/topological objectives,
  color/label count objectives, and MST objective
- node-link annotation projection adapters that map graph sample fields to
  public annotations
- node-link trace entity serialization
- node-link prompt helper wrappers

Promote to graph-domain or cross-domain shared only after confirming at least
two scenes need the exact abstraction:

- bridges and articulation over plain adjacency
- shortest path / exact distance helpers
- connected components
- MST helpers
- topological order

Some of these already exist in `trace/tasks/shared/graph_algorithms.py`; prefer
extending that file for plain adjacency algorithms instead of keeping duplicate
versions inside graph scenes.

### Node-Link Public Task Pattern

Each public file should look like this at a high level:

1. Define `TASK_ID`, `SCENE_ID`, and `SUPPORTED_QUERY_IDS`.
2. Define task-local query-id constants and semantic resolver helpers.
3. Resolve query branch with `select_task_query_id`.
4. Resolve task-specific supports, such as target count, target degree,
   directionality, degree mode, extremum mode, edit operation, target label
   support, or path length.
5. Call neutral `node_link/shared/sampling.py` helpers with semantic arguments.
6. Render with neutral scene rendering helper.
7. Compute answer in the public task file from the returned sample.
8. Select symbolic witnesses in the public task file.
9. Project annotation with `node_link/shared/annotations.py`.
10. Build prompt artifacts with `node_link/shared/prompts.py`.
11. Build trace fragments with `node_link/shared/output.py`.
12. Return `TaskOutput` directly in the public task file.

Public files may share small helper functions by importing from scene shared,
but the branch decision remains in the public file.

### Node-Link Task Families

Refactor node-link in families so each patch remains reviewable.

#### Family A: Basic Count Objectives

Tasks:

- `node_color_count`
- `edge_color_count`
- `edge_text_count`
- `cross_color_edge_count`

Shared primitives needed:

- color/label assignment helpers in `sampling.py`
- edge/node witness projection in `annotations.py`
- edge-label bbox projection in `annotations.py`

Public task ownership:

- choose color/label query semantics
- bind answer to exact count
- choose counted nodes/edges as annotation witnesses

#### Family B: Degree Objectives

Tasks:

- `degree_value_filter_count`
- `degree_after_removal_filter_count`
- `degree_extremum_value`
- `named_node_degree_value`

Shared primitives needed:

- degree map algorithms in `algorithms.py` or `metrics.py`
- graph construction for degree-constrained samples in `sampling.py`

Public task ownership:

- choose directed/undirected
- choose degree mode
- choose extremum or predicate
- bind answer and node/edge annotation witnesses

#### Family C: Connectivity and Component Objectives

Tasks:

- `same_component_count`
- `largest_component_size`
- `component_size_after_edge_edit`
- `reachable_count`
- `reachable_count_after_edge_edit`
- `isolated_after_removal_count`

Shared primitives needed:

- connected components and reachability algorithms
- edge-edit graph construction
- post-removal isolation helpers

Public task ownership:

- choose edit operation when present
- define whether source/query node is included
- bind answer and annotation from finalized graph

#### Family D: Path, Cycle, and Order Objectives

Tasks:

- `shortest_path_length`
- `shortest_path_first_edge_label`
- `longest_path_length`
- `topological_position_value`
- `unique_cycle_size`
- `largest_chordless_cycle_size`
- `hamiltonian_cycle_neighbor_label`

Shared primitives needed:

- unique shortest path
- unique longest path in DAG
- unique topological order
- cycle detection/order helpers
- path/cycle graph construction

Public task ownership:

- choose directed/undirected and path/cycle query semantics
- bind ordered vs unordered annotation correctly
- choose answer label/value

#### Family E: Structural Criticality and MST

Tasks:

- `articulation_point_count`
- `bridge_count`
- `mst_weight`

Shared primitives needed:

- articulation and bridge algorithms
- MST algorithm/weight assignment
- graph construction with exact targets

Public task ownership:

- bind count or weight answer
- choose critical node/edge or MST edge witnesses

#### Family F: Lookup and Relation Labels

Tasks:

- `edge_between_nodes_label`
- `unique_related_node_label`
- `common_related_node_count`

Shared primitives needed:

- neighbor/successor/predecessor relation algorithms
- labeled-edge assignment helpers

Public task ownership:

- choose relation mode
- bind answer label/count
- use query-specific annotation instructions and witnesses

## Later Scene Refactor Order

After `node_link` is review-ready, migrate remaining graph scenes in this order.

### 1. Tighten `adjacency`

Goal: preserve its already-good role layout while removing any remaining
ownership ambiguity.

Actions:

- Keep approved shared files.
- Move any final `TaskOutput` construction from `_lifecycle.py` into public
  task files if the contract tests are tightened.
- Keep `shared/algorithms.py` for BFS/DFS order only if those remain
  adjacency-representation-specific. If a second scene needs them, promote to
  `trace/tasks/shared/graph_algorithms.py`.

### 2. Tighten `automaton`

Goal: keep acceptance-scene shared role files and reduce lifecycle centrality.

Actions:

- Keep `shared/topology.py`, `shared/sampling.py`, `shared/rendering.py`,
  `shared/annotations.py`, `shared/prompts.py`, `shared/labels.py`,
  `shared/state.py`.
- Public acceptance tasks should own final answer and annotation binding.
- Shared acceptance code should accept semantic arguments such as
  `automaton_kind`, not public query ids.

### 3. Migrate `binary_tree`

Goal: replace disallowed shared files with role files.

Proposed files:

- `state.py`: tree node/sample/render dataclasses
- `topology.py`: tree construction primitives
- `algorithms.py`: traversal, LCA, BST path, heap property checks
- `sampling.py`: target-support and tree sampling
- `rendering.py`: tree rendering
- `annotations.py`: bbox/keyed bbox projection
- `prompts.py`: prompt artifact helpers
- `output.py`: trace fragments

Public tasks must own child-structure, depth-level, traversal, local-relative,
LCA, BST operation, and heap-violation answer/annotation binding.

### 4. Migrate `pipe_network`

Goal: remove `shared/instance.py` query routing and split `scene_common.py`.

Proposed files:

- `state.py`
- `topology.py`
- `algorithms.py`
- `sampling.py`
- `rendering.py`
- `annotations.py`
- `prompts.py`
- `output.py`
- `styles.py`

Shared code must accept semantic values such as `blocked_edges`, `source`,
`target`, `distance`, or `target_count`, not `query_id`.

### 5. Migrate `metro`

Goal: remove `MetroRouteInstanceBuilder` query branching.

Proposed files:

- `state.py`
- `topology.py`
- `algorithms.py`
- `sampling.py`
- `rendering.py`
- `annotations.py`
- `prompts.py`
- `output.py`
- `styles.py`

Promote route/shortest-path/min-transfer algorithms only if pipe or other scenes
need the exact abstraction.

### 6. Migrate `flow_network`

Goal: split `shared/instance.py`.

Proposed files:

- `state.py`
- `algorithms.py`: max-flow/min-cut computation if graph-domain-specific
- `sampling.py`: capacity network construction
- `rendering.py`
- `annotations.py`
- `prompts.py`
- `output.py`

If max-flow/min-cut becomes useful outside graph-domain flow diagrams, consider
`trace/tasks/graph/shared/algorithms.py`, not scene-local.

### 7. Migrate `graph_options`

Goal: split `structure_match.py`.

Proposed files:

- `state.py`
- `algorithms.py`: graph isomorphism/subgraph checks over option specs
- `sampling.py`
- `rendering.py`
- `option_rendering.py`
- `annotations.py`
- `prompts.py`
- `output.py`

Option bboxes are valid annotation because these are true visual option-image
tasks.

### 8. Migrate `phylogeny_tree`

Goal: split `scene_common.py` and `task_common.py`.

Proposed files:

- `state.py`
- `topology.py`
- `algorithms.py`: descendants, MRCA, sister taxa, topology signatures
- `sampling.py`
- `rendering.py`
- `annotations.py`
- `prompts.py`
- `output.py`
- `option_rendering.py` for topology-outlier options

### 9. Migrate `pedigree_chart`

Goal: split `scene_common.py` and `task_common.py`.

Proposed files:

- `state.py`
- `topology.py`
- `algorithms.py`: family relationships and relatedness coefficient
- `sampling.py`
- `rendering.py`
- `annotations.py`
- `prompts.py`
- `output.py`
- `option_rendering.py`

## Proposed Minor Contract Clarifications

These are small migration-contract clarifications that would help graph and
other domains.

1. Root `_lifecycle.py` should not build final `TaskOutput`.
   It may prepare neutral render artifacts, but public task files should return
   `TaskOutput` directly.

2. Root `_lifecycle.py` should not accept public `task_id` or `query_id`.
   If it needs identity only for metadata insertion, move that final insertion
   to the public task file or `shared/output.py` fragment builder called by the
   public task without branching.

3. Domain-specific companion docs are allowed.
   Graph needs this plan because graph-domain shared algorithms and renderers
   are genuinely reused across many scenes.

4. Compatibility facades are allowed only outside migrated scene internals.
   The old `graph_sampling.py` facade has been removed; graph scenes must
   import concrete role modules such as `graph_sample_types.py`,
   `label_assets.py`, or a scene-local `shared/sampling.py`. Rendering facades
   such as `graph_scene.py` may remain for shared renderer exports until their
   import surface is split further.

5. Scene-local shared role files must stay role-named, not objective-named.
   For graph this means `algorithms.py` and `sampling.py`, not
   `degree_runtime.py`, `node_count.py`, `scene_common.py`, or `instance.py`.

## Node-Link Migration Checklist

Do not generate review artifacts until all items pass.

1. Inventory current task files and confirm the 27 public task ids remain.
2. Remove or replace `node_link/shared/lifecycle.py`.
3. Create approved scene shared role files.
4. Decide for each current `graph/shared/graph_*_sampling.py` module whether it
   is node-link-only, graph-domain shared, or cross-domain shared.
5. Move node-link-only construction recipes to `node_link/shared/sampling.py`.
6. Move pure node-link algorithms to `node_link/shared/algorithms.py` or
   `node_link/shared/metrics.py`.
7. Keep generic renderer and render dataclasses in `graph/shared/`.
8. Rewrite public task files family by family.
9. For every task/query branch, smoke-generate one instance.
10. Run the scene-scoped migration gate:

```bash
TRACE_SCENE_PACKAGE_REVIEW_SCENE=graph/node_link \
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q \
  tests/test_review_app.py \
  tests/test_run_task_review.py \
  tests/test_scene_package_migration_contracts.py
```

11. Write/update:

```text
review/task-reviews/graph/node_link/manual_code_audit_status.json
review/task-reviews/graph/node_link/migration_test_status.json
```

12. Generate fresh task reviews only under:

```bash
PYTHONPATH=. python scripts/run_task_review.py \
  --tasks <comma-separated node_link task ids> \
  --mode full \
  --out-root review/task-reviews
```

13. Reload the review app index.

## Review-Ready Definition

For graph scenes, "review-ready" means:

- source follows public-task ownership boundaries
- scene shared files use approved role names
- shared code is identity-free
- algorithms are at the narrowest correct reusable layer
- prompts come from prompt assets
- annotation uses `annotation` / `annotation_gt`
- answer and annotation come from the same execution trace
- every query branch smoke-generates
- scene-scoped migration tests pass
- review artifacts are freshly generated under `review/task-reviews`
- review app index is reloaded

Human acceptance in the browser app is still a separate step.
# Graph Scene-Package Migration Plan

This document is the graph-domain companion plan for scene-package migration.
It is intentionally more specific than `SCENE_MIGRATION_GUIDE.md` because graph
has several scenes that share graph algorithms, graph renderers, label assets,
and topology dataclasses.

The immediate migration target is `graph/node_link`. The plan is written so
later scenes can follow the same ownership boundaries instead of repeating the
same mistakes.

## Current Domain Inventory

The graph domain currently has 10 active scenes and 61 active public tasks.

| Scene | Active tasks | Current migration state | Main source-boundary issue |
|---|---:|---|---|
| `adjacency` | 5 | Review-candidate shape, mostly aligned | Scene root `_lifecycle.py` still assembles some final outputs for component-count tasks. Shared role files are otherwise close to target. |
| `automaton` | 4 | Review-candidate shape, partially aligned | Acceptance tasks use `_lifecycle.py`; state-simulation tasks are more task-owned. Shared role files are close to target. |
| `binary_tree` | 7 | Review-candidate shape, migrated to contract | Scene-local role modules own identity-free state, sampling, algorithms, rendering, annotations, prompts, and output fragments; public files own task ids, query ids, and semantic objective plans consumed by a private lifecycle. |
| `flow_network` | 2 | Not migrated to contract | `shared/instance.py` is a scene builder/orchestrator. |
| `graph_options` | 2 | Not migrated to contract | `shared/structure_match.py` is one large mixed sampler/renderer/task helper. |
| `metro` | 4 | Not migrated to contract | `shared/instance.py` branches on `query_id`; `shared/scene_common.py` mixes algorithms, sampling, rendering, and projection. |
| `node_link` | 27 | Registered as review-candidate but not correctly migrated | `shared/lifecycle.py` is invalid: it is a disallowed shared filename and centralizes query/task plumbing, annotation projection, trace payload, and final output construction. |
| `pedigree_chart` | 2 | Not migrated to contract | `shared/scene_common.py` and `shared/task_common.py` are disallowed role names and include task-facing logic. |
| `phylogeny_tree` | 4 | Not migrated to contract | `shared/scene_common.py` and `shared/task_common.py` are disallowed role names; builder classes hide task behavior. |
| `pipe_network` | 4 | Not migrated to contract | `shared/instance.py` branches on `query_id`; `shared/scene_common.py` mixes algorithms, sampling, rendering, and projection. |

Only `adjacency`, `automaton`, and `node_link` are currently in the
review-candidate registry. `node_link` must be repaired before review artifacts
are regenerated.

## Core Ownership Rule

One public task file owns one public objective contract.

Public task files must own:

- literal `TASK_ID`
- `SCENE_ID`
- local `SUPPORTED_QUERY_IDS`
- query selection and query validation
- objective-specific semantic arguments
- objective-specific target/candidate construction when it is not purely
  scene-generic
- answer binding
- `annotation_gt` binding
- dynamic prompt slots and prompt/query key selection
- task-specific trace fields
- final `TaskOutput` construction

Public task files may call shared primitives. They must not hand an objective
plan to a shared runtime that chooses query behavior or builds the final
`TaskOutput`.

## Graph Shared Layers

Graph code should be placed at the narrowest reusable layer that fits.

### Cross-Domain Shared

Use `trace/tasks/shared/graph_algorithms.py` only for representation-agnostic
algorithms over plain adjacency mappings. These helpers should not depend on
graph-domain sample types, render types, prompt labels, or visual semantics.

Good candidates:

- BFS distances and shortest-path counts
- connected components over adjacency maps
- unique shortest-path reconstruction
- unique topological order
- future pure algorithms if reused across domains, such as bridges or
  articulation points over a plain undirected adjacency map

### Graph-Domain Shared

Use `trace/tasks/graph/shared/` for utilities reused by multiple graph scenes.
These helpers may depend on graph-domain concepts such as graph labels,
`GraphTopologySample`, graph render params, graph fonts/styles, or graph-scene
metadata, but must not depend on a specific public task id.

Keep or promote these categories here:

- graph-domain labels and label pools
- graph-domain readable style/defaults/noise/background helpers
- shared node-link-style renderer used by multiple graph scenes
- graph render dataclasses and projection helpers used by node-link,
  automaton, flow-network, metro, pipe-network, or tree-style scenes
- graph-domain prompt JSON example helpers when reused across graph scenes
- graph-domain sample types that represent generic labeled topology

Current graph-domain shared files that are legitimately reused across scenes:

- `label_assets.py`
- `style.py`
- `visual_defaults.py`
- `task_support.py` where helpers are genuinely graph-domain-wide
- `graph_sample_types.py`
- `graph_topology_helpers.py` when used by several scenes
- `graph_scene.py` and `graph_renderer.py`
- `graph_render_context.py`
- `graph_render_edges.py`
- `graph_render_geometry.py`
- `graph_render_layout.py`
- `graph_render_nodes.py`
- `graph_render_panel.py`
- `graph_render_projection.py`
- `graph_render_types.py`

Current graph-domain shared files that appear node-link-specific and should be
re-homed during the `node_link` migration unless another scene has a concrete
need for them:

- `graph_bridge_articulation_sampling.py`
- `graph_common_neighbor_sampling.py`
- `graph_component_sampling.py`
- `graph_degree_sampling.py`
- `graph_edge_path_label_sampling.py`
- `graph_edge_sampling.py`
- `graph_feasibility.py`
- `graph_isolation_sampling.py`
- `graph_label_color_sampling.py`
- `graph_mst_sampling.py`
- `graph_node_degree_sampling.py`
- `graph_path_order_sampling.py`
- `graph_profile_sampling.py`
- `graph_reachability_sampling.py`
- `graph_source_sink_sampling.py`

The old broad `graph_sampling.py` facade has been removed. Graph scenes must
import concrete graph-shared modules or scene-local role modules such as
`graph/node_link/shared/sampling.py`; do not recreate a facade that hides
ownership.

### Scene-Local Shared

Use `trace/tasks/graph/<scene_id>/shared/` for code reused by tasks in exactly
one graph scene.

Allowed graph scene-shared role files are:

- `state.py`
- `sampling.py`
- `algorithms.py`
- `rendering.py`
- `annotations.py`
- `prompts.py`
- `output.py`
- `defaults.py`
- `layout.py`
- `styles.py`
- `labels.py`
- `metrics.py`
- `topology.py`
- `projection.py`
- `option_rendering.py`

Scene shared must not:

- accept or branch on public `task_id`
- accept or branch on public `query_id`
- accept or branch on public objective-contract names
- export public query-id routing tables
- build final `TaskOutput`
- register tasks
- contain task-named runtime files
- hide copied public task bodies

If shared code needs to know which query branch is running, the public task file
must resolve the semantic value first and pass neutral arguments instead.

Example:

- Bad shared argument: `query_id="directed_max_in_degree_value"`
- Good shared arguments: `directed=True`, `degree_mode="in_degree"`,
  `extremum="max"`

## Role File Responsibilities

Use these role boundaries consistently in graph scenes.

### `state.py`

Scene-local dataclasses and stable scene constants.

Allowed:

- `SCENE_ID`
- scene sample dataclasses
- rendered-scene dataclasses
- resolved visual/semantic axis dataclasses when they are scene-wide
- stable enum-like support constants that are scene grammar, not public query
  ids

Not allowed:

- public `TASK_ID`
- public `SUPPORTED_QUERY_IDS`
- query-routing maps
- task-specific answer contracts

### `defaults.py`

Scene-level fallback defaults and config loading adapters.

Allowed:

- scene default dataclasses
- default ranges
- small helpers that resolve domain/scene default sections

Not allowed:

- query weights
- task coverage metadata
- public task ids as routing selectors

### `algorithms.py`

Pure scene-local graph algorithms.

Allowed:

- graph computations over finalized scene topology
- path, component, degree, relation, cycle, or tree computations specific to
  the scene representation
- validation of finalized graph properties

Not allowed:

- image rendering
- prompt assembly
- config loading
- public task/query branching
- final answer formatting

Promote algorithms from this file to `trace/tasks/graph/shared/` or
`trace/tasks/shared/graph_algorithms.py` when a second scene needs the same
algorithm with the same abstraction.

### `metrics.py`

Small numeric summaries or answer-range helper metrics when they are
scene-specific.

Allowed:

- degree summaries
- density summaries
- answer-range helper metrics

Do not put full sampling recipes here.

### `sampling.py`

Scene-local graph construction and support resolution.

Allowed:

- deterministic axis support selection
- semantic target support helpers
- scene graph construction recipes
- retry helpers that take neutral semantic arguments

Not allowed:

- public query-id dispatch
- public task-id dispatch
- final answer binding
- final annotation binding

### `rendering.py`

Scene-local rendering orchestration and drawing.

Allowed:

- render a scene sample to image/render dataclasses
- scene-specific visual style application
- text legibility and layout metadata

Not allowed:

- deciding task answers
- deciding annotation witnesses
- prompt text

### `annotations.py`

Projection from symbolic witnesses to public annotation values.

Allowed:

- node center to `point_set` / `point_sequence`
- edge endpoint pairs to `point_pair_set`
- visible label bboxes to `bbox_set`
- keyed maps when witness roles matter
- `AnnotationArtifacts` helpers

Not allowed:

- answer computation unrelated to annotation witness selection
- prompt text
- final `TaskOutput`

### `prompts.py`

Prompt-template assembly helpers only.

Allowed:

- prompt bundle constants
- helper wrapping `render_scene_prompt_variants`
- JSON example construction

Not allowed:

- hardcoded user-facing prompt prose outside prompt assets
- public task/query routing
- answer or annotation computation

### `output.py`

Trace payload fragments and reusable entity/relations builders.

Allowed:

- `scene_ir` fragments without public task identity
- `render_spec` fragments
- `query_spec` body fragments after public task selected prompt artifacts
- entity serialization helpers

Not allowed:

- final `TaskOutput`
- inserting public `task_id` unless the public task passes it directly into a
  fragment assembler that does not branch on it
- selecting query branches

### `option_rendering.py`

Only for scenes with true visual option panels.

Allowed:

- option grid layout
- option panel bboxes
- option panel rendering

## Immediate Target: `graph/node_link`

`node_link` currently has 27 active public tasks:

1. `task_graph__node_link__articulation_point_count`
2. `task_graph__node_link__bridge_count`
3. `task_graph__node_link__common_related_node_count`
4. `task_graph__node_link__component_size_after_edge_edit`
5. `task_graph__node_link__cross_color_edge_count`
6. `task_graph__node_link__degree_after_removal_filter_count`
7. `task_graph__node_link__degree_extremum_value`
8. `task_graph__node_link__degree_value_filter_count`
9. `task_graph__node_link__edge_between_nodes_label`
10. `task_graph__node_link__edge_color_count`
11. `task_graph__node_link__edge_text_count`
12. `task_graph__node_link__hamiltonian_cycle_neighbor_label`
13. `task_graph__node_link__isolated_after_removal_count`
14. `task_graph__node_link__largest_chordless_cycle_size`
15. `task_graph__node_link__largest_component_size`
16. `task_graph__node_link__longest_path_length`
17. `task_graph__node_link__mst_weight`
18. `task_graph__node_link__named_node_degree_value`
19. `task_graph__node_link__node_color_count`
20. `task_graph__node_link__reachable_count`
21. `task_graph__node_link__reachable_count_after_edge_edit`
22. `task_graph__node_link__same_component_count`
23. `task_graph__node_link__shortest_path_first_edge_label`
24. `task_graph__node_link__shortest_path_length`
25. `task_graph__node_link__topological_endpoint_node_label`
26. `task_graph__node_link__unique_cycle_size`
27. `task_graph__node_link__unique_related_node_label`

The current `node_link/shared/lifecycle.py` must be removed. Its contents need
to be redistributed into approved role files and public task files.

### Node-Link Role File Target

Create:

- `trace/tasks/graph/node_link/shared/state.py`
- `trace/tasks/graph/node_link/shared/defaults.py`
- `trace/tasks/graph/node_link/shared/algorithms.py`
- `trace/tasks/graph/node_link/shared/metrics.py`
- `trace/tasks/graph/node_link/shared/sampling.py`
- `trace/tasks/graph/node_link/shared/annotations.py`
- `trace/tasks/graph/node_link/shared/prompts.py`
- `trace/tasks/graph/node_link/shared/output.py`

Optional only if needed:

- `trace/tasks/graph/node_link/shared/styles.py`
- `trace/tasks/graph/node_link/shared/layout.py`
- `trace/tasks/graph/node_link/shared/projection.py`

Do not create:

- `shared/lifecycle.py`
- task-named `*_runtime.py`
- one-file `scene_common.py`
- one-file `task_common.py`
- one-file `instance.py`

### Node-Link Code Placement

Keep graph-domain shared:

- generic graph renderer and render dataclasses
- generic graph label/style/default helpers
- generic graph sample dataclasses
- generic topology helper if used by automaton/flow/metro/pipe scenes

Move or rewrite into `node_link/shared/`:

- node-link objective construction recipes
- node-link target-count feasibility helpers
- node-link-only sampling recipes for bridges, articulation points, common
  neighbors, degree predicates, edge edits, cycle/path/topological objectives,
  color/label count objectives, and MST objective
- node-link annotation projection adapters that map graph sample fields to
  public annotations
- node-link trace entity serialization
- node-link prompt helper wrappers

Promote to graph-domain or cross-domain shared only after confirming at least
two scenes need the exact abstraction:

- bridges and articulation over plain adjacency
- shortest path / exact distance helpers
- connected components
- MST helpers
- topological order

Some of these already exist in `trace/tasks/shared/graph_algorithms.py`; prefer
extending that file for plain adjacency algorithms instead of keeping duplicate
versions inside graph scenes.

### Node-Link Public Task Pattern

Each public file should look like this at a high level:

1. Define `TASK_ID`, `SCENE_ID`, and `SUPPORTED_QUERY_IDS`.
2. Define task-local query-id constants and semantic resolver helpers.
3. Resolve query branch with `select_task_query_id`.
4. Resolve task-specific supports, such as target count, target degree,
   directionality, degree mode, extremum mode, edit operation, target label
   support, or path length.
5. Call neutral `node_link/shared/sampling.py` helpers with semantic arguments.
6. Render with neutral scene rendering helper.
7. Compute answer in the public task file from the returned sample.
8. Select symbolic witnesses in the public task file.
9. Project annotation with `node_link/shared/annotations.py`.
10. Build prompt artifacts with `node_link/shared/prompts.py`.
11. Build trace fragments with `node_link/shared/output.py`.
12. Return `TaskOutput` directly in the public task file.

Public files may share small helper functions by importing from scene shared,
but the branch decision remains in the public file.

### Node-Link Task Families

Refactor node-link in families so each patch remains reviewable.

#### Family A: Basic Count Objectives

Tasks:

- `node_color_count`
- `edge_color_count`
- `edge_text_count`
- `cross_color_edge_count`

Shared primitives needed:

- color/label assignment helpers in `sampling.py`
- edge/node witness projection in `annotations.py`
- edge-label bbox projection in `annotations.py`

Public task ownership:

- choose color/label query semantics
- bind answer to exact count
- choose counted nodes/edges as annotation witnesses

#### Family B: Degree Objectives

Tasks:

- `degree_value_filter_count`
- `degree_after_removal_filter_count`
- `degree_extremum_value`
- `named_node_degree_value`

Shared primitives needed:

- degree map algorithms in `algorithms.py` or `metrics.py`
- graph construction for degree-constrained samples in `sampling.py`

Public task ownership:

- choose directed/undirected
- choose degree mode
- choose extremum or predicate
- bind answer and node/edge annotation witnesses

#### Family C: Connectivity and Component Objectives

Tasks:

- `same_component_count`
- `largest_component_size`
- `component_size_after_edge_edit`
- `reachable_count`
- `reachable_count_after_edge_edit`
- `isolated_after_removal_count`

Shared primitives needed:

- connected components and reachability algorithms
- edge-edit graph construction
- post-removal isolation helpers

Public task ownership:

- choose edit operation when present
- define whether source/query node is included
- bind answer and annotation from finalized graph

#### Family D: Path, Cycle, and Order Objectives

Tasks:

- `shortest_path_length`
- `shortest_path_first_edge_label`
- `longest_path_length`
- `topological_position_value`
- `unique_cycle_size`
- `largest_chordless_cycle_size`
- `hamiltonian_cycle_neighbor_label`

Shared primitives needed:

- unique shortest path
- unique longest path in DAG
- unique topological order
- cycle detection/order helpers
- path/cycle graph construction

Public task ownership:

- choose directed/undirected and path/cycle query semantics
- bind ordered vs unordered annotation correctly
- choose answer label/value

#### Family E: Structural Criticality and MST

Tasks:

- `articulation_point_count`
- `bridge_count`
- `mst_weight`

Shared primitives needed:

- articulation and bridge algorithms
- MST algorithm/weight assignment
- graph construction with exact targets

Public task ownership:

- bind count or weight answer
- choose critical node/edge or MST edge witnesses

#### Family F: Lookup and Relation Labels

Tasks:

- `edge_between_nodes_label`
- `unique_related_node_label`
- `common_related_node_count`

Shared primitives needed:

- neighbor/successor/predecessor relation algorithms
- labeled-edge assignment helpers

Public task ownership:

- choose relation mode
- bind answer label/count
- use query-specific annotation instructions and witnesses

## Later Scene Refactor Order

After `node_link` is review-ready, migrate remaining graph scenes in this order.

### 1. Tighten `adjacency`

Goal: preserve its already-good role layout while removing any remaining
ownership ambiguity.

Actions:

- Keep approved shared files.
- Move any final `TaskOutput` construction from `_lifecycle.py` into public
  task files if the contract tests are tightened.
- Keep `shared/algorithms.py` for BFS/DFS order only if those remain
  adjacency-representation-specific. If a second scene needs them, promote to
  `trace/tasks/shared/graph_algorithms.py`.

### 2. Tighten `automaton`

Goal: keep acceptance-scene shared role files and reduce lifecycle centrality.

Actions:

- Keep `shared/topology.py`, `shared/sampling.py`, `shared/rendering.py`,
  `shared/annotations.py`, `shared/prompts.py`, `shared/labels.py`,
  `shared/state.py`.
- Public acceptance tasks should own final answer and annotation binding.
- Shared acceptance code should accept semantic arguments such as
  `automaton_kind`, not public query ids.

### 3. Migrate `binary_tree`

Goal: replace disallowed shared files with role files.

Proposed files:

- `state.py`: tree node/sample/render dataclasses
- `topology.py`: tree construction primitives
- `algorithms.py`: traversal, LCA, BST path, heap property checks
- `sampling.py`: target-support and tree sampling
- `rendering.py`: tree rendering
- `annotations.py`: bbox/keyed bbox projection
- `prompts.py`: prompt artifact helpers
- `output.py`: trace fragments

Public tasks must own child-structure, depth-level, traversal, local-relative,
LCA, BST operation, and heap-violation answer/annotation binding.

### 4. Migrate `pipe_network`

Goal: remove `shared/instance.py` query routing and split `scene_common.py`.

Proposed files:

- `state.py`
- `topology.py`
- `algorithms.py`
- `sampling.py`
- `rendering.py`
- `annotations.py`
- `prompts.py`
- `output.py`
- `styles.py`

Shared code must accept semantic values such as `blocked_edges`, `source`,
`target`, `distance`, or `target_count`, not `query_id`.

### 5. Migrate `metro`

Goal: remove `MetroRouteInstanceBuilder` query branching.

Proposed files:

- `state.py`
- `topology.py`
- `algorithms.py`
- `sampling.py`
- `rendering.py`
- `annotations.py`
- `prompts.py`
- `output.py`
- `styles.py`

Promote route/shortest-path/min-transfer algorithms only if pipe or other scenes
need the exact abstraction.

### 6. Migrate `flow_network`

Goal: split `shared/instance.py`.

Proposed files:

- `state.py`
- `algorithms.py`: max-flow/min-cut computation if graph-domain-specific
- `sampling.py`: capacity network construction
- `rendering.py`
- `annotations.py`
- `prompts.py`
- `output.py`

If max-flow/min-cut becomes useful outside graph-domain flow diagrams, consider
`trace/tasks/graph/shared/algorithms.py`, not scene-local.

### 7. Migrate `graph_options`

Goal: split `structure_match.py`.

Proposed files:

- `state.py`
- `algorithms.py`: graph isomorphism/subgraph checks over option specs
- `sampling.py`
- `rendering.py`
- `option_rendering.py`
- `annotations.py`
- `prompts.py`
- `output.py`

Option bboxes are valid annotation because these are true visual option-image
tasks.

### 8. Migrate `phylogeny_tree`

Goal: split `scene_common.py` and `task_common.py`.

Proposed files:

- `state.py`
- `topology.py`
- `algorithms.py`: descendants, MRCA, sister taxa, topology signatures
- `sampling.py`
- `rendering.py`
- `annotations.py`
- `prompts.py`
- `output.py`
- `option_rendering.py` for topology-outlier options

### 9. Migrate `pedigree_chart`

Goal: split `scene_common.py` and `task_common.py`.

Proposed files:

- `state.py`
- `topology.py`
- `algorithms.py`: family relationships and relatedness coefficient
- `sampling.py`
- `rendering.py`
- `annotations.py`
- `prompts.py`
- `output.py`
- `option_rendering.py`

## Proposed Minor Contract Clarifications

These are small migration-contract clarifications that would help graph and
other domains.

1. Root `_lifecycle.py` should not build final `TaskOutput`.
   It may prepare neutral render artifacts, but public task files should return
   `TaskOutput` directly.

2. Root `_lifecycle.py` should not accept public `task_id` or `query_id`.
   If it needs identity only for metadata insertion, move that final insertion
   to the public task file or `shared/output.py` fragment builder called by the
   public task without branching.

3. Domain-specific companion docs are allowed.
   Graph needs this plan because graph-domain shared algorithms and renderers
   are genuinely reused across many scenes.

4. Compatibility facades are allowed only outside migrated scene internals.
   The old `graph_sampling.py` facade has been removed; graph scenes must
   import concrete role modules such as `graph_sample_types.py`,
   `label_assets.py`, or a scene-local `shared/sampling.py`. Rendering facades
   such as `graph_scene.py` may remain for shared renderer exports until their
   import surface is split further.

5. Scene-local shared role files must stay role-named, not objective-named.
   For graph this means `algorithms.py` and `sampling.py`, not
   `degree_runtime.py`, `node_count.py`, `scene_common.py`, or `instance.py`.

## Node-Link Migration Checklist

Do not generate review artifacts until all items pass.

1. Inventory current task files and confirm the 27 public task ids remain.
2. Remove or replace `node_link/shared/lifecycle.py`.
3. Create approved scene shared role files.
4. Decide for each current `graph/shared/graph_*_sampling.py` module whether it
   is node-link-only, graph-domain shared, or cross-domain shared.
5. Move node-link-only construction recipes to `node_link/shared/sampling.py`.
6. Move pure node-link algorithms to `node_link/shared/algorithms.py` or
   `node_link/shared/metrics.py`.
7. Keep generic renderer and render dataclasses in `graph/shared/`.
8. Rewrite public task files family by family.
9. For every task/query branch, smoke-generate one instance.
10. Run the scene-scoped migration gate:

```bash
TRACE_SCENE_PACKAGE_REVIEW_SCENE=graph/node_link \
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q \
  tests/test_review_app.py \
  tests/test_run_task_review.py \
  tests/test_scene_package_migration_contracts.py
```

11. Write/update:

```text
review/task-reviews/graph/node_link/manual_code_audit_status.json
review/task-reviews/graph/node_link/migration_test_status.json
```

12. Generate fresh task reviews only under:

```bash
PYTHONPATH=. python scripts/run_task_review.py \
  --tasks <comma-separated node_link task ids> \
  --mode full \
  --out-root review/task-reviews
```

13. Reload the review app index.

## Review-Ready Definition

For graph scenes, "review-ready" means:

- source follows public-task ownership boundaries
- scene shared files use approved role names
- shared code is identity-free
- algorithms are at the narrowest correct reusable layer
- prompts come from prompt assets
- annotation uses `annotation` / `annotation_gt`
- answer and annotation come from the same execution trace
- every query branch smoke-generates
- scene-scoped migration tests pass
- review artifacts are freshly generated under `review/task-reviews`
- review app index is reloaded

Human acceptance in the browser app is still a separate step.

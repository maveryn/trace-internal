# Graph Scene Refactor Guidelines

This is the graph-domain companion to
`SCENE_REFACTOR_GUIDELINES.md`. It applies while migrating scenes under:

```text
trace/tasks/graph/<scene_id>/
configs/domains/graph/<scene_id>.yaml
review/task-reviews/graph/<scene_id>/
```

Use it with:

```text
docs/workflows/SCENE_PACKAGE_MIGRATION/README.md
docs/workflows/SCENE_PACKAGE_MIGRATION/graph.md
```

The graph domain differs from games: most scenes do not have game mechanics or
turn simulation. The reusable core is graph state, pure graph algorithms,
neutral topology/data sampling, rendering, annotation projection, and prompt
assembly. Public task files still own the objective program.

## Graph Scene Package Shape

Most graph scenes should use this structure:

```text
trace/tasks/graph/<scene_id>/
  <objective_contract>.py
  ...
  shared/
    defaults.py
    state.py
    algorithms.py
    sampling.py
    rendering.py
    annotations.py
    prompts.py
    output.py
```

Only create files that are useful for the scene. Small scenes can omit
`output.py` or combine tiny prompt/default helpers if the role boundary remains
obvious. Do not create placeholder modules.

## File Responsibilities

### `defaults.py`

Scene-local code fallbacks only. YAML remains source of truth.

Allowed:

- fallback answer supports;
- fallback node/edge/count ranges;
- fallback canvas sizes and style ids.

Not allowed:

- task-group routing;
- hidden copies of scene config;
- user-facing prompt text, static prompt slots, examples, or required slot
  declarations;
- objective dispatch;
- broad `_TaskDefaults` dataclasses that mix every sibling objective.

### `state.py`

Scene state, typed contracts, stable ids, and validation.

Allowed:

- graph, tree, matrix, route, pedigree, or automaton dataclasses;
- node ids, edge ids, matrix cell ids, route ids, option ids, person ids,
  taxon ids, and entity-id helpers;
- query-neutral sample dataclasses;
- render map dataclasses;
- invariant checks that do not choose task answers.

Not allowed:

- final answer binding;
- final annotation witness selection;
- prompt assembly;
- rendering side effects;
- `TaskOutput` construction.

### `algorithms.py`

Pure graph and representation algorithms.

Allowed:

- connected components and strongly connected components;
- BFS/DFS traversal;
- shortest path, reachability, exact-distance shells;
- bridges, articulation points, degree maps;
- MST, max flow, min cut;
- DAG longest path and topological order;
- cycle/chordless-cycle/Hamiltonian helpers;
- automaton simulation and epsilon closure;
- tree traversal, LCA, pedigree relatedness, phylogeny MRCA.

Not allowed:

- random sampling;
- renderer calls;
- prompt or annotation payload assembly;
- public task objective selection;
- branching on public `task_id`.

### `sampling.py`

Axis resolution and neutral construction helpers.

Allowed:

- scene/style/label/layout/attribute axis resolution;
- graph topology construction with requested primitive properties;
- candidate graph, option graph, matrix, tree, or route construction;
- distractor construction for visual-option scenes;
- reusable feasibility helpers that return candidates.

Not allowed:

- functions named like `generate_<objective>_output`;
- `sample_for_query(query_id)` when `query_id` spans multiple public
  objectives;
- final answer binding for multiple objectives;
- final annotation witness binding for multiple objectives;
- returning complete `TaskOutput`.

If a sampler needs to enforce an objective-specific target, keep that logic in
the public task file and call neutral helpers from `sampling.py`.

### `rendering.py`

Scene renderer, render params, style variants, and render maps.

Allowed:

- node-link, tree, matrix/list, route, pipe, automaton, pedigree, phylogeny, or
  option-panel renderer;
- render parameter dataclasses;
- style/theme variants;
- text/label placement;
- final layout jitter and projection-safe render maps;
- calls into graph/domain/shared or repo/shared visual helpers.

Not allowed:

- task answer selection;
- prompt assembly;
- verifier payload construction;
- hardcoded annotation coordinates before final layout.

Annotation must project from final render maps after all layout, jitter, font,
and style decisions are applied.

### `annotations.py`

Scene-local annotation projection helpers.

Allowed:

- node center `point_set` and `point_sequence` projection;
- edge endpoint `point_pair_set` projection;
- matrix/list cell `bbox_set` projection;
- row-label or text-label bbox projection;
- visual option-panel bbox projection;
- keyed role maps for source/target/query/reference/path roles.

Not allowed:

- deciding the final answer set for multiple public objectives;
- deciding which query branch is active;
- emitting prompt text;
- returning complete `TaskOutput`.

The public task file chooses the correct witness ids. `annotations.py` only
projects those ids into the requested annotation schema.

### `prompts.py`

Prompt loading and prompt artifact assembly.

Allowed:

- prompt bundle lookup;
- merge prompt-asset static slots with task-provided dynamic slots;
- prompt template key rendering;
- prompt trace metadata.

Not allowed:

- hardcoded user-facing prompt text outside prompt assets;
- static prompt slot defaults or required slot declarations in code;
- objective dispatch that hides task-specific dynamic prompt slot choices;
- `evidence` terminology in new prompt assets or generated payloads.

### `output.py`

Common graph scene output assembly, only if objective-neutral.

Allowed:

- assemble common trace sections after the public task has already bound
  `answer_gt`, `annotation_gt`, witness ids, prompt artifacts, and rendered
  context;
- include scene entities, render map, prompt metadata, background/noise
  metadata, and task versions;
- serialize already-computed algorithm results into trace fields.

Not allowed:

- branching by public task id, objective contract, or top-level query id;
- choosing target nodes/edges/cells/options;
- computing the task answer;
- choosing annotation witnesses;
- replacing public task files with a shared full-output generator.

If `output.py` needs an `if objective == ...` block, move that code back to
the public task file.

## Public Graph Task Files

Each `trace/tasks/graph/<scene_id>/<objective_contract>.py` must:

- define exactly one registered public task class;
- set `domain = "graph"` and `scene_id = "<scene_id>"`;
- set a literal taxonomy-v0 public `task_id`;
- own objective-specific sampling loops and semantic constraints;
- bind final `answer_gt`;
- bind final `annotation_gt`;
- call shared renderer/prompt/output helpers only after the objective is
  already determined;
- record task-specific trace fields;
- expose `query_id` only for narrow operands or parameters inside the same
  answer, annotation, and program contract.

Do not use fixed-query wrappers, merged-query wrappers, `_SourceTask`
subclasses, or shared base classes whose `generate()` owns sibling objectives.

## Scene Archetypes

### Representation Scenes

Examples: `adjacency`.

Shared scene code should center on representation state:

- matrix cells;
- list rows;
- row/column label geometry;
- cell values and weights;
- representation-specific parsing helpers.

Public tasks own the represented graph operation, such as component counting,
reciprocal-pair counting, traversal, or MST.

### Diagram Graph Scenes

Examples: `node_link`, `automaton`, `flow_network`, `metro`, `pipe_network`.

Shared scene code should center on:

- topology state;
- graph algorithms;
- route/edge/node renderers;
- node and edge projection.

Public tasks own the semantic target: which nodes, edges, paths, cuts,
routes, or option labels are the answer.

### Tree And Biological-Notation Scenes

Examples: `binary_tree`, `pedigree_chart`, `phylogeny_tree`.

Shared scene code should center on:

- tree/family/clade structure;
- relation algorithms;
- topology-preserving renderers;
- role-bound keyed annotation projection.

Public tasks own the relation or count objective. Shared code may compute
primitive relations such as LCA, MRCA, sister taxon, parent/child relation, or
relatedness coefficient, but the task file binds the answer and witnesses.

### Visual Option Scenes

Examples: `graph_options`.

Shared scene code should center on:

- option panel layout;
- option graph rendering;
- graph predicate primitives;
- selected option bbox projection.

Public tasks own the option predicate and candidate construction. Option bboxes
are valid annotation because each option is a visual answer candidate.

## Current Graph Scene Targets

### `adjacency`

Target package:

```text
trace/tasks/graph/adjacency/
  directed_pair_reciprocity_count.py
  directed_strong_component_count.py
  mst_weight.py
  traversal_kth_label.py
  undirected_component_count.py
  shared/
    defaults.py
    state.py
    algorithms.py
    sampling.py
    rendering.py
    annotations.py
    prompts.py
    output.py
```

Public task ownership:

- `directed_pair_reciprocity_count.py`: reciprocal-pair predicate, integer
  answer, mirrored-cell annotation.
- `directed_strong_component_count.py`: SCC computation target, integer
  answer, component witness annotation.
- `undirected_component_count.py`: connected-component target, integer answer,
  component witness annotation.
- `mst_weight.py`: unique MST edge selection, weight-sum answer, selected
  matrix-cell annotation.
- `traversal_kth_label.py`: BFS/DFS traversal target, string answer, ordered
  row-label annotation.

### `automaton`

Target package:

```text
trace/tasks/graph/automaton/
  dfa_accepted_string_label.py
  nfa_accepted_string_label.py
  nondeterministic_state_count.py
  state_after_input_label.py
  shared/
    defaults.py
    state.py
    algorithms.py
    sampling.py
    rendering.py
    annotations.py
    prompts.py
    output.py
```

Public task ownership:

- `state_after_input_label.py`: DFA simulation path and final-state answer.
- `dfa_accepted_string_label.py`: candidate string accepted by DFA.
- `nfa_accepted_string_label.py`: candidate string accepted by NFA.
- `nondeterministic_state_count.py`: states with nondeterministic outgoing
  transitions or epsilon transitions.

### `binary_tree`

Target package:

```text
trace/tasks/graph/binary_tree/
  bst_path_operation_label.py
  child_structure_node_count.py
  depth_level_node_count.py
  heap_property_violation_label.py
  local_relative_node_label.py
  lowest_common_ancestor_label.py
  traversal_kth_label.py
  shared/
    defaults.py
    state.py
    algorithms.py
    sampling.py
    rendering.py
    annotations.py
    prompts.py
    output.py
```

Public task ownership:

- count tasks choose the predicate and counted nodes;
- relation tasks choose the queried roles and keyed witnesses;
- traversal task chooses traversal mode and position;
- BST/heap tasks choose the operation/property target and task-specific
  witnesses.

### `flow_network`

Target package:

```text
trace/tasks/graph/flow_network/
  max_flow_value.py
  min_cut_edge_count.py
  shared/
    defaults.py
    state.py
    algorithms.py
    sampling.py
    rendering.py
    annotations.py
    prompts.py
    output.py
```

Public task ownership:

- `max_flow_value.py`: max-flow value answer and selected flow/cut witnesses.
- `min_cut_edge_count.py`: cut-edge count answer and cut-edge witnesses.

### `graph_options`

Target package:

```text
trace/tasks/graph/graph_options/
  contained_subgraph_label.py
  same_structure_label.py
  shared/
    defaults.py
    state.py
    algorithms.py
    sampling.py
    rendering.py
    annotations.py
    prompts.py
    output.py
```

Public task ownership:

- `same_structure_label.py`: isomorphism predicate and selected option.
- `contained_subgraph_label.py`: subgraph containment predicate and selected
  option.

### `metro`

Target package:

```text
trace/tasks/graph/metro/
  exact_distance_station_count.py
  shortest_path_length.py
  station_membership_count.py
  transfer_count.py
  shared/
    defaults.py
    state.py
    algorithms.py
    sampling.py
    rendering.py
    annotations.py
    prompts.py
    output.py
```

Public task ownership:

- each task owns the station/path predicate and final station/path annotation;
- shared code owns route graph construction, shortest-path primitives, transfer
  predicates, and rendering.

### `node_link`

Target package:

```text
trace/tasks/graph/node_link/
  <27 objective_contract>.py
  shared/
    defaults.py
    state.py
    algorithms.py
    sampling.py
    rendering.py
    annotations.py
    prompts.py
    output.py
```

Public task ownership:

- each file owns the exact target construction for its objective;
- shared graph algorithms may compute primitive maps and candidate sets;
- shared samplers may construct graph topologies with requested primitive
  properties, but may not choose one public objective;
- no shared `degree_count.py`, `reachable_count.py`, or edge-attribute module
  should return complete outputs for sibling tasks.

### `pedigree_chart`

Target package:

```text
trace/tasks/graph/pedigree_chart/
  relatedness_coefficient_label.py
  relationship_label.py
  shared/
    defaults.py
    state.py
    algorithms.py
    sampling.py
    rendering.py
    annotations.py
    prompts.py
    output.py
```

Public task ownership:

- relationship task owns relationship label answer and relationship-path
  witnesses;
- relatedness task owns coefficient answer and coefficient/path witnesses.

### `phylogeny_tree`

Target package:

```text
trace/tasks/graph/phylogeny_tree/
  clade_leaf_count.py
  mrca_clade_membership_count.py
  sister_leaf_label.py
  topology_outlier_label.py
  shared/
    defaults.py
    state.py
    algorithms.py
    sampling.py
    rendering.py
    annotations.py
    prompts.py
    output.py
```

Public task ownership:

- clade count owns selected clade and descendant taxa;
- MRCA task owns queried taxa, MRCA clade, and counted taxa;
- sister task owns queried taxon and sister answer;
- topology task owns option predicate and selected option bbox.

### `pipe_network`

Target package:

```text
trace/tasks/graph/pipe_network/
  bridge_count.py
  pipe_exact_distance_count.py
  pipe_reachable_junction_count.py
  shortest_path_length.py
  shared/
    defaults.py
    state.py
    algorithms.py
    sampling.py
    rendering.py
    annotations.py
    prompts.py
    output.py
```

Public task ownership:

- shortest-path task owns source/target path and sequence annotation;
- reachable and exact-distance tasks own target junction sets;
- bridge task owns target pipe edges.

## Graph Anti-Patterns To Remove

Remove or rewrite these patterns during migration:

1. `shared/*` modules that import `TaskOutput` and decide multiple public
   objectives.
2. Public task files that only subclass a source class from `shared/`.
3. `FixedGraphQueryTaskMixin`, `MergedGraphQueryTaskMixin`, or any equivalent
   fixed-query wrapper in migrated graph task files.
4. Public task files whose `task_id` is inherited rather than literal.
5. Shared helpers that accept `task_id`, `objective_contract`, or broad
   `query_id` and return prompt, answer, and annotation together.
6. Scene-local renderer files in `trace/tasks/graph/shared/` unless at least
   two cleaned scenes use them with a scene-neutral API.
7. Broad catch-all files such as `task_support.py` or `graph_sampling.py` if
   they continue to hide scene/objective responsibilities.

## Domain Shared Promotion Candidates

During scene migration, record candidates but do not promote new helpers into
`trace/tasks/graph/shared/` until the final checkpoint.

Likely graph-domain candidates:

- graph label generation and label buckets;
- graph-wide visual defaults and named color themes;
- small graph algorithm wrappers reused by several scenes;
- generic node/edge annotation projection helpers;
- generic graph diagram renderer primitives reused by node-link-like scenes;
- prompt JSON example helpers.

Keep scene-local:

- matrix/list renderers;
- binary-tree renderers and tree-specific algorithms;
- automaton transition rendering and epsilon semantics;
- pedigree and phylogeny notation renderers;
- metro/pipe-specific visual grammar;
- option-panel graph construction when only `graph_options` uses it;
- any helper named with one scene's vocabulary.

## Scene Completion Note

Each completed graph scene section in `graph.md` should include:

```text
Completion note:
- source ownership:
- split/merge decision:
- scene shared helpers:
- domain shared candidates deferred:
- config/prompt/docs updated:
- complexity removed:
- task reviews regenerated/stale folders purged:
- checks:
- final post-migration review:
- blockers:
```

The `domain shared candidates deferred` line is required even when it says
`none`.

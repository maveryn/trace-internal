# Graph Scene-Package Migration Roadmap

This roadmap restarts the `graph` migration under
`docs/workflows/SCENE_PACKAGE_MIGRATION/README.md`.
Use `docs/workflows/SCENE_PACKAGE_MIGRATION/GRAPH_SCENE_REFACTOR_GUIDELINES.md`
for scene-local source layout and graph-specific helper-role boundaries.

The current graph source tree has already been moved toward scene-package
paths, but it must not be treated as migrated. Several scene `shared/` modules
still build complete `TaskOutput` objects for multiple public objectives, and
several public task files are wrappers or fixed-query subclasses over those
shared generators. scene-package migration requires objective ownership in the public task file.

## Status

- Domain: `graph`
- Current active task count: `61`
- Proposed active task count: `61`
- Active scene count: `10`
- Migration state: structurally partial, objective-ownership pending.
- Registry check: currently blocked in this checkout by an unrelated games
  import error (`trace.tasks.games.battleship.shared.scene` missing). Static
  graph source inventory is usable for planning, but implementation must
  restore whole-registry import before graph is marked complete.

## Non-Negotiable Gates

Before `graph` can be marked migrated:

1. Remove `graph` from `MIGRATED_SCENE_PACKAGE_DOMAINS` until every scene below
   passes scene-package gates.
2. Keep graph scenes structurally routed only if runtime needs that, and list
   all graph scenes in `SCENE_PACKAGE_OBJECTIVE_OWNERSHIP_PENDING_SCENES`.
3. Every active graph task id maps to
   `trace/tasks/graph/<scene_id>/<objective_contract>.py`.
4. Every public graph task file defines exactly one registered public task
   class with a literal public `task_id`.
5. No graph public task file is only a wrapper around `_SourceTask`,
   `FixedGraphQueryTaskMixin`, `MergedGraphQueryTaskMixin`, or a shared
   generator.
6. No scene `shared/` module returns complete `TaskOutput` objects for multiple
   public objectives.
7. No scene `shared/` module branches over public task ids or objective
   contracts to choose answers, annotation witnesses, dynamic prompt slots, or
   verifier payloads.
8. No graph-owned active code/config/docs/review artifacts use legacy
   `task_group` routing.
9. New graph prompts/docs/payloads use `annotation`, `annotation_gt`, and
   answer+annotation terminology.
10. Scene configs are keyed as `configs/domains/graph/<scene_id>.yaml`.
11. Retired broad source modules, old config files, old prompt paths, and stale
    review folders are deleted; no compatibility aliases.
12. Domain-shared graph modules contain only cross-scene helpers and no
    scene-local files or objective dispatchers.

## Graph-Specific Shared Boundary

Graph does not need the game-oriented `mechanics.py` concept literally. The
equivalent graph scene package should use only files that fit the scene:

```text
trace/tasks/graph/<scene_id>/
  <objective_contract>.py
  shared/
    defaults.py        # code fallbacks only; prompt slots live in assets/tasks
    state.py           # scene dataclasses, entity ids, validated samples
    algorithms.py      # pure graph/representation algorithms
    sampling.py        # neutral construction and axis resolution
    rendering.py       # scene renderer and render params
    annotations.py     # projection helpers from render map to annotation
    prompts.py         # prompt bundle/artifact assembly
    output.py          # optional objective-neutral TaskOutput assembly
```

Use fewer files for small scenes. Do not create placeholder modules.

Scene shared may own:

- graph dataclasses and validated scene state;
- pure graph algorithms such as BFS/DFS, SCC, MST, LCA, max flow, min cut,
  reachability, component enumeration, cycle enumeration, and tree traversal;
- neutral scene construction primitives;
- graph/diagram renderers, style helpers, layout, text, and projection;
- annotation projection primitives by node id, edge id, matrix cell, row label,
  route station, option panel, or pedigree person.

Public task files must own:

- objective-specific answer support and query-axis selection;
- target/candidate construction for that objective;
- final answer binding;
- final annotation witness selection;
- dynamic prompt slot construction for the objective;
- task-specific trace fields and validation checks.

Domain shared should be a final checkpoint, not the default destination during
the scene loop. Candidate graph-domain shared helpers after scenes are clean:

- graph label pools and label generation;
- graph-wide visual defaults/style wrappers;
- graph diagram rendering primitives genuinely reused by at least two scenes;
- small pure graph algorithm wrappers that are scene-neutral;
- generic graph annotation projection primitives.

Move out of domain shared or delete during migration:

- fixed-query or merged-query wrapper mixins used to preserve old broad tasks;
- large source samplers that choose among public objectives;
- scene-named renderer files that only one scene uses;
- graph complexity helpers and config plumbing owned by this domain;
- broad `task_support.py` style catch-alls once scene-local equivalents exist.

## Current Debt Summary

Static source audit of current graph tree:

- `adjacency`: migrated under scene-package migration; public task files own objective output and
  scene-local shared modules are split by role.
- `automaton`: shared `state_simulation.py` and `string_acceptance.py` build
  complete outputs for several objectives.
- `binary_tree`: shared `node_count.py`, `node_label.py`, and
  `search_tree_operation.py` build complete outputs for sibling objectives.
- `flow_network`: shared `max_flow_value.py` owns both max-flow and min-cut
  public objectives.
- `graph_options`: shared `structure_match_label.py` owns both option-match
  objectives.
- `metro`: shared `task.py` owns complete output generation for multiple
  metro objectives.
- `node_link`: many task files own objective logic already, but shared
  `degree_count.py`, `edge_attribute_label.py`, `reachable_count.py`,
  `node_count_after_degree_filter.py`, and `source_sink_count.py` still hide
  complete objective output generation or wrapper paths.
- `pedigree_chart`: shared `task_common.py` owns output generation for both
  public objectives.
- `phylogeny_tree`: shared `task_common.py` owns output generation for four
  public objectives.
- `pipe_network`: shared `task.py` and `junction_path_count.py` own complete
  output generation for multiple objectives.

These are migration failures even when source paths are already
`trace/tasks/graph/<scene_id>/<objective_contract>.py`.

## One-Pass Execution Model

1. Preflight the domain once.
2. Process scenes in the order in this roadmap.
3. For each scene, finish objective ownership, config/prompt/docs sync,
   stale-review cleanup, and local checks before moving on.
4. After all scenes are clean, do one domain-shared consolidation checkpoint.
5. Run whole-domain validation and only then mark `graph` migrated.

Do not do a path-only migration. Do not create wrapper files as an intermediate
state. If a scene cannot be split without wrappers, merge the public tasks or
keep the scene pending until the objective boundary is redesigned.

## Preflight Fixes Before Scene Loop

1. Demote `graph` from `MIGRATED_SCENE_PACKAGE_DOMAINS`.
2. Add all active graph scenes to
   `SCENE_PACKAGE_OBJECTIVE_OWNERSHIP_PENDING_SCENES["graph"]`.
3. Keep graph scene-package routing only as pending structural routing, not as
   completed migration.
4. Restore whole-registry import if unrelated games import failures block
   validation.
5. Snapshot current active graph inventory from taxonomy/docs if registry is
   temporarily blocked.
6. Remove graph-owned complexity semantics during scene migration; do not add a
   replacement difficulty proxy.
7. Search graph-owned active surfaces for prohibited terms before and after
   each scene:

```bash
rg -n "task_group|evidence|complexity|coverage" trace/tasks/graph configs/domains/graph docs/domains/GRAPH_TASK_SETUP.md docs/tasks/task_graph__*.md
```

8. Do not promote new helpers into `trace/tasks/graph/shared/` during scene
   cleanup unless they are already a small, proven cross-scene primitive.

## Scene Loop

### adjacency

- Status: migrated in scene-package migration.
- Tasks:
  - `task_graph__adjacency__directed_pair_reciprocity_count`
  - `task_graph__adjacency__directed_strong_component_count`
  - `task_graph__adjacency__mst_weight`
  - `task_graph__adjacency__traversal_kth_label`
  - `task_graph__adjacency__undirected_component_count`
- Current risk: none known beyond normal manual audit/solve-rate review.
- Scene contract: rendered adjacency-list, adjacency-matrix, and
  weighted-adjacency-matrix panels with node labels, row/column headers, and
  matrix/list cell geometry in the render map.
- Shared scene helpers:
  - `state.py`: adjacency labels, matrix/list cell ids, row ids, weighted edge
    ids, component/traversal sample dataclasses.
  - `algorithms.py`: SCC, connected components, BFS/DFS traversal order, MST
    over weighted undirected matrix.
  - `sampling.py`: neutral adjacency matrix/list construction helpers and
    label/style axis resolution.
  - `rendering.py`: adjacency list/matrix/weighted matrix renderer.
  - `annotations.py`: bbox projection for matrix cells and row labels.
  - `prompts.py`: adjacency prompt artifact assembly.
  - `output.py`: omitted; current task files assemble trace payloads directly.
- Task ownership:
  - `directed_pair_reciprocity_count.py`: integer answer; `bbox_set`
    annotation over mirrored off-diagonal cells; program
    `count(unordered_node_pairs where reciprocal_state in {one_way, mutual})`.
  - `directed_strong_component_count.py`: integer answer; representative
    `bbox_set` or scene-approved component witnesses; program
    `count(strongly_connected_components(directed_adjacency))`.
  - `undirected_component_count.py`: integer answer; representative
    `bbox_set`; program `count(connected_components(undirected_adjacency))`.
  - `mst_weight.py`: integer answer; `bbox_set` over selected weighted matrix
    cells; program `sum(weights(edge) for edge in unique_mst(weighted_graph))`.
  - `traversal_kth_label.py`: string answer; `bbox_sequence` over visited row
    labels; program `label_at(traversal(adjacency_list, source, mode), k)`.
- Split/merge decision: keep all five separate. Component count tasks differ
  by directedness/SCC algorithm but share neutral helpers; MST and traversal
  have different answer and annotation contracts.
- Tests/checks: recompute SCC/components/MST/traversal from trace payload;
  smoke-generate all query ids.

### automaton

- Tasks:
  - `task_graph__automaton__dfa_accepted_string_label`
  - `task_graph__automaton__nfa_accepted_string_label`
  - `task_graph__automaton__nondeterministic_state_count`
  - `task_graph__automaton__state_after_input_label`
- Current risk: shared full-output generators in `state_simulation.py` and
  `string_acceptance.py`.
- Scene contract: finite automaton state-transition diagram with start arrow,
  accepting-state rings, transition labels, optional epsilon labels, and
  candidate string panels.
- Shared scene helpers:
  - `state.py`: automaton dataclasses, state ids, transition ids, string option
    ids, renderable automaton sample.
  - `algorithms.py`: DFA simulation, NFA epsilon closure, NFA acceptance,
    nondeterministic-state predicate.
  - `sampling.py`: neutral DFA/NFA graph construction, candidate string
    construction, label/transition support.
  - `rendering.py`: automaton renderer and candidate string panel renderer.
  - `annotations.py`: state point sequences and transition/option bboxes.
  - `prompts.py`: automaton prompt artifacts.
- Task ownership:
  - `state_after_input_label.py`: string answer; `point_sequence` annotation;
    program `final_state(simulate_dfa(start, input_string))`.
  - `dfa_accepted_string_label.py`: string option answer; annotation over
    visited state path and/or selected string option; program
    `select(candidate_string where simulate_dfa accepts)`.
  - `nfa_accepted_string_label.py`: string option answer; annotation over NFA
    accepting path/selected string option; program
    `select(candidate_string where nfa_accepts)`.
  - `nondeterministic_state_count.py`: integer answer; `point_set` annotation;
    program `count(states with duplicate outgoing symbol or epsilon edge)`.
- Split/merge decision: keep separate. DFA acceptance, NFA acceptance,
  deterministic state simulation, and nondeterminism counting are different
  program contracts.

### binary_tree

- Tasks:
  - `task_graph__binary_tree__bst_path_operation_label`
  - `task_graph__binary_tree__child_structure_node_count`
  - `task_graph__binary_tree__depth_level_node_count`
  - `task_graph__binary_tree__heap_property_violation_label`
  - `task_graph__binary_tree__local_relative_node_label`
  - `task_graph__binary_tree__lowest_common_ancestor_label`
  - `task_graph__binary_tree__traversal_kth_label`
- Current risk: shared full-output generators in `node_count.py`,
  `node_label.py`, and `search_tree_operation.py`.
- Scene contract: ordered binary tree diagram; parent/child/left/right
  relations come from rendered tree structure and labels.
- Shared scene helpers:
  - `state.py`: tree node dataclasses, ids, labels, parent/child maps.
  - `algorithms.py`: traversal orders, LCA, local relation lookup, BST search
    path, heap violation predicate, depth/child-structure predicates.
  - `sampling.py`: neutral tree construction, BST/heap-valid or invalid tree
    construction, label/style axes.
  - `rendering.py`: binary tree renderer.
  - `annotations.py`: node bbox/point projection and keyed role maps.
  - `prompts.py`: binary tree prompt artifacts.
- Task ownership:
  - `child_structure_node_count.py`: integer answer; `bbox_set`; program
    `count(nodes where child_count/leaf/internal predicate matches)`.
  - `depth_level_node_count.py`: integer answer; `bbox_set`; program
    `count(nodes at queried depth/level)`.
  - `local_relative_node_label.py`: string answer; `keyed_bbox_map`; program
    `label(relation(node, role in {parent,left_child,right_child,sibling}))`.
  - `lowest_common_ancestor_label.py`: string answer; `keyed_bbox_map`;
    program `label(lca(node_a,node_b))`.
  - `traversal_kth_label.py`: string answer; `bbox_sequence`; program
    `label_at(tree_traversal(mode), k)`.
  - `bst_path_operation_label.py`: string option answer; `bbox_sequence` or
    keyed path annotation; program `select(operation/path outcome for BST
    search/insert/delete scenario)`.
  - `heap_property_violation_label.py`: string answer; `keyed_bbox_map`;
    program `find(parent_child_edge violating heap property)`.
- Split/merge decision: keep separate. Child-structure and depth counts share
  scene/annotation schema but have different operand roles and predicates; do
  not merge unless implementation shows identical objective code beyond the
  predicate parameter.

### flow_network

- Tasks:
  - `task_graph__flow_network__max_flow_value`
  - `task_graph__flow_network__min_cut_edge_count`
- Current risk: shared `max_flow_value.py` owns both objectives.
- Scene contract: directed capacity network with source/sink roles and visible
  edge capacities.
- Shared scene helpers:
  - `state.py`: capacity graph, source/sink ids, edge ids, flow/cut result
    dataclasses.
  - `algorithms.py`: max-flow computation, min-cut extraction.
  - `sampling.py`: capacity graph construction with target flow/cut supports.
  - `rendering.py`: capacity network renderer.
  - `annotations.py`: edge point-pair or label-bbox projection.
  - `prompts.py`: flow-network prompt artifacts.
- Task ownership:
  - `max_flow_value.py`: integer answer; annotation for saturated/cut witness
    edges as defined by final contract; program `value(max_flow(G,s,t))`.
  - `min_cut_edge_count.py`: integer answer; edge annotation; program
    `count(edges crossing one minimum s-t cut)`.
- Split/merge decision: keep separate because answer operation and annotation
  witness semantics differ.

### graph_options

- Tasks:
  - `task_graph__graph_options__contained_subgraph_label`
  - `task_graph__graph_options__same_structure_label`
- Current risk: shared option-task module owns complete output generation.
- Scene contract: one reference/target graph plus six visual graph-option
  panels. Option panel bbox annotation is valid because options are visual
  answer images.
- Shared scene helpers:
  - `state.py`: option graph dataclasses and option ids.
  - `algorithms.py`: isomorphism and subgraph-isomorphism predicates.
  - `sampling.py`: option set construction and distractor generation.
  - `rendering.py`: multi-option graph renderer.
  - `annotations.py`: selected option bbox projection.
  - `prompts.py`: option prompt artifacts.
- Task ownership:
  - `same_structure_label.py`: string option answer; `bbox_set` selected
    option; program `select(option where isomorphic(option, reference))`.
  - `contained_subgraph_label.py`: string option answer; `bbox_set` selected
    option; program `select(option where target_graph contains option/reference
    according to task view)`.
- Split/merge decision: keep separate. Both are option-label tasks, but the
  graph predicate and candidate construction differ.

### metro

- Tasks:
  - `task_graph__metro__exact_distance_station_count`
  - `task_graph__metro__shortest_path_length`
  - `task_graph__metro__station_membership_count`
  - `task_graph__metro__transfer_count`
- Current risk: shared `task.py` builds complete outputs for multiple
  objectives.
- Scene contract: metro map with colored route lines, station labels, and route
  legend.
- Shared scene helpers:
  - `state.py`: station/route graph, route membership, station ids.
  - `algorithms.py`: shortest paths, distance shells, transfer station
    predicate, route membership predicate.
  - `sampling.py`: neutral metro-network construction and route/station axes.
  - `rendering.py`: metro map renderer.
  - `annotations.py`: station point-set/sequence projection.
  - `prompts.py`: metro prompt artifacts.
- Task ownership:
  - `shortest_path_length.py`: integer answer; `point_sequence` annotation;
    program `length(shortest_path(station_a, station_b))`.
  - `exact_distance_station_count.py`: integer answer; `point_set`;
    program `count(stations at graph_distance k from source)`.
  - `station_membership_count.py`: integer answer; `point_set`; program
    `count(stations satisfying route-membership predicate)`.
  - `transfer_count.py`: integer answer; `point_set`; program
    `count(stations where route_membership_count >= 2)`.
- Split/merge decision: keep separate. `station_membership_count` and
  `transfer_count` are related but should remain separate unless the route
  membership task is explicitly generalized and the public ids are redesigned.

### node_link

- Tasks:
  - `task_graph__node_link__articulation_point_count`
  - `task_graph__node_link__bridge_count`
  - `task_graph__node_link__common_related_node_count`
  - `task_graph__node_link__component_size_after_edge_edit`
  - `task_graph__node_link__cross_color_edge_count`
  - `task_graph__node_link__degree_after_removal_filter_count`
  - `task_graph__node_link__degree_extremum_value`
  - `task_graph__node_link__degree_value_filter_count`
  - `task_graph__node_link__edge_between_nodes_label`
  - `task_graph__node_link__edge_color_count`
  - `task_graph__node_link__edge_text_count`
  - `task_graph__node_link__hamiltonian_cycle_neighbor_label`
  - `task_graph__node_link__isolated_after_removal_count`
  - `task_graph__node_link__largest_chordless_cycle_size`
  - `task_graph__node_link__largest_component_size`
  - `task_graph__node_link__longest_path_length`
  - `task_graph__node_link__mst_weight`
  - `task_graph__node_link__named_node_degree_value`
  - `task_graph__node_link__node_color_count`
  - `task_graph__node_link__reachable_count`
  - `task_graph__node_link__reachable_count_after_edge_edit`
  - `task_graph__node_link__same_component_count`
  - `task_graph__node_link__shortest_path_first_edge_label`
  - `task_graph__node_link__shortest_path_length`
  - `task_graph__node_link__topological_position_value`
  - `task_graph__node_link__unique_cycle_size`
  - `task_graph__node_link__unique_related_node_label`
- Current risk: largest scene; many files already contain objective code, but
  merged/fixed-query shared modules still own output generation for several
  public objectives.
- Scene contract: labeled directed/undirected node-link graph with optional
  semantic node colors, edge colors, edge labels/weights, routed edges,
  context text, and post-layout annotation projection.
- Shared scene helpers:
  - `state.py`: graph sample dataclasses, node/edge ids, directedness,
    attribute schemas.
  - `algorithms.py`: components, degree maps, bridges/articulation, paths,
    cycles, reachability, MST, topological order, Hamiltonian/chordless-cycle
    helpers.
  - `sampling.py`: neutral graph topology/attribute construction helpers and
    visual-axis resolution; objective-specific target sampling remains in task
    files unless reused by at least two tasks with the same primitive.
  - `rendering.py`: node-link renderer and style/layout/routing helpers.
  - `annotations.py`: node point sets/sequences, edge point-pair sets,
    edge-label bboxes, keyed maps.
  - `prompts.py`: node-link prompt artifact assembly.
  - `output.py`: optional common output assembly after task files bind answer
    and annotation.
- Task ownership summary:
  - Degree/count family:
    - `named_node_degree_value.py`: degree value for a named node; integer;
      edge `point_pair_set`; program `degree(node, mode)`.
    - `degree_extremum_value.py`: max/min/second degree value; integer or
      configured label/value answer; `point_set` of extremal nodes; program
      `extreme(degree_map, mode, rank, exclusion)`.
    - `degree_value_filter_count.py`: count nodes satisfying degree/source/sink
      predicate; integer; `point_set`; program
      `count(nodes where degree_mode value matches predicate)`.
    - `degree_after_removal_filter_count.py`: count remaining nodes after
      degree-one removal predicate; integer; `point_set`; program
      `count(nodes after removal/filter transform)`.
  - Component/reachability family:
    - `same_component_count.py`: integer; `point_set`; program
      `size(component_containing(query_node))`.
    - `largest_component_size.py`: integer; `point_set`; program
      `size(unique_largest_component)`.
    - `component_size_after_edge_edit.py`: integer; `point_set`; program
      `size(component_containing(query_node) after edge add/remove)`.
    - `reachable_count.py`: integer; `point_set`; program
      `count(reachable_from(source) including/excluding source as specified)`.
    - `reachable_count_after_edge_edit.py`: integer; `point_set`; program
      `count(reachable_from(source) after directed edge add/remove)`.
  - Path/order/cycle family:
    - `shortest_path_length.py`: integer; `point_sequence`; program
      `length(shortest_path(source,target))`.
    - `shortest_path_first_edge_label.py`: string edge label; edge annotation;
      program `label(first_edge(shortest_path(source,target)))`.
    - `longest_path_length.py`: integer; `point_sequence`; program
      `length(unique_longest_path(DAG))`.
    - `topological_position_value.py`: integer/string as configured; ordered
      annotation; program `position(node, topological_order)`.
    - `unique_cycle_size.py`: integer; `point_set`; program
      `size(unique_cycle)`.
    - `largest_chordless_cycle_size.py`: integer; `point_sequence`; program
      `size(largest_chordless_cycle)`.
    - `hamiltonian_cycle_neighbor_label.py`: string label; `point_sequence`;
      program `neighbor_of(node, direction, Hamiltonian_cycle)`.
  - Edge/attribute family:
    - `edge_between_nodes_label.py`: string label; edge annotation; program
      `attribute(edge(u,v))`.
    - `edge_color_count.py`: integer; `point_pair_set`; program
      `count(edges with queried color)`.
    - `edge_text_count.py`: integer; edge-label `bbox_set` or edge
      `point_pair_set`; program `count(edges with queried text/labeled state)`.
    - `cross_color_edge_count.py`: integer; `point_pair_set`; program
      `count(edges connecting node_color_a and node_color_b)`.
  - Node/structure family:
    - `node_color_count.py`: integer; `point_set`; program
      `count(nodes with queried semantic color)`.
    - `common_related_node_count.py`: integer; `point_set`; program
      `count(common neighbors/successors/predecessors of node pair)`.
    - `unique_related_node_label.py`: string label; keyed/node annotation;
      program `label(unique neighbor/successor/predecessor satisfying role)`.
    - `bridge_count.py`: integer; `point_pair_set`; program
      `count(bridges)`.
    - `articulation_point_count.py`: integer; `point_set`; program
      `count(articulation_points)`.
    - `isolated_after_removal_count.py`: integer; `point_set`; program
      `count(isolated nodes after removing query node)`.
    - `mst_weight.py`: integer; `point_pair_set`; program
      `sum(weights(unique_mst_edges))`.
- Split/merge decision: keep the 27 public tasks for now. During
  implementation, review only two possible merge risks:
  1. edge lookup vs shortest-path-first-edge lookup must remain separate
     because candidate set and program differ;
  2. degree/source/sink counting may stay one public task only if it is truly
     one predicate-count program with the same answer and annotation schema.

### pedigree_chart

- Tasks:
  - `task_graph__pedigree_chart__relatedness_coefficient_label`
  - `task_graph__pedigree_chart__relationship_label`
- Current risk: shared `task_common.py` builds outputs for both objectives.
- Scene contract: pedigree diagram with generation rows, sex-coded symbols,
  spouse connectors, descent connectors, and option labels for answer choices.
- Shared scene helpers:
  - `state.py`: person/family graph dataclasses, relationship ids, option ids.
  - `algorithms.py`: kinship relationship classification and relatedness
    coefficient computation.
  - `sampling.py`: neutral family graph construction and queried-person
    selection.
  - `rendering.py`: pedigree renderer and option panel renderer.
  - `annotations.py`: keyed person bbox maps and selected option bbox helpers.
  - `prompts.py`: pedigree prompt artifacts.
- Task ownership:
  - `relationship_label.py`: string option answer; `keyed_bbox_map` for
    queried people and relationship path witnesses; program
    `classify_relationship(person_a, person_b)`.
  - `relatedness_coefficient_label.py`: string/fraction option answer;
    `keyed_bbox_map`; program `coefficient(relationship_path(person_a,b))`.
- Split/merge decision: keep separate because the answer semantics and program
  are different despite shared pedigree scene construction.

### phylogeny_tree

- Tasks:
  - `task_graph__phylogeny_tree__clade_leaf_count`
  - `task_graph__phylogeny_tree__mrca_clade_membership_count`
  - `task_graph__phylogeny_tree__sister_leaf_label`
  - `task_graph__phylogeny_tree__topology_outlier_label`
- Current risk: shared `task_common.py` builds outputs for four objectives.
- Scene contract: rooted cladogram with terminal taxon labels and unlabeled
  internal branch points; topology is semantic, branch lengths/order are
  non-semantic unless option panels are shown.
- Shared scene helpers:
  - `state.py`: tree dataclasses, taxon ids, internal-node ids, option ids.
  - `algorithms.py`: clade leaves, MRCA, sister taxa/clades, topology
    comparison/outlier.
  - `sampling.py`: neutral cladogram and option-tree construction.
  - `rendering.py`: cladogram and topology-option renderer.
  - `annotations.py`: taxon point sets, keyed taxon bboxes, option bbox sets.
  - `prompts.py`: phylogeny prompt artifacts.
- Task ownership:
  - `clade_leaf_count.py`: integer; `point_set`; program
    `count(descendant_terminal_taxa(clade_root))`.
  - `mrca_clade_membership_count.py`: integer; `keyed_bbox_map` or
    `point_set`; program `count(taxa in clade rooted at mrca(taxon_a,taxon_b))`.
  - `sister_leaf_label.py`: string label; `keyed_bbox_map`; program
    `label(sister_taxon(query_taxon))`.
  - `topology_outlier_label.py`: string option label; selected option bbox;
    program `select(option_tree not topology-equivalent to others/reference)`.
- Split/merge decision: keep separate.

### pipe_network

- Tasks:
  - `task_graph__pipe_network__bridge_count`
  - `task_graph__pipe_network__pipe_exact_distance_count`
  - `task_graph__pipe_network__pipe_reachable_junction_count`
  - `task_graph__pipe_network__shortest_path_length`
- Current risk: shared `task.py` and `junction_path_count.py` build complete
  outputs for several objectives.
- Scene contract: pipe-junction network with labeled junctions, open/blocked
  pipe segments, and grid-like industrial/blueprint visual style.
- Shared scene helpers:
  - `state.py`: junction graph dataclasses, pipe ids, blocked/open edge state.
  - `algorithms.py`: shortest path, reachability, exact-distance shell,
    bridge detection.
  - `sampling.py`: neutral pipe-grid network construction.
  - `rendering.py`: pipe network renderer.
  - `annotations.py`: junction point sets/sequences and pipe point-pair sets.
  - `prompts.py`: pipe-network prompt artifacts.
- Task ownership:
  - `shortest_path_length.py`: integer; `point_sequence`; program
    `length(shortest_open_pipe_path(source,target))`.
  - `pipe_reachable_junction_count.py`: integer; `point_set`; program
    `count(junctions reachable from source through open pipes)`.
  - `pipe_exact_distance_count.py`: integer; `point_set`; program
    `count(junctions at exact open-pipe distance k)`.
  - `bridge_count.py`: integer; `point_pair_set`; program
    `count(open pipes whose removal disconnects network)`.
- Split/merge decision: keep separate.

## Config, Prompt, Docs, And Review Cleanup

For each scene:

1. Keep exactly one scene config:
   `configs/domains/graph/<scene_id>.yaml`.
2. Delete legacy graph config files once no active graph task reads them:
   `counting.yaml`, `comparison.yaml`, `order.yaml`, `optimization.yaml`,
   `path.yaml`, `relation.yaml`.
3. Move prompt assets to scene-owned directories and remove legacy prompt
   paths that encode broad reasoning groups.
4. Update `docs/domains/GRAPH_TASK_SETUP.md` after each scene completion.
5. Update all `docs/tasks/task_graph__*.md` touched by the scene to remove
   legacy routing language and use `annotation`.
6. Delete review folders for retired or renamed task ids.
7. Regenerate changed active task reviews under
   `review/task-reviews/graph/<scene_id>/<task_id>/`.
8. Reload the review app index after review artifacts change.

## Final Domain-Shared Checkpoint

After all scenes pass local scene-package checks:

1. Compare cleaned scene-local helpers.
2. Promote only narrow cross-scene graph utilities into
   `trace/tasks/graph/shared/`.
3. Rename promoted helpers to scene-neutral names; no `node_link_*` filename in
   domain shared unless it is only used by the `node_link` scene, in which case
   it belongs under `node_link/shared/`.
4. Delete wrapper/fixed-query migration helpers.
5. Ensure no domain-shared helper imports `TaskOutput` unless it is a truly
   objective-neutral output assembler used across scenes after answer and
   annotation are already bound. Prefer scene-local `output.py`.
6. Rerun enforcement tests and graph smoke generation.

## Whole-Domain Validation Plan

Run these before marking `graph` complete:

```bash
python -m compileall -q trace/tasks/graph
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_scene_package_migration_contracts.py
PYTHONPATH=. python - <<'PY'
import trace.tasks
from trace.tasks.registry import list_task_ids
ids = sorted(tid for tid in list_task_ids() if tid.startswith("task_graph__"))
print(len(ids))
for tid in ids:
    print(tid)
PY
```

Then run scene smoke generation for each task with a small count and regenerate
task reviews for changed active tasks:

```bash
PYTHONPATH=. python scripts/run_task_review.py --tasks <task_id> --mode full --out-root review/task-reviews
```

Completion requires:

- active graph task count remains `61`, unless a documented split/merge changes
  taxonomy;
- graph scenes remain exactly the ten scenes listed above;
- every graph scene removed from objective-ownership pending;
- `graph` added back to `MIGRATED_SCENE_PACKAGE_DOMAINS`;
- no stale graph task-review folders for retired ids;
- graph docs and task docs synchronized with registry/taxonomy;
- review app index reloaded after task-review regeneration.

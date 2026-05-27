# Graph Coverage Extension

## Scope

This note tracks remaining graph-domain coverage gaps from external benchmark
analysis after the current graph, pages, chart, and shared-label work.

Current working conclusion: the graph domain already has strong synthetic
coverage for pure graph reasoning. Active graph tasks cover degree-style node
counts, named-node degree, semantic node and edge color counts, cross-color
edge counts, common neighbors, connected components, articulation points,
bridges, unique cycles, shortest paths, longest directed paths, reachability
before/after edge edits, topological order, minimum spanning tree, max-flow
capacity networks, pipe junction networks, metro-route networks, visible
edge-label lookup/counting, automaton state-transition simulation and string
acceptance, binary-tree node/traversal/relation reasoning, and basic BST/heap
operation queries.

The remaining graph-owned gaps are narrow. After adding automaton,
max-flow/min-cut, metro-transfer, unique-node-label, and edge-text-label count
coverage, distinct edge-label aggregation is an optional text-label aggregation
extension, not a core topology gap. Signed causal graphs should be deferred
unless we decide they belong in `graph` rather than a future science-style
scene in an existing domain.

Infographic, flowchart, concept-map, hierarchy, schema, and poster-like page
presentation is not a graph-domain capability gap when the verifier source of
truth is page/workflow/section/schema metadata rather than graph topology.

## Benchmark Cues

- ChartMuseum includes network and flowchart examples, including a
  co-lexification network question asking which concept is adjacent to a named
  concept and a flow-chart page-routing example with multiple page outputs.
- InfoVQA and ChartMuseum include graph, network, and process-flow traversal
  inside infographic-style pages.
- EvoChart has a small number of path/flow questions in chart-like graphics.
- MathVista TestMini has occasional food-web or causal-network questions where
  a visible graph is only part of a science/domain-knowledge problem.
- MMMU-ProVis and GameQALite include computer-science graph/automata examples
  such as maximum-flow networks, NFA/DFA-style state diagrams, transition
  simulation, and binary-tree traversal/counting. These should become graph
  tasks only when all rules and answers are visible, synthetic, and
  metadata-grounded.

## Domain Boundary

- Put a task in `graph` when adjacency, direction, connectivity, path, degree,
  edge/node attribute, route membership, or graph topology is the verifier
  source of truth.
- Put it in `pages/process_flow` when the source of truth is workflow state:
  decision nodes, conditional branches, lanes, statuses, document pages, or
  step-by-step procedural routing.
- Put it in `pages/concept_map`, `pages/hierarchy`, or `pages/schema` when the
  source of truth is branch membership, tree/document hierarchy, or schema
  roles/cardinality rather than graph-theory properties.
- Put it in `charts` when the graph-like visual is a data encoding such as a
  Sankey, alluvial flow, chord-style quantitative flow, or chart panel.
- Put it in `science` or another future domain only if the answer requires
  domain-specific causal, biological, or physical knowledge rather than visible
  graph metadata alone.
- Keep list or multi-span answers out of graph for this wave. Convert them to
  scalar counts, unique labels, endpoint labels, or option labels where
  possible.

## Current Graph Surface

Active scene families:

- `node_link_graph`: simple directed or undirected node-link graphs with
  `graph_directionality=directed|undirected`, labels as letters, numbers, or
  `named`, semantic node/edge colors for selected tasks, multiple layouts, and
  straight or mixed-arc edge routing.
- `weighted_node_link_graph`: weighted node-link graphs for minimum spanning
  tree reasoning.
- `capacitated_flow_graph`: directed capacity networks for max-flow and
  minimum-cut reasoning.
- `pipe_junction_graph`: open/blocked pipe networks for shortest route,
  reachability, bridge-pipe, and exact-distance tasks.
- `metro_route_graph`: colored transit-route networks for station-membership,
  shortest-path, transfer-count, and exact-distance tasks.
- `automaton_state_graph`: directed state-transition diagrams with a start
  arrow, accepting-state rings, and visible `0|1` transition labels.
- `binary_tree_diagram`: top-down ordered binary trees where parent/child,
  sibling, LCA, left/right traversal, BST search/insert, and heap-property
  relations are visible by position and numeric keys.

Active task families:

- Counting: merged degree-style node counts, named-node degree, node color,
  edge color, cross-color edge, edge text-label count, node-removal isolation,
  articulation points, bridges, pipe bridges, and metro station membership.
- Relation/path: merged component-size count, unique cycle size, shortest path,
  longest directed path, merged directed reachability, common neighbors,
  visible edge-label lookup, pipe reachability/distance, metro route distance,
  metro transfer count, automaton state simulation, automaton string
  acceptance, binary-tree traversal, binary-tree node-label relations, and
  search-tree operation paths.
- Comparison/order/optimization: extreme degree, topological position, minimum
  spanning tree weight, and max-flow/min-cut.

## Covered Elsewhere

These benchmark motifs should not drive new graph-domain tasks unless the
answer is purely graph-topological.

### Page-Like Infographic Networks

Status: `covered by pages / not a graph gap`

TRACE already has page-style presentation coverage:

- `pages/infographic` for section/card metric infographics,
- `pages/process_flow_diagram` for workflow traversal, status/lane filters, and
  cross-lane handoff counts,
- `pages/concept_map_diagram` for branch membership, ordered child labels, and
  marked child counts,
- `pages/hierarchy_diagram` for tree descendant/leaf/path counts,
- `pages/database_schema_diagram` for schema field roles and relationship-line
  counts.

Do not add generic poster/card/sidebar wrappers to `node_link_graph` just to
look infographic-like. That duplicates pages and weakens the visual-domain
boundary. If an external example is a page, flowchart, org chart, schema,
concept map, or sectioned infographic, it should normally stay in `pages`.

### Flowchart And Process-Flow Traversal

Status: `covered by pages/process_flow`

Conditional workflow traversal belongs in `pages/process_flow`, not graph.
Graph should own only pure adjacency/path/reachability questions without
workflow conditions, statuses, lanes, or page semantics.

### Hierarchies, Org Charts, Concept Maps, And Schemas

Status: `covered by pages unless purely abstract topology`

Use `pages` when the visual is an org chart, outline, concept map, document
hierarchy, or database schema. Use `graph` only when the scene is an abstract
graph/tree and the task asks graph metadata such as degree, path length,
component size, leaf count, or ancestor/descendant under explicitly synthetic
topology.

## Genuine Remaining Graph Gaps

### G1. Unique Node-Label Relation

Status: `implemented / accepted`

Some benchmark network questions ask for a visible node label rather than a
numeric graph property, for example "which concept is connected to BLOOD?"
TRACE graph tasks use visible node labels as prompt identities, but current
graph answers are still mostly integers.

Implemented coverage:

- `proposal:graph/relation/unique_node_label` asks for the unique neighbor,
  successor, or predecessor label under
  `query_id=unique_neighbor_label|unique_successor_label|unique_predecessor_label`.
- The task enforces one valid answer and uses one answer-node bbox as evidence.

Calibration note: qwen25vl7b `100x24` seed `20260523` is accepted after
branch-specific tuning. The current solve-rate workbook reports mean solve
`0.378`, hard `0.160`, easy `0.190`, and band `0.650`; the calibration parquet
distribution passed with `68` unique answers and max answer frequency `6/100`.

### G2. Edge-Label Counting And Typed-Edge Attributes

Status: `partial; edge text-label count accepted`

Implemented coverage:

- `proposal:graph/relation/edge_attribute_label` asks for the visible text on a
  queried undirected edge, directed edge, or first edge of a unique shortest
  path. Edge-label bboxes are trace-visible.
- Edge text labels now sample from repo-wide shared label manifests rather than
  a tiny fixed verb list.
- `proposal:graph/counting/edge_text_label_count` counts visible edge-label boxes
  whose text exactly matches a queried label. Evidence is the bbox set around
  every matching label box. Qwen25vl7b `100x24` seed `20260523` is accepted
  with mean solve `0.390`, hard `0.010`, easy `0.150`, and band `0.840`.

Remaining optional graph-owned gap: distinct-label aggregation. This is lower
priority than route-transfer reasoning because it mostly tests visible
edge-label reading plus set aggregation, while exact edge-label counting is
already accepted.

Candidate tasks:

- `proposal:graph/counting/unique_edge_label_count`: count distinct visible edge
  labels used in the graph.
- `proposal:graph/counting/labeled_edge_count`: count edges with a specified
  edge-type marker or text class.

Evidence should be edge-label bboxes for text-label tasks or edge point-pairs
for typed-edge tasks. Avoid adding an edge-color lookup task for now; it would
mostly duplicate existing edge-color counting plus the edge-attribute lookup
task, which already proved too easy.

### G3. Metro Route Transfer Semantics

Status: `implemented / accepted`

Current metro tasks cover pure route topology: transfer-station count,
single-route station count, shortest-path length, exact-distance count, and
minimum colored-route changes for a required-stop trip.

Implemented coverage:

- `proposal:graph/path/metro_transfer_count`: given source, via, and goal station
  labels, answer the fewest colored-route changes needed to travel from source
  to goal while stopping at the via station. Evidence is the selected
  minimum-transfer station `point_sequence`; trace records the route sequence
  and route-change station labels.

Keep route-line membership visible and avoid fare, zone, timetable, or
real-world map semantics. The calibrated task uses answer support `0..4`
because narrower transfer-change ranges fail the standard 5-unique-answer
distribution gate. Qwen25vl7b `100x24` seed `20260523` is accepted with mean
solve `0.252`, hard `0.260`, easy `0.010`, and cap `0.000`.

### G4. Explicit Signed Causal Graphs

Status: `boundary-sensitive gap`

MathVista-style food-web and causal-network examples often require biology or
causal interpretation beyond visible graph traversal. That should not be a
graph task unless all causal rules are synthetic and explicitly visible.

Graph-owned version:

- use a signed directed graph scene where every edge visibly carries `+/-` or
  increase/decrease markers,
- encode the propagation rule in the task contract and trace metadata,
- ask only scalar or unique-label questions.

Candidate tasks:

- `proposal:graph/relation/signed_path_effect_label`
- `proposal:graph/counting/positive_influence_count`
- `proposal:graph/relation/causal_successor_count`
- `proposal:graph/relation/effect_after_node_change_label`

This should wait until we decide whether signed causal diagrams belong in
`graph` or a future science/causal domain. Do not add this as the next graph
task under the current visual-domain boundary.

### G5. Dense Graph Readability

Status: `ongoing review constraint, not a task gap`

External network diagrams can have dense labels, curved edges, clustered
groups, legends, colored communities, and annotations. TRACE has multiple
node-link layouts, named labels, mixed-arc routing, visual noise, and graph
style variation. The remaining issue is calibration/review discipline:

- do not increase density just to mimic benchmark clutter,
- keep labels, arrowheads, edge-label bboxes, and evidence geometry readable,
- add visual variation only when review confirms it does not create ambiguous
  graph structure.

### G6. Graph-Theory Or Automata Benchmark Family

Status: `automaton state simulation implemented / accepted; automaton string acceptance review implemented; max-flow implemented / accepted; binary-tree review implemented`

External benchmark gap 4 can be served by one graph-domain task family without
renaming `physics` to `science` or adding broad engineering/chemistry coverage.
Keep the task graph-owned only when adjacency, capacities, terminals, state
transitions, and acceptance rules are fully visible and synthetic.

Implemented coverage:

- `proposal:graph/relation/automaton_state_simulation_label` uses a DFA-style
  state-transition diagram plus a short binary input string. It asks either for
  the final state or the state after the first `k` symbols. Evidence is the
  ordered state-center `point_sequence`. Qwen25vl7b `100x24` seed `20260523`
  is accepted with mean solve `0.237`, hard `0.010`, easy `0.000`, and band
  `0.990`.
- `proposal:graph/relation/automaton_string_acceptance_label` uses the same
  automaton scene plus six candidate input strings. It asks which option is
  accepted by a DFA or NFA. Evidence is one accepting state-center
  `point_sequence`. Review/distribution artifacts are generated under
  `plans/task-reviews/graph/automaton_state_graph/`; qwen25 solve-rate
  calibration is pending.
- `proposal:graph/optimization/max_flow_value` uses a directed capacity network
  with source `S`, sink `T`, and visible integer capacities. It asks for
  max-flow value or unique minimum-cut edge count. Evidence is the relevant
  unique minimum-cut directed edge `point_pair_set`. Qwen25vl7b `100x24` seed
  `20260523` is accepted with mean solve `0.192`, hard `0.130`, easy `0.000`,
  and band `0.870`.
- `proposal:graph/counting/binary_tree_node_count` uses a labeled ordered binary
  tree and asks for leaf, internal, single-child, two-child, or depth-level
  node counts. Evidence is the counted node `bbox_set`. Review/distribution
  artifacts are generated under
  `plans/task-reviews/graph/binary_tree_diagram/`; qwen25 solve-rate
  calibration is pending.
- `proposal:graph/order/binary_tree_traversal_label` asks for the label at a
  requested position in preorder, inorder, postorder, or level-order traversal.
  Evidence is the ordered visited-prefix `bbox_sequence`. Review/distribution
  artifacts are generated under
  `plans/task-reviews/graph/binary_tree_diagram/`; qwen25 solve-rate
  calibration is pending.
- `proposal:graph/relation/binary_tree_node_label` asks for parent, left-child,
  right-child, sibling, or lowest-common-ancestor labels. Evidence is a
  `bbox_set` around the queried node or nodes and the answer node. Review
  artifacts are generated under
  `plans/task-reviews/graph/binary_tree_diagram/`; qwen25 solve-rate
  calibration is pending.
- `proposal:graph/relation/search_tree_operation_label` asks for the terminal node
  of a BST search, the parent for a BST insertion, or the child violating a
  min-heap property. Evidence is an ordered `bbox_sequence` over the operation
  path or checked parent-child pair. Review artifacts are generated under
  `plans/task-reviews/graph/binary_tree_diagram/`; qwen25 solve-rate
  calibration is pending.
- `proposal:graph/order/adjacency_traversal_label` uses a directed adjacency-list
  panel and asks for the label at a requested BFS or DFS visit position.
  Evidence is the ordered row-label `bbox_sequence` from the source row through
  the answer row. Review artifacts are generated under
  `plans/task-reviews/graph/adjacency_representation_graph/`; qwen25
  solve-rate calibration is pending; distribution review passes.
- `proposal:graph/counting/adjacency_component_count` uses an adjacency-list or
  adjacency-matrix panel and asks for connected-component or strongly connected
  component count. Evidence is one representative row/header label `bbox_set`
  per counted component. Review artifacts are generated under
  `plans/task-reviews/graph/adjacency_representation_graph/`; qwen25
  solve-rate calibration is pending; distribution review passes with component
  count support `2..6`.
- `proposal:graph/optimization/adjacency_matrix_mst_weight` uses a weighted
  adjacency-matrix panel and asks for the total weight of the unique minimum
  spanning tree. Evidence is a `bbox_set` over one selected matrix cell per MST
  edge. Review artifacts are generated under
  `plans/task-reviews/graph/adjacency_representation_graph/`; qwen25
  solve-rate calibration is pending; distribution review passes.

No additional graph-theory/automata/tree/adjacency-representation task is
currently needed. A terminal-label reachability task would be too close to
existing reachability plus unique-node label tasks after automaton coverage.

## Suggested Next Graph Work

1. Spend the next graph pass calibrating or pruning existing
   non-accepted node-link rows before adding more node-link variants.
2. Defer signed causal graphs until the domain boundary with future science
   tasks is decided.

## Remaining Open Questions

1. Are signed causal/food-web diagrams graph tasks, or should they wait for a
   science-style scene in an existing domain?

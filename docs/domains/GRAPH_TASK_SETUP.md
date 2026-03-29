# Graph Task Setup

## Purpose
Define the concrete v1 setup for the current graph-domain task families.

## V1 scope
1. `domain = graph`
2. Active `task_group`s:
   - `counting`
   - `comparison`
   - `order`
   - `optimization`
   - `path`
   - `relation`
3. Current concrete tasks:
   - `task_graph_counting_degree_count`
   - `task_graph_counting_articulation_point_count`
   - `task_graph_counting_bridge_count`
   - `task_graph_comparison_largest_component_size`
   - `task_graph_order_topological_position`
   - `task_graph_optimization_minimum_spanning_tree_weight`
   - `task_graph_path_shortest_path_length`
   - `task_graph_relation_reachable_count`
   - `task_graph_relation_same_component_count`
   - `task_graph_relation_unique_cycle_size`

## Scene contract
1. Use one simple node-link graph per image; keep graphs unweighted by default, and introduce weights only when they are semantically essential to the task.
2. Keep node labels visible and canonical; v1 uses labels from `A..J`.
3. Node count support is `5..10` for undirected graph tasks in v1, `5..9` for directed graph variants, and `5..8` for the current weighted MST task so edge labels stay readable.
4. No self-loops or multi-edges.
5. Directed variants also reject reciprocal edge pairs by default so arrowheads remain readable.
6. Layout is visual variation only; the task semantics come from adjacency.
7. V1 graph scenes may vary whole-image node label format (`letters|numbers`), node glyph style (`circle|rounded_square|hexagon`), named node color, and global layout transform, but those axes stay non-semantic unless a future task explicitly queries them.

## Current task contracts
1. `task_graph_counting_degree_count`
   - ask one of:
     - `How many nodes have degree k?`
     - `How many nodes have in-degree k?`
     - `How many nodes have out-degree k?`
   - answer type: `integer`
   - evidence type: `label_set`
   - default `query_degree` support: `0..4`
   - default answer support: `0..5`
   - default style supports:
     - label variant: `letters|numbers`
     - node shape: `circle|rounded_square|hexagon`
     - named node color: shared TRACE palette
     - layout transform: `identity|rotate_90|rotate_180|rotate_270|mirror_left_right|mirror_up_down`
2. `task_graph_relation_same_component_count`
   - ask:
     - `How many nodes, including node X itself, are in the same connected component as X?`
   - answer type: `integer`
   - evidence type: `label_set`
   - default connected-component count support: `2..4`
   - default queried component-size support: `1..6`
   - prompt/evidence contract: the queried node itself is included in both the count and the evidence label set
3. `task_graph_counting_articulation_point_count`
   - ask:
     - `How many nodes are articulation points?`
   - answer type: `integer`
   - evidence type: `label_set`
   - default articulation-point-count support: `0..8`
   - prompt/evidence contract: evidence contains every articulation-point node in the graph
4. `task_graph_relation_unique_cycle_size`
   - ask:
     - `The graph contains exactly one cycle. How many nodes are in that cycle?`
   - answer type: `integer`
   - evidence type: `label_set`
   - default cycle-size support: `3..7`
   - prompt/evidence contract: the graph is connected and unicyclic, evidence contains every node in the unique cycle, and generation leaves at least one node outside the cycle
5. `task_graph_counting_bridge_count`
   - ask:
     - `How many edges are bridges?`
   - answer type: `integer`
   - evidence type: `edge_set`
   - default bridge-count support: `0..8`
   - prompt/evidence contract: evidence contains every bridge edge as one two-label endpoint pair, and each endpoint pair is unordered semantically even though the implementation canonicalizes it internally for determinism
6. `task_graph_comparison_largest_component_size`
   - ask:
     - `How many nodes are in the largest connected component?`
   - answer type: `integer`
   - evidence type: `label_set`
   - default connected-component count support: `2..4`
   - default unique-largest-component-size support: `2..6`
   - prompt/evidence contract: evidence contains every node in the unique largest connected component, and generation rejects ties for largest component size
7. `task_graph_path_shortest_path_length`
   - ask:
     - `The graph has a unique shortest path from node X to node Y. How many edges are in that path?`
     - `The directed graph has a unique shortest path from node X to node Y, following the direction of the arrows. How many edges are in that path?`
   - answer type: `integer`
   - evidence type: `label_path`
   - default node-count support: `5..10` for undirected, `5..9` for directed
   - default shortest-path-length support: `1..5`
   - prompt/evidence contract: evidence is the ordered node-label path from source to goal, includes both queried endpoints, and answer equals `len(path) - 1`
8. `task_graph_relation_reachable_count`
   - ask:
     - `How many nodes, including node X itself, are reachable from X by following the direction of the arrows?`
   - answer type: `integer`
   - evidence type: `label_set`
   - default node-count support: `5..9`
   - default reachable-count support: `1..7`
   - prompt/evidence contract: the queried node itself is included in both the answer and the evidence set, traversal follows edge direction, and generation preserves at least one unreachable node
9. `task_graph_optimization_minimum_spanning_tree_weight`
   - ask:
     - `The weighted graph has a unique minimum spanning tree. What is its total weight?`
   - answer type: `integer`
   - evidence type: `edge_set`
   - default node-count support: `5..8`
   - default extra-edge-count support: `1..2`
   - default edge-weight support: distinct integers in `1..9`
   - prompt/evidence contract: evidence contains every MST edge as an unordered endpoint pair, and answer equals the sum of the weights on those edges
10. `task_graph_order_topological_position`
   - ask:
     - `What is the position of node X in the unique topological order, counting from 1?`
   - answer type: `integer`
   - evidence type: `label_sequence`
   - default node-count support: `5..7`
   - default target-position support: `1..7`
   - prompt/evidence contract: evidence contains every node label in the unique topological order from first to last, and answer equals the 1-based position of the queried node inside that ordered sequence

## Variation axes
1. `task_variant`
   - `degree_count`
   - `in_degree_count`
   - `out_degree_count`
   - `same_component_count`
   - `articulation_point_count`
   - `bridge_count`
   - `unique_cycle_size`
   - `largest_component_size`
   - `topological_position`
   - `minimum_spanning_tree_weight`
   - `shortest_path_length`
   - `directed_shortest_path_length`
   - `reachable_count`
2. `topology_profile`
   - `balanced`
   - `low_degree`
   - `hub_heavy`
3. `scene_variant`
   - `circular`
   - `shell`
   - `spring`

## Rendering policy
1. Use a clean single-panel light-background graph scene in v1.
2. Keep node labels inside the nodes and make them readable at all supported graph sizes.
3. Directed variants should keep edge density lower than the undirected ceiling and render clear arrowheads without reciprocal-pair clutter.
4. Weighted graph tasks should render edge weights as small high-contrast labels near the edges; keep weights in a narrow visible range such as `1..9` and lower node/edge counts so labels remain readable.
5. Prefer lower-crossing or roomier layouts, but never let layout position define the answer.

## Evidence policy
1. Use `label_set` when the witness unit is one or more nodes.
2. Treat `label_set` as an unordered semantic set; canonicalize it internally for deterministic serialization, but do not imply that witness order matters unless the task explicitly asks for an ordered path/sequence.
3. Use `edge_set` when the witness unit is one or more undirected edges.
4. Treat `edge_set` as an unordered semantic set of unordered endpoint pairs; canonicalize endpoint order and outer list order internally only for deterministic serialization.
5. Use `label_path` when the witness unit is an ordered node path.
6. `label_path` is ordered semantically; preserve source-to-goal order and include both endpoints when the prompt asks about one path between two queried nodes.
7. Use `label_sequence` when the witness unit is an ordered node list that is not itself a graph path.
8. `label_sequence` shares the same ordered-label-list JSON shape as `label_path`, but verifier semantics come from task-specific ordering rules rather than edge adjacency between consecutive labels.
9. Keep pixel-space node or edge geometry in projected trace metadata for review overlays rather than as the primary user-facing evidence contract.
10. For same-component queries, make the prompt explicit when the queried node itself is included in both the answer and the evidence set.
11. For largest-component comparison queries, enforce a unique largest component by construction before exposing a single `label_set` witness set.
12. For unique-cycle queries, build a connected unicyclic graph by construction and verify the final graph still has exactly one cycle before exposing the witness set.
13. For shortest-path queries, verify the finalized adjacency still has exactly one shortest path between the queried endpoints before exposing a `label_path` witness.
14. For directed shortest-path queries, compute forward distances over successor adjacency and reverse distances over predecessor adjacency before reconstructing the ordered witness path.
15. For unique topological-order queries, verify the finalized successor adjacency still admits exactly one valid topological order before exposing a `label_sequence` witness.
16. For weighted edge-optimization queries, keep prompt-facing evidence on the selected edge set itself; vertex-only evidence is not sufficient when the answer depends on chosen edges and their weights.

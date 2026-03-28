# Graph Task Setup

## Purpose
Define the concrete v1 setup for the current graph-domain task families.

## V1 scope
1. `domain = graph`
2. Active `task_group`s:
   - `counting`
   - `comparison`
   - `relation`
3. Current concrete tasks:
   - `task_graph_counting_degree_count`
   - `task_graph_counting_articulation_point_count`
   - `task_graph_comparison_largest_component_size`
   - `task_graph_relation_same_component_count`
   - `task_graph_relation_unique_cycle_size`

## Scene contract
1. Use one simple unweighted node-link graph per image.
2. Keep node labels visible and canonical; v1 uses labels from `A..J`.
3. Node count support is `5..10` for undirected graph tasks in v1 and `5..9` for the directed degree-count variants.
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
5. `task_graph_comparison_largest_component_size`
   - ask:
     - `How many nodes are in the largest connected component?`
   - answer type: `integer`
   - evidence type: `label_set`
   - default connected-component count support: `2..4`
   - default unique-largest-component-size support: `2..6`
   - prompt/evidence contract: evidence contains every node in the unique largest connected component, and generation rejects ties for largest component size

## Variation axes
1. `task_variant`
   - `degree_count`
   - `in_degree_count`
   - `out_degree_count`
   - `same_component_count`
   - `articulation_point_count`
   - `unique_cycle_size`
   - `largest_component_size`
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
4. Prefer lower-crossing or roomier layouts, but never let layout position define the answer.

## Evidence policy
1. Use `label_set` when the witness unit is one or more nodes.
2. Treat `label_set` as an unordered semantic set; canonicalize it internally for deterministic serialization, but do not imply that witness order matters unless the task explicitly asks for an ordered path/sequence.
3. Keep pixel-space node boxes in projected trace metadata for review overlays rather than as the primary user-facing evidence contract.
4. For same-component queries, make the prompt explicit when the queried node itself is included in both the answer and the evidence set.
5. For largest-component comparison queries, enforce a unique largest component by construction before exposing a single `label_set` witness set.
6. For unique-cycle queries, build a connected unicyclic graph by construction and verify the final graph still has exactly one cycle before exposing the witness set.
7. If a future graph task needs ordered path evidence, define that as a separate graph-native label/path contract rather than forcing it into `label_set` or bbox-only evidence.

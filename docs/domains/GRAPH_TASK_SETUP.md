# Graph Task Setup

## Purpose
Define the concrete v1 setup for the first graph-domain task family.

## V1 scope
1. `domain = graph`
2. First active `task_group`:
   - `counting`
3. First concrete task:
   - `task_graph_counting_degree_count`

## Scene contract
1. Use one simple undirected unweighted node-link graph per image.
2. Keep node labels visible and canonical; v1 uses labels from `A..J`.
3. Node count support for the first task is `5..10`.
4. No self-loops or multi-edges.
5. Layout is visual variation only; the task semantics come from adjacency.
6. V1 graph scenes may vary whole-image node label format (`letters|numbers`), node glyph style (`circle|rounded_square|hexagon`), named node color, and global layout transform, but those axes stay non-semantic unless a future task explicitly queries them.

## First task contract
1. `task_graph_counting_degree_count`
   - ask: `How many nodes have degree k?`
   - answer type: `integer`
   - evidence type: `label_set`
   - default `query_degree` support: `0..4`
   - default answer support: `0..5`
   - default style supports:
     - label variant: `letters|numbers`
     - node shape: `circle|rounded_square|hexagon`
     - named node color: shared TRACE palette
     - layout transform: `identity|rotate_90|rotate_180|rotate_270|mirror_left_right|mirror_up_down`

## Variation axes
1. `task_variant`
   - `degree_count`
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
3. Prefer lower-crossing or roomier layouts, but never let layout position define the answer.

## Evidence policy
1. Use `label_set` when the witness unit is one or more nodes.
2. Keep pixel-space node boxes in projected trace metadata for review overlays rather than as the primary user-facing evidence contract.
3. If a future graph task needs ordered path evidence, define that as a separate graph-native label/path contract rather than forcing it into bbox-only evidence.

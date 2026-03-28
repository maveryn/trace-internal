# `task_graph_relation_same_component_count`

## Summary
- Domain: `graph`
- Task group: `relation`
- Answer type: `integer`
- Evidence type: `label_set`

## Task
Given one labeled undirected graph, count how many nodes are in the same connected component as a queried node.

The prompt is explicit that both:
- the answer count, and
- the evidence label set

must include the queried node itself.

## Variants
- `same_component_count`

## Generation
- One simple undirected unweighted node-link graph per image.
- Node count: `5..10`
- Connected-component count: `2..4`
- Queried component size support: `1..6`
- Topology profiles:
  - `balanced`
  - `low_degree`
  - `hub_heavy`
- Visual diversity:
  - labels: `letters|numbers`
  - node glyph: `circle|rounded_square|hexagon`
  - layout: `circular|shell|spring`
  - global layout transform
  - named node color

## Evidence contract
- `evidence` is the `label_set` of every node in the connected component containing the queried node.
- The witness set is unordered semantically; the implementation only canonicalizes label order internally for deterministic serialization.
- The queried node label is included in `evidence`.
- `answer = len(evidence)`.

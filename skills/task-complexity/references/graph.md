# Graph Complexity

## Recommended criteria vocabulary
- `visual_scan`
- `ambiguity`
- `clutter`

## Domain fallback weights
```yaml
visual_scan: 0.40
ambiguity: 0.35
clutter: 0.25
```

## Task-group overrides

### `counting`
```yaml
topology_reasoning: 0.40
visual_scan: 0.30
ambiguity: 0.20
clutter: 0.10
```

Measure:
- node count and visible edge load,
- how much topology inspection is required beyond local inspection,
- closeness of near-miss node degrees,
- readability pressure from crossings, tight layouts, or small nodes.

### `relation`
```yaml
topology_reasoning: 0.45
visual_scan: 0.25
ambiguity: 0.20
clutter: 0.10
```

Measure:
- connected-component count and visible graph size,
- how much topology tracing the query requires beyond a local neighborhood (for example same-component traversal, directed reachability traversal, or isolating the unique cycle),
- whether other components have the same or nearly the same size as the queried component,
- readability pressure from crossings, tight layouts, or small nodes.

### `comparison`
```yaml
topology_reasoning: 0.45
visual_scan: 0.20
ambiguity: 0.25
clutter: 0.10
```

Measure:
- connected-component count and visible graph size,
- how much whole-graph comparison is required beyond inspecting one anchored component,
- whether runner-up components are close in size to the unique largest component,
- readability pressure from crossings, tight layouts, or small nodes.

### `path`
```yaml
topology_reasoning: 0.50
visual_scan: 0.20
ambiguity: 0.20
clutter: 0.10
```

Measure:
- visible graph size and edge load,
- shortest-path length and how much tracing beyond local inspection is required,
- how many off-path branches or safe off-path cycles create near-path distractor structure even when the shortest path remains unique,
- whether the task is directed or undirected, since directed path tracing adds extra control-flow burden even at the same witness length,
- readability pressure from crossings, tight layouts, or small nodes.

### `optimization`
```yaml
topology_reasoning: 0.50
visual_scan: 0.20
ambiguity: 0.20
clutter: 0.10
```

Measure:
- visible node/edge load plus edge-label count,
- how much global edge-choice reasoning is required beyond local inspection (for example MST selection over one connected weighted graph),
- how close alternative non-tree edges are to the selected tree under the task’s uniqueness rule,
- readability pressure from crossings, tight layouts, or dense edge-weight labels.

## Notes
- Keep graph-domain criteria broad at domain scope; `topology_reasoning` belongs at task-group scope unless every graph family needs it.
- Do not let layout choice define difficulty directly unless the task truly depends on layout semantics; layout should usually feed `clutter` or `ambiguity`, not replace topology reasoning.
- Non-semantic whole-image style axes such as label format, node glyph, named node color, or global layout transform should usually affect `clutter` only lightly, if at all; they are diversity tools first, not graph-reasoning difficulty knobs.
- Prefer adjacency-driven knobs over answer magnitude when modeling graph difficulty.

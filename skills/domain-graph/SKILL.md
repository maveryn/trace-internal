---
name: domain-graph
description: Use when designing, implementing, or reviewing TRACE graph-domain tasks, especially for simple-graph contracts, label-based evidence, topology-vs-layout separation, and graph-specific ambiguity checks.
---

# Graph Domain

Use this whenever the task lives under `domain=graph`.

## Read first
1. `docs/domains/GRAPH_TASK_SETUP.md`
2. `docs/domains/TASK_FAMILY_VARIANTS.md`
3. `docs/project/STATUS.md`
4. `docs/workflows/TASK_AUTHORING.md`
5. `docs/workflows/SHARED_UTILITIES.md`

## V1 graph-domain policy
- Keep graphs simple and unweighted by default; if a task needs weights, make them explicit, keep them visually readable (for example small integers such as `1..9`), and ensure they are semantically essential rather than decorative.
- Node labels are the canonical prompt-facing identities for this domain.
- Layout is visual variation, not semantics.
- Questions should be answerable from adjacency/topology alone even if the layout changes.
- Prefer one graph per image in v1.
- Whole-image visual diversity such as label format, node glyph style, named node color, or global layout transform is encouraged as long as it remains non-semantic for the task.
- If a graph task mixes undirected and directed variants, make the prompt wording, trace metadata, and rendered edge treatment explicit (`degree` vs `in-degree` vs `out-degree`, arrowheads for directed edges, and a recorded `graph_directionality` field).
- For directed path tasks, follow arrow direction semantically and verify witness uniqueness with successor adjacency plus reverse-distance checks from the goal.

## Evidence heuristics
- Use `label_set` for unordered node witness sets.
- Use `edge_set` for unordered edge witness sets.
- Use `label_path` for ordered node-path witnesses.
- Use `label_sequence` for ordered node witnesses that are not graph paths.
- Treat `label_set` as unordered semantically; canonicalize it internally for determinism, but do not present ordering as part of the task unless the task truly depends on order.
- Treat `edge_set` as an unordered semantic set of unordered endpoint pairs; canonicalize each pair and the outer set internally only for determinism.
- Treat `label_path` as ordered semantically; preserve source-to-goal order and include endpoints whenever the path contract names them explicitly.
- Treat `label_sequence` as ordered semantically; keep the same ordered-label-list JSON shape, but verify it against the task’s ordering rule rather than edge adjacency between consecutive labels.
- Use one label answer or ordered label path only when the semantics truly require it.
- Keep node/edge pixel geometry in trace for reviews and overlays, but do not force bbox evidence when labels already provide the natural witness contract.
- When labels are numeric, keep evidence in ascending numeric label order rather than raw lexicographic string order.

## Variation heuristics
- Separate topology variation from layout variation.
- Use topology families such as:
  - balanced
  - low_degree
  - hub_heavy
- Use layout families such as:
  - circular
  - shell
  - spring
- Add safe whole-image style axes such as:
  - label format (`letters|numbers`)
  - node glyph (`circle|rounded_square|hexagon`)
  - named node color
  - global layout transform
- Make sure layout choice does not leak the answer or change the node labels.

## Current graph coverage
- `comparison`
  - `task_graph_comparison_largest_component_size`
- `counting`
  - `task_graph_counting_degree_count`
  - `task_graph_counting_articulation_point_count`
  - `task_graph_counting_bridge_count`
- `path`
  - `task_graph_path_shortest_path_length`
- `optimization`
  - `task_graph_optimization_minimum_spanning_tree_weight`
- `order`
  - `task_graph_order_topological_position`
- `relation`
  - `task_graph_relation_reachable_count`
  - `task_graph_relation_same_component_count`
  - `task_graph_relation_unique_cycle_size`

## Shared helpers to prefer
- `trace/tasks/graph/shared/graph_sampling.py`
- `trace/tasks/graph/shared/graph_scene.py`
- `trace/tasks/graph/shared/task_support.py`
- `trace/tasks/graph/shared/visual_defaults.py`
- `trace/tasks/graph/shared/complexity.py`

## Pair with
- `skills/task-design/SKILL.md`
- `skills/task-complexity/SKILL.md`
- `skills/task-implementation/SKILL.md`
- `skills/verification-review/SKILL.md`

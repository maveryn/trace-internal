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
- Keep graphs simple and unweighted by default; directionality should be an explicit task/task-variant contract rather than an implicit renderer detail.
- Node labels are the canonical prompt-facing identities for this domain.
- Layout is visual variation, not semantics.
- Questions should be answerable from adjacency/topology alone even if the layout changes.
- Prefer one graph per image in v1.
- Whole-image visual diversity such as label format, node glyph style, named node color, or global layout transform is encouraged as long as it remains non-semantic for the task.
- If a graph task mixes undirected and directed variants, make the prompt wording, trace metadata, and rendered edge treatment explicit (`degree` vs `in-degree` vs `out-degree`, arrowheads for directed edges, and a recorded `graph_directionality` field).

## Evidence heuristics
- Use `label_set` for node witness sets.
- Treat `label_set` as an unordered witness set semantically; canonicalize it internally for determinism, but do not present ordering as part of the task unless the task truly depends on order.
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
- `relation`
  - `task_graph_relation_same_component_count`

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

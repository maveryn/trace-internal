---
name: domain-graph
description: Use when designing, implementing, or reviewing TRACE graph-domain tasks, especially for simple-graph contracts, label-based annotation, topology-vs-layout separation, and graph-specific ambiguity checks.
---

# Graph Domain

Use this whenever the task lives under `domain=graph`.

## Read first
1. `docs/domains/graph.md`
2. `docs/ACTIVE_TASK_INVENTORY.md` for the generated active scene/task list.
3. `docs/workflows/TASK_AUTHORING.md`
4. `docs/workflows/SHARED_UTILITIES.md`

## Active-contract reminders
- `docs/domains/graph.md` owns the active graph scene/task/annotation contract.
- Keep graphs simple and unweighted by default; if a task needs weights, make them explicit, keep them visually readable (for example small integers such as `1..9`), and ensure they are semantically essential rather than decorative.
- Node labels are the canonical prompt-facing identities for this domain.
- Layout is visual variation, not semantics.
- Questions should be answerable from adjacency/topology alone even if the layout changes.
- Prefer one graph per image in v0.
- Whole-image visual diversity such as label format, node glyph style, named node color, or global layout transform is encouraged as long as it remains non-semantic for the task.
- If a graph task mixes undirected and directed variants, make the prompt wording, trace metadata, and rendered edge treatment explicit (`degree` vs `in-degree` vs `out-degree`, arrowheads for directed edges, and a recorded `graph_directionality` field).
- For directed path tasks, follow arrow direction semantically and verify witness uniqueness with successor adjacency plus reverse-distance checks from the goal.

## Practical review checklist
- Use the annotation contracts in `docs/domains/graph.md`: `point_set`, `point_sequence`, `point_pair_set`, `bbox_set`, and `bbox_sequence` according to witness semantics.
- Treat `point_set`, `point_pair_set`, and counted-node `bbox_set` annotation as unordered semantically; canonicalize internally for determinism, but do not present ordering as part of the task unless the task truly depends on order.
- Preserve `point_sequence` and `bbox_sequence` order for path, traversal, and operation tasks.
- Keep node/edge pixel geometry in trace for reviews and overlays, and choose the public annotation type that matches the witness unit.
- Separate topology variation from layout variation.
- Prefer shared graph helpers under `trace/tasks/graph/shared/` before adding task-local sampling/rendering logic.

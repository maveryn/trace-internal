---
name: domain-graph
description: Use when designing, implementing, or reviewing TRACE graph-domain tasks, especially for simple-graph contracts, label-based evidence, topology-vs-layout separation, and graph-specific ambiguity checks.
---

# Graph Domain

Use this whenever the task lives under `domain=graph`.

## Read first
1. `docs/domains/GRAPH_TASK_SETUP.md`
2. `docs/project/STATUS.md`
3. `docs/workflows/TASK_AUTHORING.md`
4. `docs/workflows/SHARED_UTILITIES.md`

## Active-contract reminders
- `docs/domains/GRAPH_TASK_SETUP.md` owns the active graph scene/task/evidence contract.
- Keep graphs simple and unweighted by default; if a task needs weights, make them explicit, keep them visually readable (for example small integers such as `1..9`), and ensure they are semantically essential rather than decorative.
- Node labels are the canonical prompt-facing identities for this domain.
- Layout is visual variation, not semantics.
- Questions should be answerable from adjacency/topology alone even if the layout changes.
- Prefer one graph per image in v1.
- Whole-image visual diversity such as label format, node glyph style, named node color, or global layout transform is encouraged as long as it remains non-semantic for the task.
- If a graph task mixes undirected and directed variants, make the prompt wording, trace metadata, and rendered edge treatment explicit (`degree` vs `in-degree` vs `out-degree`, arrowheads for directed edges, and a recorded `graph_directionality` field).
- For directed path tasks, follow arrow direction semantically and verify witness uniqueness with successor adjacency plus reverse-distance checks from the goal.

## Practical review checklist
- Use the evidence contracts in `docs/domains/GRAPH_TASK_SETUP.md`: `label_set`, `edge_set`, `label_path`, or `label_sequence` according to witness semantics.
- Treat `label_set` as unordered semantically; canonicalize it internally for determinism, but do not present ordering as part of the task unless the task truly depends on order.
- Treat `edge_set` as an unordered semantic set of unordered endpoint pairs; canonicalize each pair and the outer set internally only for determinism.
- Preserve `label_path` source-to-goal order and distinguish it from `label_sequence`, which is ordered but not necessarily path-adjacent.
- Keep node/edge pixel geometry in trace for reviews and overlays, but do not force bbox evidence when labels already provide the natural witness contract.
- When unordered graph evidence uses numeric labels, canonicalize it in ascending numeric label order rather than raw lexicographic string order; do not reorder `label_path` or `label_sequence` witnesses, because their task semantics depend on the emitted order.
- Separate topology variation from layout variation.
- Prefer shared graph helpers under `trace/tasks/graph/shared/` before adding task-local sampling/rendering logic.

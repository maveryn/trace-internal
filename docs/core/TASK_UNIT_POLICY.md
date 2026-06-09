# TRACE Task-Unit Policy

`docs/core/TRACE_TAXONOMY_DESIGN.md` is the canonical policy for taxonomy
design and program-contract refinement. This file summarizes the task-unit
decision rules; when in doubt, use the concrete-program checklist in the core
taxonomy design doc.

This document defines what should count as one TRACE task.

Use it when:
- proposing new tasks,
- deciding whether a new idea should become a `query_id` / query id or a
  new task id,
- evaluating whether an existing task should be split or merged,
- rebalancing the benchmark for uniform task-level sampling.

## 1) Why this matters
1. TRACE samples uniformly across task ids by default.
2. That means the real benchmark unit is the **task**, not the `domain` or `task_group`.
3. If one task is extremely broad and another is extremely narrow, uniform task sampling becomes uneven.
4. So the key design question is not just “is this a good question?” but “is this the right **task unit**?”

## 2) Core definition
1. A TRACE task should represent **one stable visual-grounding contract**.
2. A task is not just a theme bucket like “cards”, “tables”, or “physics”.
3. Public taxonomy identifies tasks as `domain -> scene_id -> task_id`, where
   active public ids use `task_<domain>__<scene_id>__<task_slug>`.
4. `domain + scene_id` is the renderer/image axis. It defines the scene
   contract: visual grammar, visible object vocabulary, nonsemantic style
   support, and any stable query-facing view contract.
5. `task_slug` is the reasoning/output axis. It is derived from one task
   contract over that scene.
6. Source `task_group` remains an implementation/config grouping during the
   transition, but it is not the public taxonomy unit.
7. Use `query_id` only for task-internal branch grouping and replay selectors.

## 2.1) Hard Task Boundary

A public task is valid when it has one stable scene contract and one stable
task contract.

The task contract has exactly three required fields:

1. **Answer schema** — the prompt-facing answer type and shape, such as
   integer count, integer value, one-decimal numeric value, string label,
   option letter, or reduced fraction.
2. **Annotation schema** — the prompt-facing annotation type and semantic witness
   structure, such as unordered object bboxes, ordered path points, or keyed
   role-bound witnesses.
3. **Program schema** — the shallowest concrete reasoning-program skeleton
   that preserves the intermediate objects required to answer, such as
   selected object set, scoped object set, ranked list, path, reachable set,
   aggregate, legal move set, counterfactual scene state, or formula-derived
   unknown. It must name the actual candidate set, operand roles, derived
   computation, final operator, output binding, and annotation role template.
   Generic placeholders such as `select_by_rank(items, metric, rank)` are
   draft-only and cannot justify an accepted merge/split decision.

Merge tasks only when the scene contract remains stable and all three task
contract fields match. If any task-contract field differs, or if one task would
mix materially different query-facing views, the default decision is **keep
separate**, not "needs review".

Examples:

1. Highest vs lowest over the same visible chart marks can stay one task when
   both are parameters of the same ranked-selection program schema.
2. Above vs below a threshold over the same object set can stay one task when
   both are one-bound predicate parameters.
3. Threshold count and interval count should split because one uses a
   one-bound predicate and the other uses a two-bound predicate.
4. Shortest path vs longest path should split when they require different
   path-optimization programs, even if both use ordered path annotation.
5. Node-color count vs edge-color count should split when the annotation witness
   object changes from nodes to edges.
6. Max-flow value vs minimum-cut edge count should split because the program
   schema and annotation/answer contract differ, even though they share a
   flow-network scene.

Use a "blocked/needs inspection" outcome only when the available docs, code, or
sampled outputs are inconsistent or insufficient to determine the scene
contract or task contract. Do not use a review bucket merely because two tasks
are conceptually related or share a scene.

## 2.2) Query ID Definition

Use **query id** as the human-facing term and `query_id` as the canonical
metadata field.

A query id is an implementation/review key for task-internal branches and
replay. It is not part of public task identity. In the target design, query ids
should be derivable from parameter axes inside a stable task contract.

Rules:

1. Query ids may name mirrored directions, predicate directions, rank
   parameters, target attributes, or other bounded branches inside one stable
   program schema.
2. Query ids must not hide different answer schemas, annotation schemas, program
   schemas, or query-facing view contracts.
3. Visual/rendering/style choices are not query ids unless they change the
   task contract.
4. Difficulty knobs, counts, labels, colors, and sampled values are not query
   ids unless they are needed as replay keys for a documented task branch.
5. Different program schemas are not query ids just because the scene, answer
   type, or annotation type is shared.

## 3) What should stay stable within one task
The following should usually remain broadly stable inside a single task:

### A. Scene scaffold
1. The image grammar should feel like the same kind of scene.
2. Cosmetic style can vary, but the core interaction pattern should stay recognizable.
3. Examples:
   - one reference-plus-scene matching layout,
   - one single table with queried cells,
   - one board game state with move candidates,
   - one analog clock or multi-clock grid.

### B. Unit of attention
1. The same kind of visual object should remain central:
   - cards,
   - table cells,
   - board squares,
   - event blocks,
   - labeled candidates,
   - graph nodes/edges,
   - etc.
2. If one branch reasons over subsets of objects and another reasons over
   ordered sequences of those objects, that is often a sign of a new task.

### C. Witness semantics
1. Public annotation should usually refer to the same semantic kind of witness
   across branches.
2. Annotation type alone does **not** decide the boundary, but stable witness semantics are a strong sign of a coherent task.
3. Examples of stable witness semantics:
   - qualifying object boxes,
   - winning option panel,
   - ordered path,
   - queried table cells,
   - matching labels.

### D. Visual search pattern
1. The model should be doing roughly the same kind of perceptual job across
   task-internal branches.
2. Examples:
   - find qualifying items,
   - compare a few named values,
   - trace one path,
   - identify one winning candidate,
   - count one family of visible witnesses.

## 4) What may vary inside one task
These differences do **not** automatically require a new task:
1. scene chrome / style choices,
2. object identities, colors, counts, and placements,
3. local arithmetic or logical reasoning over the same support set,
4. multiple query ids over the same witness semantics,
5. being text-heavy, as long as the text must still be visually located/read from the image,
6. reasoning difficulty.

In other words: a task does **not** need equal difficulty across branches, but
it should keep one stable grounding contract.

## 5) New query branch vs new task

### Add a new `query_id` / query id when:
1. the same scene scaffold still works,
2. the same unit of attention still matters,
3. the same witness semantics still apply,
4. the model is doing roughly the same visual search,
5. the same answer schema, annotation schema, and program schema still apply,
6. the new query is a parameter, mirror direction, threshold, ordering choice,
   or local answer transform inside that program schema.

Examples:
1. adding more unordered card-qualification queries inside one hand-based card task,
2. adding above/below threshold directions inside one single-column
   threshold-count task,
3. adding more clock readout offsets inside one single-clock task.
4. adding highest/lowest or kth-highest/kth-lowest mirrors over the same
   located chart marks.

### Create a new task when:
1. the scene grammar changes materially,
2. the witness semantics change materially,
3. the visual search pattern changes materially,
4. the program schema changes materially,
5. the new program has a different notion of what the “relevant object” is,
6. the same broad theme now hides multiple different perceptual contracts.

Common signals:
1. **order matters vs order does not**
   - unordered subset counting vs ordered sequence/run reasoning
2. **single support region vs pairwise or full-scene support**
   - one queried column vs row-wise two-column comparison
3. **destination reasoning vs consequence reasoning**
   - legal moves vs result of one marked move
4. **one interaction grammar vs another**
   - row rule checking vs 2D grid rule checking
5. **different program schema**
   - shortest path vs longest path
   - path traversal vs topological ordering
   - MST vs max flow
   - articulation points vs bridge edges

## 6) Different annotation is a signal, not a rule
1. Different annotation formats or annotation scopes often reveal that a task is over-broad.
2. But annotation differences alone do **not** force a split.
3. The real question is whether the underlying perceptual contract changed.

Good mental model:
1. if annotation differs **because the grounding job changed**, split pressure is real;
2. if annotation differs only slightly while the visual job remains the same, the task can stay unified.

## 7) Split now vs split later
Not every split candidate should be split immediately.

### Split now when:
1. the current task clearly mixes multiple grounding families, **and**
2. each resulting child would still be a healthy standalone task with enough internal variety.

### Mark as a latent split when:
1. the current task mixes multiple grounding families, **but**
2. one or more child families would still be too narrow if split today.

In that case:
1. keep the task together for now,
2. record the split pressure,
3. and split later once the thinner child family has enough additional query/scene variety.

This matters especially in domains like `games`, where different games may naturally support different numbers of viable tasks.

## 8) Merge policy
Merge only when two task ids are effectively the same sampling unit.

Required merge conditions:
1. same scene contract, including stable query-facing view contract,
2. same answer schema,
3. same annotation schema,
4. same program schema,
5. only query-parameter, mirror-operator, threshold, ordering, or local
   answer-transform differences separate them.

Do **not** merge just because two tasks come from the same theme, scene, domain,
answer type, or annotation type. If two tasks are related but fail any required
merge condition, mark them **keep separate** unless sampled outputs or docs are
inconsistent enough to block classification.

## 9) Domain asymmetry is acceptable
1. Different domains do **not** need the same number of tasks.
2. Different games also do **not** need the same number of tasks.
3. Some families naturally support many healthy task units; others saturate quickly.
4. The goal is not symmetry of counts.
5. The goal is a benchmark where each task is a comparably meaningful sampling unit.

## 10) Variant-Aware Dataset Sampling
1. The default TRACE sampling unit remains the task id.
2. `query_id` values are diagnostics for query ids inside one task, not
   separate public tasks. Source `query_id` remains only an internal replay
   selector.
3. Large RLVR training builds may optionally use query-id-aware task counts when comparing task-unit ablations.
4. The supported weight formula is:
   - `task_weight = 1 + alpha * (active_query_id_count - 1)`
5. Use `alpha=0.0` for the equal-task baseline, `alpha=0.5` for the balanced query-id-aware recipe, and `alpha=1.0` for the query-id-proportional ablation.
6. This changes only task-level build counts; task-local query sampling remains owned by each task's config and generator.

## 11) Practical checklist
When deciding whether something is one task or multiple tasks, ask:
1. Is the model looking at the same kind of thing each time?
2. Is it performing the same kind of visual search?
3. Would the public annotation still mean the same kind of witness?
4. Is the same program schema being used?
5. Does repeated sampling from this task feel like one grounded family rather than several bundled together?
6. If split, would both children still be viable standalone tasks?

If the answers are mostly “yes”, keep it as one task.
If the answers are mostly “no”, it likely wants multiple tasks.
If the answers are mixed because one required merge condition fails, keep the
tasks separate rather than creating a vague review candidate.

## 12) Relationship to the audit workflow
1. `docs/workflows/TASK_UNIT_AUDIT.md` is the review procedure.
2. This document is the underlying policy for what a TRACE task should be.
3. Use this policy first, then use the audit workflow to apply it to concrete tasks.

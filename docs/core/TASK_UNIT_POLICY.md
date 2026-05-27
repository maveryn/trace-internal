# TRACE Task-Unit Policy

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
1. A TRACE task should represent **one stable visual-grounding family**.
2. A task is not just a theme bucket like “cards”, “tables”, or “physics”.
3. A task should correspond to one reasonably uniform perceptual contract:
   - what the model must look at,
   - what kind of visual search it performs,
   - what kind of witness/evidence supports the answer,
   - and what kind of scene grammar it sees repeatedly.
4. Public taxonomy identifies this as `domain -> scene_id -> task_id`.
5. Source `task_group` remains an implementation/config grouping during the transition, but it is not the public taxonomy unit.
6. Use `query_id` for task-internal branch identity and replay selectors.

## 2.1) Hard Task Boundary

A public task is one stable combination of the following four contract axes:

1. **Scene grammar** — the repeated visual setup and rendering grammar.
2. **Primary witness kind** — the semantic object type that evidence points to,
   such as a node set, edge set, ordered path, table cells, chart marks, map
   regions, option panel, or page element boxes.
3. **Visual search pattern** — the perceptual job needed to locate the support,
   such as finding qualifying objects, tracing one path, selecting one option,
   ranking visible marks, or aggregating a named group of cells/regions.
4. **Algorithmic/objective family** — the domain-level problem family applied
   after the visual support is located.

Merge tasks only when all four axes match and the difference can be expressed
as a task-local `query_id` operator or parameter. If any axis differs, the
default decision is **keep separate**, not "needs review".

Objective family is intentionally **coarser than an individual subroutine**.
Use the smallest named domain concept that still describes the whole task
without becoming a theme bucket. A task may contain several `query_id`s with
different rationale templates when they are branches of one coherent objective
family over the same scene and witness contract.

Examples of coherent objective families:

1. Music-staff `pitch/interval` reading may include note naming, interval
   naming, same-pitch checks, and transposition checks.
2. Music-staff `key/scale` reasoning may include key-signature identification,
   scale-degree function, and scale validation.
3. Music-staff `chord/harmony` reasoning may include chord quality, inversion,
   and roman-numeral labeling.
4. Arithmetic-constraint missing-value puzzles may include several visible
   rule templates when the scene remains a compact rule-bearing arithmetic
   diagram with one missing value.

Examples of different objective families:

1. Music key/scale reasoning vs visible bar counting.
2. Chord-label reasoning vs dominant-chord counting.
3. Path length between hierarchy nodes vs subtree descendant counting.
4. Shortest path vs longest path in a graph.
5. BST search/insert path operation vs heap-property violation scan.

Examples:

1. Highest vs lowest over the same visible chart marks is usually one objective
   family with mirrored query parameters.
2. Above vs below a threshold over the same object set is usually one predicate
   family with mirrored query parameters.
3. Shortest path vs longest path are different algorithmic/objective families,
   even if both use an ordered path as evidence.
4. Node-color count vs edge-color count are different primary witness kinds.
5. Articulation-point count vs bridge-edge count are different witness kinds and
   different graph-objective families.
6. Max-flow value vs minimum-cut edge count are different objective contracts,
   even though they share a flow-network scene.

Use a "blocked/needs inspection" outcome only when the available docs, code, or
sampled outputs are inconsistent or insufficient to determine the four axes.
Do not use a review bucket merely because two tasks are conceptually related or
share a scene.

## 2.2) Query ID Definition

Use **query id** as the human-facing term and `query_id` as the canonical
metadata field.

A query id is the smallest task-internal semantic branch that needs a
distinct reasoning/rationale template family. This includes changes to the
requested operation, answer transform, witness role, ordering rule, filtering
predicate, traversal rule, comparison target, or evidence explanation.

Rules:

1. Every active `query_id` must have a corresponding rationale template family
   for each supported output mode and detail level once rationale targets are
   enabled for that task.
2. If a branch needs a different rationale template family, give it a distinct
   `query_id`.
3. If two branches differ only by slot values inside the same rationale
   structure, they may remain one `query_id`. Examples include mirrored words
   like highest/lowest or before/after only when the same template can express
   both with a parameter.
4. Visual/rendering/style variants are not query ids unless they change the
   reasoning/rationale template family.
5. Difficulty knobs, counts, labels, colors, and sampled values are not query
   variants unless they change the reasoning/rationale template family.
6. Different algorithms or objective families are not query ids just
   because the scene, answer type, or evidence type is shared. For example,
   shortest path and longest path should be separate public tasks unless the
   domain intentionally defines a broader objective family that preserves one
   solver/rationale structure.

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
2. If one variant reasons over subsets of objects and another reasons over ordered sequences of those objects, that is often a sign of a new task.

### C. Witness semantics
1. Public evidence should usually refer to the same semantic kind of witness across variants.
2. Evidence type alone does **not** decide the boundary, but stable witness semantics are a strong sign of a coherent task.
3. Examples of stable witness semantics:
   - qualifying object boxes,
   - winning option panel,
   - ordered path,
   - queried table cells,
   - matching labels.

### D. Visual search pattern
1. The model should be doing roughly the same kind of perceptual job across variants.
2. Examples:
   - find qualifying items,
   - compare a few named values,
   - trace one path,
   - identify one winning candidate,
   - count one family of visible witnesses.

## 4) What may vary inside one task
These differences do **not** automatically require a new task:
1. scene chrome / style variants,
2. object identities, colors, counts, and placements,
3. local arithmetic or logical reasoning over the same support set,
4. multiple query ids over the same witness semantics,
5. being text-heavy, as long as the text must still be visually located/read from the image,
6. reasoning difficulty.

In other words: a task does **not** need equal difficulty across variants, but it should keep one stable grounding contract.

## 5) New variant vs new task

### Add a new `query_id` / query id when:
1. the same scene scaffold still works,
2. the same unit of attention still matters,
3. the same witness semantics still apply,
4. the model is doing roughly the same visual search,
5. the same algorithmic/objective family still applies,
6. the new query is a parameter, mirror direction, threshold, ordering choice,
   or local answer transform inside that family.

Examples:
1. adding more unordered card-qualification queries inside one hand-based card task,
2. adding more threshold/interval conditions inside one single-column table-counting task,
3. adding more clock readout offsets inside one single-clock task.
4. adding highest/lowest or kth-highest/kth-lowest mirrors over the same
   located chart marks.

### Create a new task when:
1. the scene grammar changes materially,
2. the witness semantics change materially,
3. the visual search pattern changes materially,
4. the algorithmic/objective family changes materially,
5. the new family has a different notion of what the “relevant object” is,
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
5. **different algorithmic objective**
   - shortest path vs longest path
   - path traversal vs topological ordering
   - MST vs max flow
   - articulation points vs bridge edges

## 6) Different evidence is a signal, not a rule
1. Different evidence formats or evidence scopes often reveal that a task is over-broad.
2. But evidence differences alone do **not** force a split.
3. The real question is whether the underlying perceptual contract changed.

Good mental model:
1. if evidence differs **because the grounding job changed**, split pressure is real;
2. if evidence differs only slightly while the visual job remains the same, the task can stay unified.

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
1. same scene grammar,
2. same primary witness kind,
3. same visual search pattern,
4. same algorithmic/objective family,
5. same answer/evidence role at the contract level,
6. only query-parameter, mirror-operator, threshold, ordering, or local
   answer-transform differences separate them.

Do **not** merge just because two tasks come from the same theme, scene, domain,
answer type, or evidence type. If two tasks are related but fail any required
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
3. Would the public evidence still mean the same kind of witness?
4. Is the same algorithmic/objective family being used?
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

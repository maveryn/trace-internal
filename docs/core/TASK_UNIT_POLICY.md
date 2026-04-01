# TRACE Task-Unit Policy

This document defines what should count as one TRACE task.

Use it when:
- proposing new tasks,
- deciding whether a new idea should become a `task_variant` or a new task id,
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
4. multiple query variants over the same witness semantics,
5. being text-heavy, as long as the text must still be visually located/read from the image,
6. reasoning difficulty.

In other words: a task does **not** need equal difficulty across variants, but it should keep one stable grounding contract.

## 5) New variant vs new task

### Add a new `task_variant` when:
1. the same scene scaffold still works,
2. the same unit of attention still matters,
3. the same witness semantics still apply,
4. the model is doing roughly the same visual search,
5. the new query feels like a natural extension of the existing family.

Examples:
1. adding more unordered card-qualification queries inside one hand-based card task,
2. adding more threshold/interval conditions inside one single-column table-counting task,
3. adding more clock readout offsets inside one single-clock task.

### Create a new task when:
1. the scene grammar changes materially,
2. the witness semantics change materially,
3. the visual search pattern changes materially,
4. the new family has a different notion of what the “relevant object” is,
5. the same broad theme now hides multiple different perceptual contracts.

Common signals:
1. **order matters vs order does not**
   - unordered subset counting vs ordered sequence/run reasoning
2. **single support region vs pairwise or full-scene support**
   - one queried column vs row-wise two-column comparison
3. **destination reasoning vs consequence reasoning**
   - legal moves vs result of one marked move
4. **one interaction grammar vs another**
   - row rule checking vs 2D grid rule checking

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

Strong merge signals:
1. same scene scaffold,
2. same unit of attention,
3. same witness semantics,
4. same visual search pattern,
5. only thin query wording or arithmetic differences separate them.

Do **not** merge just because two tasks come from the same theme or domain.

## 9) Domain asymmetry is acceptable
1. Different domains do **not** need the same number of tasks.
2. Different games also do **not** need the same number of tasks.
3. Some families naturally support many healthy task units; others saturate quickly.
4. The goal is not symmetry of counts.
5. The goal is a benchmark where each task is a comparably meaningful sampling unit.

## 10) Practical checklist
When deciding whether something is one task or multiple tasks, ask:
1. Is the model looking at the same kind of thing each time?
2. Is it performing the same kind of visual search?
3. Would the public evidence still mean the same kind of witness?
4. Does repeated sampling from this task feel like one grounded family rather than several bundled together?
5. If split, would both children still be viable standalone tasks?

If the answers are mostly “yes”, keep it as one task.
If the answers are mostly “no”, it likely wants multiple tasks.

## 11) Relationship to the audit workflow
1. `docs/workflows/TASK_UNIT_AUDIT.md` is the review procedure.
2. This document is the underlying policy for what a TRACE task should be.
3. Use this policy first, then use the audit workflow to apply it to concrete tasks.

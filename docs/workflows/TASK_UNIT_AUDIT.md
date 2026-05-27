# TRACE Task-Unit Audit

Use this workflow when auditing whether a proposed or active TRACE task is the right unit for uniform task-level sampling.

Read `docs/core/TASK_UNIT_POLICY.md` first for the underlying definition of what should count as one TRACE task.

Naming rule: use **query id** as the human-facing term for task-internal
semantic branches and `query_id` as the canonical metadata field. Do not call
these branches `task variants`; `task_id` is the public sampling unit.

## 1) Purpose
1. Keep the TRACE task inventory aligned with the real sampling unit used at training time: one task id gets one share of sampling mass.
2. Ensure each task is a reasonably uniform visual-grounding problem rather than a loose theme bucket.
3. Catch tasks that should be broadened, merged, split, or removed before they distort benchmark balance.

## 2) Core principle
1. In TRACE, `task_group` is mostly an implementation and organization aid.
2. The important benchmark unit is the `task`.
3. A good TRACE task should therefore represent one stable visual-grounding family with enough internal scene/query variety to justify uniform sampling alongside the other tasks.
4. Tasks do **not** need equal reasoning difficulty.
5. Tasks **do** need roughly comparable within-task visual variety and grounding breadth.
6. Audits must use the hard task boundary in
   `docs/core/TASK_UNIT_POLICY.md`: scene grammar, primary witness kind, visual
   search pattern, and algorithmic/objective family.
7. If any one of those axes differs between two active task ids, the default
   decision is `Keep`, not a speculative review candidate.

## 3) What this audit should not penalize
1. A task may be text-heavy if the text must still be visually found/read from the image.
2. A task may be reasoning-heavy if the image is still genuinely required.
3. A task may be easy or hard; difficulty is not the main audit target here.

## 4) Task-unit rubric
Audit each task against the following questions.

### A. Uniform grounding family
1. Do the scene/query ids feel like the same kind of visual-grounding job?
2. Or is the task actually mixing multiple distinct grounding families under one task id?

### B. Within-task scene variety
1. Does the task have enough layout, arrangement, object-role, or scene-structure variety?
2. Is it more than one nearly fixed scaffold with superficial cosmetic change?

### C. Within-task query variety
1. Does the task have multiple query ids, or equivalent combinatorial diversity, within the same grounding family?
2. Would repeated samples from this task still expose the model to meaningfully different grounded questions?
3. If rationale targets are enabled, does every distinct rationale-template
   family correspond to a distinct `query_id`?

### D. Grounding necessity
1. Is the image genuinely required?
2. Would weak-perception shortcuts solve too much of the task?
3. Does the model need to locate, compare, relate, or read visually grounded content rather than rely mostly on prompt wording?

### E. Evidence fit
1. Is the public evidence/witness contract natural for the task?
2. Is the witness visually meaningful rather than degenerate, vacuous, or nearly identical to the final answer?
3. Does the evidence support the same execution trace as the answer?

### F. Variant balance
1. Do the variants within the task have roughly similar grounding breadth?
2. Is one variant much richer or more visually demanding than the others?
3. If one variant dominates the task's diversity while others are narrow, the task likely needs restructuring.

### G. Objective-family boundary
1. Does every query branch use the same algorithmic/objective family?
2. Are differences only mirror operators, thresholds, ordering choices, sampled
   slots, or local answer transforms over the same located support?
3. Or does a branch require a genuinely different solver family, such as
   shortest path vs longest path, traversal vs topological order, MST vs max
   flow, node removal vs edge removal, or option selection vs direct trace
   readout?
4. Do not split a task just because each `query_id` needs a different
   rationale template. Different rationale templates imply distinct
   `query_id`s, not necessarily distinct public tasks.
5. For notation systems, rule-based puzzles, and other domain languages, audit
   the objective at the smallest coherent named concept level, not at the
   finest subroutine level. For example, music `key/scale` query ids and
   arithmetic missing-value rule templates can stay inside one task when they
   share the same scene grammar, witness class, answer/evidence role, and
   public problem family.

## 5) Decision outcomes
Each task should end the audit with one of the following labels.

### Keep
1. The task already looks like a good TRACE sampling unit.

### Broaden
1. The task is a valid unit, but too narrow in scene/query variety.
2. Keep the task id and add more grounded variation within the same family.

### Merge
1. Two or more tasks are really the same visual-grounding family.
2. Their differences are too thin to justify separate uniform-sampling units.

### Split
1. One task is actually carrying multiple distinct grounding families.
2. Separate them into multiple task ids so each unit is visually and contractually cleaner.

### Retire
1. The task is too weak, too degenerate, too redundant, or too awkward for TRACE evidence to justify keeping as a standalone task.

### Blocked Needs Inspection
1. The docs, code, prompt bundles, or sampled outputs are inconsistent enough
   that the task cannot be classified.
2. This label is not for tasks that merely share a scene or topic.
3. Name the exact missing or conflicting information needed to classify it.

## 6) Merge triggers
Recommend merging only when all of the following are true:
1. Same scene grammar.
2. Same primary witness kind.
3. Same visual search pattern.
4. Same algorithmic/objective family.
5. Same answer/evidence role at the contract level.
6. Differences are only query-parameter, mirror-operator, threshold, ordering,
   local answer-transform, or same-family rule-template choices.

Do not list a merge candidate because two tasks are conceptually related, share
the same scene, or share answer/evidence types. If one required merge condition
fails, classify the pair as `Keep`.

## 7) Split triggers
Consider splitting a task when one or more of the following are true:
1. Variants require different visual search patterns.
2. Variants use meaningfully different scene scaffolds.
3. Variants use different evidence contracts or witness semantics.
4. Variants require different algorithmic/objective families.
5. One part of the task is much broader or more visually varied than the rest.
6. The task is really combining multiple grounding jobs only because they share a theme.

## 8) Red flags
1. One prompt template repeated over a nearly fixed scene scaffold.
2. Tiny or collapsed scene/query diversity inside the task.
3. Evidence that is technically valid but not naturally grounded.
4. Variants that feel like separate tasks but were bundled for convenience.
5. Separate tasks that feel like one task split too finely.
6. Audit notes that contain a "review candidate" bucket for merely related
   tasks. Use `Keep`, `Merge`, `Split`, `Broaden`, `Retire`, or
   `Blocked Needs Inspection` instead.

## 9) Recommended audit process
1. Read the task doc, task module, prompt bundle, config, and recent review artifacts.
2. Summarize the task's actual scene variants, query ids, and evidence contract.
3. Judge the task against the rubric above.
4. Assign one outcome:
   - `Keep`
   - `Broaden`
   - `Merge`
   - `Split`
   - `Retire`
   - `Blocked Needs Inspection`
5. If merge/split is suggested, name the neighboring tasks or variants involved
   and cite which hard-boundary axes match or differ.
6. If tasks are related but fail a required merge condition, record `Keep` and
   state the failed axis rather than creating a review candidate.
7. Record concrete follow-up notes rather than abstract complaints.

## 10) Handoff format
For each audited task, record:
1. `Outcome`
2. `Why`
3. `Scene variety`
4. `Query variety`
5. `Grounding necessity`
6. `Evidence fit`
7. `Follow-up`

## 11) Repo-level use
1. Use this workflow before large benchmark expansions.
2. Use it when deciding whether a candidate should become a new task or only a new variant inside an existing task.
3. Use it when rebalancing the current task inventory toward cleaner uniform task-level sampling.

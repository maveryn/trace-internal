# TRACE Task-Unit Audit

Use this workflow when auditing whether a proposed or active TRACE task is the right unit for uniform task-level sampling.

Read `docs/core/TASK_UNIT_POLICY.md` first for the underlying definition of what should count as one TRACE task.

## 1) Purpose
1. Keep the TRACE task inventory aligned with the real sampling unit used at training time: one task id gets one share of sampling mass.
2. Ensure each task is a reasonably uniform visual-grounding problem rather than a loose theme bucket.
3. Catch tasks that should be broadened, merged, split, or retired before they distort benchmark balance.

## 2) Core principle
1. In TRACE, `task_group` is mostly an implementation and organization aid.
2. The important benchmark unit is the `task`.
3. A good TRACE task should therefore represent one stable visual-grounding family with enough internal scene/query variety to justify uniform sampling alongside the other tasks.
4. Tasks do **not** need equal reasoning difficulty.
5. Tasks **do** need roughly comparable within-task visual variety and grounding breadth.

## 3) What this audit should not penalize
1. A task may be text-heavy if the text must still be visually found/read from the image.
2. A task may be reasoning-heavy if the image is still genuinely required.
3. A task may be easy or hard; difficulty is not the main audit target here.

## 4) Task-unit rubric
Audit each task against the following questions.

### A. Uniform grounding family
1. Do the scene/query variants feel like the same kind of visual-grounding job?
2. Or is the task actually mixing multiple distinct grounding families under one task id?

### B. Within-task scene variety
1. Does the task have enough layout, arrangement, object-role, or scene-structure variety?
2. Is it more than one nearly fixed scaffold with superficial cosmetic change?

### C. Within-task query variety
1. Does the task have multiple query variants, or equivalent combinatorial diversity, within the same grounding family?
2. Would repeated samples from this task still expose the model to meaningfully different grounded questions?

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

## 6) Merge triggers
Consider merging tasks when most of the following are true:
1. Same or near-identical visual scaffold.
2. Same grounding pattern.
3. Same witness/evidence style.
4. Similar within-task variety.
5. Differences are mostly thin query wording or minor arithmetic/logical changes.

## 7) Split triggers
Consider splitting a task when one or more of the following are true:
1. Variants require different visual search patterns.
2. Variants use meaningfully different scene scaffolds.
3. Variants use different evidence contracts or witness semantics.
4. One part of the task is much broader or more visually varied than the rest.
5. The task is really combining multiple grounding jobs only because they share a theme.

## 8) Red flags
1. One prompt template repeated over a nearly fixed scene scaffold.
2. Tiny or collapsed scene/query diversity inside the task.
3. Evidence that is technically valid but not naturally grounded.
4. Variants that feel like separate tasks but were bundled for convenience.
5. Separate tasks that feel like one task split too finely.

## 9) Recommended audit process
1. Read the task doc, task module, prompt bundle, config, and recent review artifacts.
2. Summarize the task's actual scene variants, query variants, and evidence contract.
3. Judge the task against the rubric above.
4. Assign one outcome:
   - `Keep`
   - `Broaden`
   - `Merge`
   - `Split`
   - `Retire`
5. If merge/split is suggested, name the neighboring tasks or variants involved.
6. Record concrete follow-up notes rather than abstract complaints.

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

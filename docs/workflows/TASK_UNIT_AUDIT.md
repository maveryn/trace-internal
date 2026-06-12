# TRACE Task-Unit Audit

Use this workflow when auditing whether a proposed or active TRACE task is the right unit for uniform task-level sampling.

Read these policy docs first for the task-boundary rules:

1. `docs/core/TAXONOMY.md`
2. `docs/core/TASK_UNIT_POLICY.md`
3. the matching domain contract doc under `docs/domains/`

`docs/core/TASK_UNIT_POLICY.md` is the canonical source for program-contract
design. Inferred or generic program rows are draft-only; refine them before
approving any taxonomy decision.

Domain setup docs, task modules, prompts, configs, tests, and review artifacts
are factual inputs for what each task currently does. Repo-local skills are not
taxonomy policy sources for this audit. If a skill conflicts with the policy
docs above, ignore the skill for task-boundary decisions.

Naming rule: use **query id** as the human-facing term for task-internal
semantic branches and `query_id` as the canonical metadata field. `task_id` is
the public sampling unit.

## 1) Purpose
1. Keep the TRACE task inventory aligned with the real sampling unit used at training time: one task id gets one share of sampling mass.
2. Ensure each task is a reasonably uniform visual-grounding problem rather than a loose theme bucket.
3. Catch tasks that should be broadened, merged, split, or removed before they distort benchmark balance.

## 2) Core principle
1. In TRACE, the important benchmark unit is the public `task_id`.
2. The domain and scene are grouping/reporting axes.
3. A good TRACE task should therefore represent one stable visual-grounding family with enough internal scene/query variety to justify uniform sampling alongside the other tasks.
4. Tasks do **not** need equal reasoning difficulty.
5. Tasks **do** need roughly comparable within-task visual variety and grounding breadth.
6. Audits must use the hard task boundary in
   `docs/core/TASK_UNIT_POLICY.md`: stable scene contract plus stable
   `answer_schema`, `annotation_schema`, and concrete `program_schema`.
7. If any one of those task-contract fields differs between two active task ids,
   or if the scene/view contract would no longer be stable, the default
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

### E. Annotation fit
1. Is the public annotation/witness contract natural for the task?
2. Is the witness visually meaningful rather than degenerate, vacuous, or nearly identical to the final answer?
3. Does the annotation support the same execution trace as the answer?

### F. Branch balance
1. Do the branches within the task have roughly similar grounding breadth?
2. Is one branch much richer or more visually demanding than the others?
3. If one branch dominates the task's diversity while others are narrow, the
   task likely needs restructuring.

### G. Program-schema boundary
1. Does every query branch use the same program schema?
2. Is the program schema concrete enough to identify the candidate set,
   operand roles, derived computation, final operator, output binding, and
   annotation role template?
3. Are differences only mirror operators, thresholds, ordering choices,
   sampled slots, or local answer transforms over the same located support?
4. Or does a branch require a genuinely different reasoning program, such as
   shortest path vs longest path, traversal vs topological order, MST vs max
   flow, node removal vs edge removal, or option selection vs direct trace
   readout?
5. Do not keep a branch inside one public task if it changes answer schema,
   annotation schema, program schema, or query-facing view contract merely
   because it can be represented by a `query_id`.
6. For notation systems, rule-based puzzles, and other domain languages, audit
   the program schema at the shallowest level that preserves the required
   intermediate reasoning objects, not at the finest subroutine level.
7. Do not approve a taxonomy row whose program schema is only a generic
   placeholder such as `items`, `metric`, `condition`, or `predicate`.

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
1. The task is too weak, too degenerate, too redundant, or too awkward for TRACE annotation to justify keeping as a standalone task.

### Blocked Needs Inspection
1. The docs, code, prompt bundles, or sampled outputs are inconsistent enough
   that the task cannot be classified.
2. This label is not for tasks that merely share a scene or topic.
3. Name the exact missing or conflicting information needed to classify it.

## 6) Merge triggers
Recommend merging only when all of the following are true:
1. Same scene contract, including stable query-facing view contract.
2. Same answer schema.
3. Same annotation schema.
4. Same concrete program schema.
5. Differences are only query-parameter, mirror-operator, threshold, ordering,
   local answer-transform, or bounded rule-template parameters inside the same
   program schema.

Do not list a merge candidate because two tasks are conceptually related, share
the same scene, or share answer/annotation types. If one required merge condition
fails, classify the pair as `Keep`.

## 7) Split triggers
Consider splitting a task when one or more of the following are true:
1. Branches require different visual search patterns.
2. Branches use meaningfully different scene scaffolds.
3. Branches use different annotation contracts or witness semantics.
4. Branches require different program schemas.
5. One part of the task is much broader or more visually varied than the rest.
6. The task is really combining multiple grounding jobs only because they share a theme.

## 8) Red flags
1. One prompt template repeated over a nearly fixed scene scaffold.
2. Tiny or collapsed scene/query diversity inside the task.
3. Annotation that is technically valid but not naturally grounded.
4. Branches that feel like separate tasks but were bundled for convenience.
5. Separate tasks that feel like one task split too finely.
6. Audit notes that contain a "review candidate" bucket for merely related
   tasks. Use `Keep`, `Merge`, `Split`, `Broaden`, `Retire`, or
   `Blocked Needs Inspection` instead.

## 9) Recommended audit process
1. Read the task doc, task module, prompt bundle, config, and recent review artifacts.
2. Summarize the task's actual scene/style axes, query ids, and annotation
   contract.
3. Judge the task against the rubric above.
4. Assign one outcome:
   - `Keep`
   - `Broaden`
   - `Merge`
   - `Split`
   - `Retire`
   - `Blocked Needs Inspection`
5. If merge/split is suggested, name the neighboring tasks or branches involved
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
6. `Annotation fit`
7. `Follow-up`

## 11) Audit artifact format
Taxonomy-analysis artifacts should live under `review/taxonomy-audit/`, not
under `plans/`. Use one machine-readable row per current task/query branch
when possible, then summarize proposed task units per domain.

Recommended row fields:

1. `domain`
2. `scene_id`
3. `current_task_id`
4. `current_query_id`
5. `proposed_task_id`
6. `proposed_task_slug`
7. `scene_contract`
8. `view_contract`
9. `answer_schema`
10. `annotation_schema`
11. `program_schema`
12. `parameter_axes`
13. `program_arguments_json` — structured review metadata for argument values
    and variant axes inside the task; this does not replace `program_schema` as
    the hard task-boundary field.
14. `decision` — `keep`, `split`, `merge`, `rename`, `broaden`, `retire`, or
    `blocked_needs_inspection`
15. `merge_with` or `split_from`, when applicable
16. `rationale`
17. `notes`

During taxonomy analysis, classify the correct task boundary first. Do not
force merge/split choices to hit a target task count; fill count gaps later
with new approved scenes or tasks.

Before marking a taxonomy decision approved, verify that `program_schema` is
not an inferred/generic placeholder. If the current audit artifact only has a
generic skeleton, file a taxonomy issue or add a manual override with a
concrete program contract.

## 12) Repo-level use
1. Use this workflow before large benchmark expansions.
2. Use it when deciding whether a candidate should become a new task or only a
   query branch inside an existing task.
3. Use it when rebalancing the current task inventory toward cleaner uniform task-level sampling.

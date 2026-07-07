# TRACE Code Review Guidelines

Use this checklist for implementation, refactor, and pre-commit reviews. The
goal is to verify the source design, not to chase tests while hiding stale
contracts.

## Read First
1. `docs/README.md`
2. `docs/contracts/SYSTEM_ARCHITECTURE.md`
3. `docs/contracts/TAXONOMY.md`
4. `docs/contracts/TASK_UNIT_POLICY.md`
5. `docs/workflows/TASK_AUTHORING.md`
6. Relevant domain setup doc in `docs/domains/`
7. `docs/contracts/SOURCE_LAYOUT.md`

## Core Checklist
1. Scope is correct: changes stay in the assigned domain/scene unless shared
   infrastructure is genuinely required.
2. Public task ids follow `task_<domain>__<scene_id>__<objective_contract>` and
   stale task ids, aliases, disabled tasks, redirect docs, and compatibility
   wrappers are removed.
3. Public task files own objective/query logic, answer binding, annotation
   binding, task-specific prompt slots, task-specific trace fields, and final
   `TaskOutput` construction.
4. Scene `shared/` modules contain identity-free primitives only: state,
   sampling primitives, layout, rendering, projection, annotation helpers,
   validation helpers, or scene math/mechanics.
5. Shared code does not accept or branch on public `task_id`, `query_id`,
   objective contract, public task name, registered class name, or sibling task
   identity.
6. No wrapper-only public task files, copy-split legacy bodies, task-named shared
   runtimes, or shared multi-task generators remain in active scenes.
7. Helper placement is at the narrowest reusable layer that fits:
   `core -> tasks/shared -> domain/shared -> scene/shared -> task-local`.
   Promote only after real multi-consumer reuse or an approved domain shared
   boundary.
8. Prompt prose, examples, answer instructions, annotation instructions, and
   static wording live in prompt assets, not task modules.
9. Configs contain generation/rendering/prompt knobs only. They do not contain
   public objective dispatch, query routing, query weights, task coverage, or
   retired scalar difficulty gates.
10. Answer, annotation, projected annotation, trace witnesses, and prompt slots
    come from the same execution trace.
11. Public annotation uses active global annotation types and marks minimal
    visual answer-verification witnesses for the task family, not full proof
    traces. Use map annotation when witness role binding matters.
12. Verifiers consume metadata contracts and projections, not pixels.
13. Randomness is explicit, deterministic from seed/spec/version inputs, and
    recorded when it affects prompt, layout, rendering, answer, or annotation.
14. Semantic visual attributes do not accidentally correlate with answer value,
    query id, correct option, or construction order unless the task explicitly
    asks about that attribute.
15. Rendering changes preserve annotation coordinates: sample layout/style before
    projection and use only coordinate-preserving post-image noise.
16. Required/readout text and semantic markers use the shared legibility and
    contrast helpers or a documented domain wrapper. Text centered inside
    badges, circular markers, option chips, or node labels should use the
    shared bbox-aware centered text helper, not hand-written width/height
    offsets.
17. Tests cover behavior and contracts, not stale literal defaults or retired
    task ids.
18. Task docs, domain docs, prompt assets, configs, taxonomy metadata, tests, and
    review artifacts are updated together for the changed surface.
19. Review artifacts, when regenerated, live only under
    `review/task-reviews/<domain>/<scene_id>/<task_id>/`; reload the browser
    app index after artifact changes.
20. Reviewer issues remain open until human verification. Agents add repair
    notes after fixes and do not resolve issues unless explicitly instructed.

## Source-Layout Red Flags
1. A public task file only sets constants and calls a shared generator.
2. A scene shared helper receives `task_id`, `query_id`, or objective names.
3. A shared module computes final answers or `annotation_gt` for multiple public
   objectives.
4. Review artifacts were generated without current source, taxonomy, prompt,
   annotation, distribution, and focused-test checks.
5. Tests were weakened, allowlists expanded, or stale artifacts reused to make
   incomplete source ownership appear valid.

## Handoff
Report:
1. changed files;
2. task/scene ids affected;
3. tests and review commands run;
4. artifacts regenerated and app reload/restart status;
5. remaining blockers or human-review decisions needed.

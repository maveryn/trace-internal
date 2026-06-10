# Scene-Package Migration Shared Guidelines

This folder is the tracked source of truth for the scene-package migration.
Use it for domain-specific migration plans before editing domain code.

This document is the shared repo-specific contract for the migration effort. If
a domain plan conflicts with this file, fix the domain plan before
implementation.

Scene-level source layout and helper-role boundaries are specified in:

```text
docs/workflows/SCENE_PACKAGE_MIGRATION/SCENE_REFACTOR_GUIDELINES.md
```

Domain-specific scene layout guidance may further constrain that pattern. For
games, use:

```text
docs/workflows/SCENE_PACKAGE_MIGRATION/GAMES_SCENE_REFACTOR_GUIDELINES.md
```

## Migration Target

Public task identity is:

```text
domain -> scene_id -> task_id
```

Active task ids use:

```text
task_<domain>__<scene_id>__<objective_contract>
```

Each public task id maps to exactly one public task file:

```text
trace/tasks/<domain>/<scene_id>/<objective_contract>.py
```

Scene-local reusable code lives under:

```text
trace/tasks/<domain>/<scene_id>/shared/
```

Domain-level reusable code lives under:

```text
trace/tasks/<domain>/shared/
```

Cross-domain reusable code lives under:

```text
trace/tasks/shared/
```

After a domain is migrated, its task code, configs, prompt assets, docs, tests,
and generated records must not use `task_group` as a routing, metadata,
compatibility, or documentation concept.

TRACE now uses `annotation`, not `evidence`. New prompts, docs, review notes,
verifier payloads, rewards, and generated artifacts must use `annotation`,
`annotation_gt`, or `answer+annotation` terminology unless explicitly describing
historical migration debt.

## Role Boundary

The scene-package migration is not a path-only migration. The public task file must own the
task objective program. Shared modules may own reusable scene machinery, but not
public objective dispatch.

Migration must proceed scene-first inside one complete domain pass. During the
scene loop, keep reusable code at the scene-local `shared/` layer unless it is
already a clear, small, cross-scene utility. Do not try to design the final
domain shared layer while individual scenes still have copy-split or
wrapper-only task files. After scene-level objective ownership is fixed across
the domain, run a final domain-shared consolidation checkpoint before final
validation. That checkpoint is part of the same migration pass, not a separate
future refactor.

## Migration State Model

Use explicit migration states. Do not infer objective-complete status from a
scene merely being absent from a pending set.

1. Structurally routed: task files live under
   `trace/tasks/<domain>/<scene_id>/`, and runtime routing can find them.
2. Objective-ownership pending: the scene is structurally routed, but still
   needs the source/config/prompt/docs cleanup required by this migration.
3. Objective-ownership complete: the scene has passed the final checklist,
   enforcement tests, smoke generation, task-review refresh, and manual
   post-migration review.

Strict enforcement tests should target the explicit objective-complete scene
registry only. Existing scenes that were called complete under older policy
must be re-audited before entering that registry.

### Public Task File Owns

Each `trace/tasks/<domain>/<scene_id>/<objective_contract>.py` file should own:

1. the registered public task class;
2. objective-specific sampling and query parameter selection;
3. objective-specific target construction and semantic constraints;
4. final answer binding;
5. public `annotation_gt` construction, including role keys when needed;
6. task-specific dynamic prompt slot values and prompt metadata;
7. task-specific trace fields and validation checks;
8. calls into reusable scene helpers, without delegating the whole objective.

This means the task file should make the reader understand what question the
task asks, what objects are candidates, how the answer is selected, and what
annotation witnesses are expected.

### Hard Rule: Scene Shared Code Is Identity-Free

Scene-local shared code must not know which public task or query branch is
calling it. Passing public identity into shared code defeats the migration,
even if the file paths look correct.

Forbidden in `trace/tasks/<domain>/<scene_id>/shared/`:

1. accepting `task_id`, `query_id`, `supported_query_ids`, `objective_contract`,
   public task names, public query names, or registered class names as function
   arguments;
2. branching on public task ids, public query ids, objective-contract names, or
   registered class names;
3. exporting `SUPPORTED_*_QUERY_IDS` or similar public-query routing tables;
4. constructing samples with `sample_for_query(query_id)`,
   `sample_for_objective(objective_contract)`, or equivalent routers;
5. choosing answer semantics, annotation semantics, prompt semantics, target
   construction, or candidate construction from a public identity string.

Allowed:

1. public task files may pass already-resolved semantic arguments into shared
   helpers, such as `target_status="hit"`, `player="black"`,
   `option_count=6`, `target_ship`, `candidate_cells`, `hidden_fleet=True`, or
   a typed scene-state dataclass;
2. shared helpers may branch on semantic state that is intrinsic to the scene,
   such as a piece color, board direction, ship status, card rank, move
   direction, or render style, as long as those values are not aliases for
   public task/query identity;
3. global framework code outside scene-local `shared/` may carry public
   metadata for registry, taxonomy, prompt bundle lookup, and final record
   serialization. That metadata boundary must not be used to choose scene
   sampling, answer binding, or annotation binding.

If shared code needs `query_id` to decide what to do, the code is not shared.
Move the branch into the public task file and pass the semantic result into a
smaller shared helper.

### Hard Rule: Prompt Wording And Static Slots Are External

Prompt assets are the source of truth for user-facing wording. Migrated task
code must not contain prompt prose, static examples, answer hints, annotation
hints, rule descriptions, scene descriptions, or duplicated required prompt-key
tuples.

Prompt assets should own:

1. scene, task, query, and output templates;
2. static slots such as rule text, object descriptions, answer instructions,
   annotation instructions, and JSON examples;
3. required slot declarations;
4. dynamic slot declarations for values that task code must provide.

Task code may own:

1. prompt asset identifiers and selected template keys;
2. the task-local query branch, if the task has narrow query variants;
3. dynamic slot values derived from the generated scene, such as target labels,
   player colors, option labels, roll sequences, or selected object names;
4. the final call to the reusable prompt renderer.

Config may keep non-text prompt wiring such as bundle ids during migration, but
migrated scenes must move user-facing prompt prose out of ordinary domain YAML.
Prompt schema support for static slots, required slots, and dynamic slot
declarations is part of this migration. A scene cannot be marked complete while
it still depends on code-side required prompt-key tuples or config-owned prompt
prose as the source of truth.

### Hard Rule: Defaults Mirror Ownership

Fallback defaults must live at the same ownership layer as the behavior they
control. Do not use scene `shared/defaults.py` as a dumping ground for every
knob used by tasks in the scene.

Scene shared defaults may contain only values that define scene-wide grammar or
scene-wide reusable machinery, such as canvas dimensions, board size support,
style supports, global distractor-count bounds, renderer constants, and small
resolver fallbacks used by multiple objectives.

Public task files or task-specific config overrides must own fallbacks that
control one objective contract, including:

1. answer supports;
2. option-count supports for one visual-option task;
3. target-answer balancing axes;
4. target object supports that exist only for one task;
5. construction bounds used only to make one task's answer feasible.

If a fallback changes what one public task asks, how its answer is distributed,
or how its annotation witnesses are chosen, it is task-owned. If it changes the
shared visual scene grammar, it may be scene-owned.

Query branches are task-internal mirrors of the same objective contract. Their
supported ids belong in the public task file or a task-local module. Migrated
scene configs must not contain `query_id_weights`,
`query_variant_weights`, `balanced_query_id_sampling`, or equivalent query
sampling knobs in either `shared` or `task_overrides`.

Prompt required-key tuples are not task-owned fallbacks and should not be moved
from scene shared defaults into public task files. Prompt assets own required
slot declarations. Code-side required prompt-key tuples are migration blockers
for a completed scene, not acceptable final state.

### Scene Shared Owns

`trace/tasks/<domain>/<scene_id>/shared/` may own code reused by multiple tasks
in the same scene:

1. scene dataclasses and scene state;
2. board, chart, diagram, graph, page, or apparatus construction primitives;
3. legal-move, geometry, physics, graph, chart, or layout primitives;
4. reusable samplers that do not choose among public objectives;
5. renderers, style helpers, text helpers, marker helpers, and layout helpers;
6. annotation projection primitives and small annotation artifact builders;
7. validation helpers that check scene invariants.

Scene shared code can return scene state, candidate sets, render outputs,
primitive measurements, and reusable annotation fragments. It must not return a
complete `TaskOutput` for several public tasks.

Single current caller is not a violation. Identity-free scene primitives may
live in scene `shared/` when they are named by scene semantics and reusable in
principle. Do not move helpers into public task files solely because only one
current task calls them.

File size is not a migration gate. Split large shared files only when a real
role boundary is unclear or a file hides mixed responsibilities. Enforce role
boundaries and identity-free APIs, not arbitrary line-count limits.

### Domain Shared Owns

`trace/tasks/<domain>/shared/` is only for utilities reused by two or more
scenes in the same domain. It must not contain scene-local files, scene-named
dispatchers, or helpers that only one scene uses.

For migration work, treat domain shared as a final-checkpoint destination. A
helper should be promoted there only after at least two cleaned-up scene
packages use the same narrow primitive and the helper can be named without
referencing one scene's vocabulary. Premature promotion to domain shared is a
migration smell.

### Cross-Domain Shared Owns

`trace/tasks/shared/` is only for utilities that are genuinely cross-domain.
Before moving code there, confirm that at least two domains need it and that the
helper does not encode one domain's scene assumptions.

## Forbidden Migration Patterns

These patterns are scene-package migration failures even if source paths look correct:

1. wrapper-only public task files that subclass or call a shared source task;
2. public task files that differ only by task id, class name, or one constant;
3. sibling task files made by copying the same bundled module into every file;
4. a scene `shared/` module with a giant `if task_id/query_id/objective` block;
5. a shared module that branches over public objectives and returns complete
   `TaskOutput` objects;
6. a public task file that defines public task classes for sibling objectives;
7. a public task file that imports a `_SourceTask` or `_BaseTask` whose
   `generate()` method owns multiple public objectives;
8. compatibility aliases, disabled legacy tasks, or redirect task ids;
9. stale `task_group` routing kept "temporarily" inside migrated code;
10. prompt templates or generated records that still say `evidence`;
11. scene shared helpers that accept public `task_id` / `query_id` and use them
    as routing keys, even if the returned object is not a complete
    `TaskOutput`;
12. scene shared files that expose query-id support tables for public task
    files to select from instead of keeping query support local to the task
    file;
13. prompt prose, static prompt slot values, static JSON examples, answer
    instructions, annotation instructions, or rule text embedded in task
    modules or scene shared modules;
14. required prompt-key tuples duplicated in code when the prompt asset should
    declare required, static, and dynamic slots;
15. migrated scene configs that keep long user-facing prompt prose instead of
    referencing prompt assets and storing non-text generation/rendering knobs;
16. scene `shared/defaults.py` files that contain task answer supports, query
    weights, task-only option-count supports, or task-only feasibility bounds;
17. moving prompt required-key tuples from scene shared defaults into public
    task files instead of making prompt assets declare required slots;
18. migrated configs that contain `query_id_weights`, `query_variant_weights`,
    `balanced_query_id_sampling`, or equivalent query-sampling knobs anywhere
    in the scene config.

The correct boundary is extraction, not wrapping and not copy-splitting:

1. move reusable scene mechanics into the narrowest valid `shared/` layer;
2. keep objective-specific program code in each public task file;
3. merge tasks instead of making wrapper siblings if their objective programs
   cannot be separated without no-op files;
4. split tasks if one file would otherwise hide multiple answer, annotation, or
   program schemas.

## Domain Planning Requirements

Every domain must get a domain-specific plan in this folder before migration:

```text
docs/workflows/SCENE_PACKAGE_MIGRATION/<domain>.md
```

Each domain plan must be scene-by-scene and include:

1. current public task count and proposed public task count;
2. every active scene id;
3. every active task id in each scene;
4. each task's answer schema, annotation schema, and concrete program schema;
5. split/merge decisions with reasons;
6. old source modules and target source files;
7. what code belongs in scene `shared/`;
8. what code belongs in domain `shared/`;
9. configs to create, rename, or delete;
10. prompt assets to create, rename, or delete;
11. docs and task docs to update or delete;
12. task-review artifact paths to regenerate or purge when task ids change;
13. tests to add or update;
14. known blockers and pending scenes.

Do not start a domain implementation from only a task list. The plan must show
the objective ownership boundary for every scene first.

## Scene Migration Checklist

For each scene, do this in order:

1. Inventory the existing source modules, configs, prompt templates, docs,
   stale review artifacts, tests, and generated task ids.
2. Write the scene contract: visual grammar, object vocabulary, view contract,
   style/layout variation, and annotation projection assumptions.
3. Write one concrete task contract per proposed public task:
   answer schema, annotation schema, program schema, candidate set, operand
   roles, final operation, and annotation role template.
4. Decide split/merge before moving code.
5. Extract reusable scene mechanics into scene `shared/`.
6. Move objective-specific code into the public task file.
7. Delete retired task ids and old public modules; do not leave compatibility
   tasks.
8. Move config to `configs/domains/<domain>/<scene_id>.yaml`.
9. Move prompt assets to scene/task-aligned names and remove `task_group`
   assumptions. User-facing wording, static slots, examples, and required slot
   declarations belong in those prompt assets, not in task code or ordinary
   scene config.
10. Update taxonomy, registry imports, docs, task docs, tests, and review paths
    together.
11. Purge stale task-review folders owned by retired or renamed task ids.
12. Regenerate current task-review artifacts for changed active tasks under
    `review/task-reviews/` and reload the review app index.
13. Run scene/package enforcement tests and domain smoke tests.
14. Only then mark the scene complete in the domain plan.

After all scenes in a domain pass this checklist, do the final domain-shared
consolidation checkpoint before whole-domain validation:

1. compare cleaned scene-local `shared/` helpers for real duplication;
2. promote only narrow cross-scene primitives into domain `shared/`;
3. keep game-specific, board-specific, chart-specific, or renderer-specific
   helpers in their scene packages;
4. rerun the same enforcement tests so promotion does not recreate a dispatcher
   or wrapper anti-pattern.

## Enforcement Gates

The migration is not accepted until shared tests enforce these invariants for
the objective-ownership complete scenes in the migrated domain:

1. every active task id maps to exactly one file at the target source path;
2. each public task file defines exactly one active public task id;
3. public task files are not wrappers around shared multi-task generators;
4. sibling public task files are not exact or near-exact copies;
5. scene `shared/` modules do not branch over public objective contracts and
   return complete `TaskOutput` objects;
6. scene `shared/` modules do not define registered public task classes;
7. public task files do not define sibling public task classes;
8. domain `shared/` does not contain scene-local helpers;
9. migrated code/config/docs contain no active `task_group` references;
10. generated prompts and artifacts use `annotation`, not `evidence`;
11. configs are scene-keyed, not task-group-keyed;
12. retired ids, docs, configs, and review folders are deleted;
13. public task files do not import wrapper mixins, `_SourceTask` classes, or
    `_BaseTask.generate()` implementations that own sibling objectives;
14. sibling public task files are checked for normalized-AST or token-level
    near-duplicates, not only exact byte-size duplicates;
15. scene `shared/` modules do not import `TaskOutput`, define public task ids,
    or build final prompt/answer/annotation triples for multiple objectives;
16. scene `shared/` modules do not accept or branch on public `task_id`,
    `query_id`, `supported_query_ids`, `objective_contract`, public task names,
    or public query names;
17. query-id support constants stay in public task files or task-local modules,
    not in scene shared routing tables;
18. prompt wording, static prompt slots, JSON examples, answer instructions,
    annotation instructions, and required slot declarations are externalized in
    prompt assets; task code supplies only dynamic slots derived from generated
    state;
19. migrated scene configs contain no query-id weighting or balanced query
    sampling knobs; query branches are task-local and uniformly sampled unless
    controlled by explicit runtime params;
20. validation uses registry, taxonomy, docs inventory, smoke generation, and
    current task-review artifacts.

If a domain or scene has already been moved into the target path layout but
still violates objective ownership, mark it as pending in code and in the
domain plan. Do not call it migrated until the enforcement gates pass.

## Review And Retired Migration Surfaces

Task reviews remain part of migration acceptance. Task-complexity and
task-coverage surfaces are retired from this migration effort.

Task reviews:

1. Generate review artifacts for changed active tasks with
   `scripts/run_task_review.py --out-root review/task-reviews`.
2. Reload the review app index after `review/task-reviews/` changes.
3. If a task id is retired or renamed, delete its stale task-review folder when
   the owning domain pass reaches cleanup.
4. Migration acceptance comes from source ownership, registry/taxonomy/config
   consistency, prompt/annotation contracts, smoke generation, enforcement
   tests, and current browser-visible task-review artifacts.

Task complexity:

1. Do not preserve task-complexity scoring as a migration requirement.
2. Do not rename task complexity into another public field, metadata field, or
   calibration proxy.
3. Remove task-complexity config knobs, helper calls, metadata fields, and docs
   when migrating a scene or domain.
4. Do not introduce new complexity proxies while refactoring.
5. If complexity helpers remain temporarily because unmigrated code still calls
   them, treat them as cleanup debt and do not make public task files depend on
   them.

Task coverage:

1. Do not preserve task-coverage scoring, coverage-expansion bookkeeping, or
   benchmark-coverage summary code as a migration requirement.
2. Remove task-coverage config knobs, helper calls, generated summaries,
   migration gates, and docs when they are owned by the migrating scene or
   domain.
3. Do not replace task coverage with another per-task metadata proxy during
   scene-package migration.
4. If historical coverage plans remain for project context, keep them clearly
   outside active task/runtime/docs surfaces and do not let migrated task code
   import or emit coverage fields.

Core ABI scope:

1. The current repo may still expose `TaskComplexity`, `TaskOutput.complexity`,
   `TrainInstance.task_complexity`, curriculum complexity fields, and
   complexity-oriented scripts/tests while migration is in progress.
2. Those core ABI fields are global cleanup targets, not domain-specific
   concepts to preserve.
3. A domain pass should remove all domain-owned complexity builders, config
   knobs, prompt/doc mentions, and task trace metadata, and all domain-owned
   task-coverage builders, config knobs, active-doc claims, and trace metadata.
4. Do not add dummy zero-complexity builders to migrated task files just to
   satisfy the old ABI. If core still temporarily requires a value, keep the
   compatibility shim outside objective-owned public task files and mark it as
   global cleanup debt.
5. A domain is not fully migrated until its own active code/config/docs no
   longer depend on task-complexity semantics.

Calibration and solve-rate artifacts are also not part of structural migration
unless the user explicitly asks for a calibration run.

## Domain Plan Template

Use this structure for each domain plan:

```markdown
# <Domain> Scene-Package Migration Plan

## Status
- Current active task count:
- Proposed active task count:
- Migration state:
- Blockers:

## Domain-Level Shared Boundary
- Keep in trace/tasks/<domain>/shared/:
- Move out of domain shared:
- Cross-domain helper candidates:

## Scene Inventory

### <scene_id>
- Current task ids:
- Proposed task ids:
- Split/merge decision:
- Scene contract:
- Shared scene helpers:
- Task files:
  - <objective_contract>.py:
    - answer schema:
    - annotation schema:
    - program schema:
    - objective-owned logic:
- Config changes:
- Prompt changes:
- Docs/stale review cleanup:
- Tests:
- Risks:

## Retired Ids

## Validation Plan
- Scene/package enforcement checks:
- Smoke-generation checks:
- Active inventory/docs/taxonomy sync checks:
- Task-review regeneration and stale review-artifact cleanup:
- Core complexity ABI cleanup or temporary shim status:

## Open Questions
```

## Implementation Discipline

1. Work scene-local whenever possible.
2. Keep commits/review notes scoped to one domain migration pass.
3. Never use broad scripted rewrites that create wrapper files without checking
   objective ownership.
4. Prefer small reusable helpers over giant shared dispatchers.
5. Prefer task merge over wrapper siblings when objective code cannot be
   meaningfully separated.
6. Prefer task split when query branches change answer schema, annotation
   schema, program schema, or query-facing view contract.
7. Do not mark a domain migrated because imports pass. The code structure must
   express the taxonomy boundary.

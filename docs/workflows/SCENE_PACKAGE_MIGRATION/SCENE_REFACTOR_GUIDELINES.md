# Scene Refactor Guidelines For Scene-Package Migration

This is the domain-agnostic structure guide for refactoring one scene package.
It is tracked migration guidance under `docs/workflows/SCENE_PACKAGE_MIGRATION/`;
do not treat it as a permanent architecture document until the migration
settles.

Use this together with:

```text
docs/workflows/SCENE_PACKAGE_MIGRATION/README.md
docs/workflows/SCENE_PACKAGE_MIGRATION/DOMAIN_AUDIT_PLAYBOOK.md
docs/workflows/SCENE_PACKAGE_MIGRATION/<domain>.md
```

## Goal

Each scene package should make role boundaries obvious from the file layout.
The goal is not to introduce inheritance hierarchies or force object-oriented
patterns. Use plain functions and dataclasses unless a class has a real
cohesive responsibility.

The public task file must still own the objective program:

- objective-specific sampling choices;
- semantic target construction;
- final answer binding;
- final `annotation_gt` binding;
- dynamic prompt slots derived from the task state and task-specific trace
  fields.

Scene shared code may expose reusable machinery, but it must not hide public
task objectives behind a shared dispatcher.

## Identity-Free Shared Code

Scene-local `shared/` code must not accept public task/query identity. This is
a hard migration boundary, not a style preference.

Do not pass these into scene shared helpers:

- `task_id`;
- `query_id`;
- `supported_query_ids`;
- `objective_contract`;
- public task names;
- public query names;
- registered task class names.

Do not keep these in scene shared helpers:

- `SUPPORTED_*_QUERY_IDS` routing tables;
- `sample_for_query(...)` routers;
- `build_for_task(...)` or `build_for_objective(...)` dispatchers;
- branches that choose answer, annotation, prompt, target, or candidate
  construction from public identity strings.

Public task files may pass task-specific semantic arguments into shared
helpers. Examples: `target_status="hit"`, `player="black"`, `move_direction`,
`option_count`, `target_cells`, `candidate_boards`, `hidden_fleet`, or a typed
scene-state dataclass. The shared helper should process those semantic values
without knowing which public task or query produced them.

If a shared helper needs to inspect `task_id` or `query_id`, move that decision
back into the public task file and pass a semantic value to a smaller helper.

## Placement Rule

Place helpers at the narrowest correct reusable boundary:

```text
trace/tasks/<domain>/<scene_id>/<objective_contract>.py
trace/tasks/<domain>/<scene_id>/shared/
trace/tasks/<domain>/shared/
trace/tasks/shared/
```

During the scene-by-scene migration loop, default to scene-local shared code.
Do not promote new helpers to domain shared immediately. Instead, record
promotion candidates and revisit them after all scenes in the domain are
cleaned.

Promotion is a final domain checkpoint:

1. clean each scene locally first;
2. collect promotion candidates while working;
3. compare candidates after all scenes are objective-owned;
4. promote only helpers reused by at least two cleaned scenes;
5. rerun enforcement checks after promotion.

Premature promotion is a migration smell. It often creates fake abstractions
from one scene's needs and later reintroduces dispatcher-style code.

## Recommended Scene Package Shape

Different domains will need different exact filenames. The common pattern is:

```text
trace/tasks/<domain>/<scene_id>/
  <objective_contract>.py
  ...
  shared/
    defaults.py
    state.py
    mechanics.py
    sampling.py
    rendering.py
    prompts.py
    annotations.py
    output.py
```

Use only the files that make sense for the scene. Do not create empty
placeholder modules.

### `defaults.py`

Owns scene-level code fallback defaults only. YAML remains the source of truth.

Allowed:

- fallback generation supports that define shared scene grammar;
- fallback rendering dimensions;
- small fallback constants used by resolvers.

Not allowed:

- a second hidden copy of the scene config;
- task answer supports;
- option-count supports used by only one public task;
- target-answer balancing axes or feasibility bounds used by only one public
  task;
- query branch supports, query weights, or balanced query-sampling flags;
- user-facing prompt text, static prompt slots, or JSON examples;
- required prompt-key tuples or slot declarations that belong in prompt assets;
- runtime mutation of defaults;
- objective dispatch;
- broad `_TaskDefaults` dataclasses that obscure which values are fallbacks.

If a fallback changes one task's answer distribution, target sampling, option
count, or annotation witness set, keep it in the public task file or in
`task_overrides.<task_id>` config. If it changes the shared scene grammar or
renderer, it can stay in scene `shared/defaults.py`.

Query branches are not config-weighted in migrated scenes. Keep supported query
ids in public task files or task-local modules and sample them uniformly by
default. Do not keep `query_id_weights`, `query_variant_weights`,
`balanced_query_id_sampling`, or equivalent query-sampling knobs in migrated
scene config.

### `state.py`

Owns scene-local data contracts and intrinsic constants.

Allowed:

- dataclasses for scene state, query-neutral samples, render context, and rule
  results;
- type aliases;
- intrinsic constants, ids, and validation helpers;
- stable entity-id helpers.

Not allowed:

- answer binding for public tasks;
- prompt assembly;
- rendering side effects;
- config resolution.

### `mechanics.py`

Owns pure scene rules and transformations.

Allowed:

- board, graph, chart, apparatus, or layout rule primitives;
- legal move or geometric computation helpers;
- pure validators and derived relation functions.

Not allowed:

- public task objective selection;
- `TaskOutput` construction;
- prompt text or annotation payload assembly.

### `sampling.py`

Owns neutral construction primitives and axis resolution.

Allowed:

- config/default resolution helpers;
- random-axis resolution;
- scene-state construction primitives;
- candidate generation utilities that do not choose among public objectives.

Not allowed:

- functions named like `generate_<objective>_output`;
- `sample_scene_for_query(query_id)` if it branches over public objectives;
- receiving `query_id`, `supported_query_ids`, public query names, or task ids
  as routing inputs;
- final answer or annotation binding for multiple tasks.

### `rendering.py`

Owns scene rendering and renderer parameters.

Allowed:

- render parameter dataclasses;
- themes and style variants;
- renderer functions that return image, entities, and render map;
- calls into domain/shared style, layout, text, and marker helpers.

Not allowed:

- task answer selection;
- prompt assembly;
- verifier or reward payload construction.

### `prompts.py`

Owns thin prompt artifact assembly for the scene only when it stays
identity-free. Prompt assets own wording, static slots, examples, and slot
declarations.

Allowed:

- prompt asset lookup by scene/task/query template keys already selected by
  the public task file;
- merge of prompt-asset static slots with task-provided dynamic slots;
- prompt slot rendering through shared prompt infrastructure;
- prompt trace metadata.

Not allowed:

- hardcoded user-facing prompt text outside prompt assets;
- static prompt slot defaults in code;
- duplicated required prompt-key tuples or slot declarations in code;
- objective dispatch that hides task-specific prompt choices;
- prompt selection based on public `task_id` or `query_id` inside scene shared;
- `evidence` terminology in new prompts.

### `annotations.py`

Owns annotation projection primitives.

Allowed:

- mapping scene ids/entities to points or boxes;
- small artifact helpers for homogeneous annotation schemas;
- keyed annotation helpers where roles matter.

Not allowed:

- deciding which objects are the final task answer across public objectives;
- broad task-specific witness selection that belongs in a public task file.

### `output.py`

Owns generic output assembly only when it stays objective-neutral.

Allowed:

- convert already-bound answer, annotation, render context, prompt artifacts,
  and task trace fragments into `TaskOutput`;
- common trace sections shared by all tasks in the scene.

Not allowed:

- accepting or branching by public `task_id`, `objective_contract`, or
  top-level `query_id`;
- choosing the answer;
- choosing the annotation witnesses;
- returning complete outputs for several public objectives from shared
  functions.

If `output.py` starts deciding what an objective means, move that code back to
the public task file.

## Public Task File Shape

Each public task file should be readable as the task's objective contract.

If an existing public task id misstates the actual objective contract, rename or
merge it during the scene pass instead of preserving the stale id. For example,
`legal_move_count` should not remain the public task id for a task that also
samples hit or blocked destination predicates. Retired ids must be deleted, not
kept as aliases.

It should:

- define exactly one registered public task class;
- call scene shared helpers for state construction, mechanics, rendering,
  prompt assembly, annotation projection, and output assembly;
- keep objective-specific target construction and validation in the file;
- bind `answer_gt` and `annotation_gt` directly or through a narrow
  objective-local helper in the same file;
- pass only dynamic prompt slots derived from the generated task state into
  the prompt renderer;
- record task-specific trace fields.

It should not:

- subclass a multi-objective base task;
- call a shared full-output generator;
- import `FixedQueryVariantTaskMixin` or `QuerySubsetTaskMixin`;
- define sibling public task ids/classes;
- be a no-op wrapper around shared code.

## Promotion Candidate Notes

Every scene completion note should include a short promotion-candidate section.

Record candidates like this:

```text
domain shared candidates deferred:
- option-panel layout for 4/6 visual MCQ boards
- unit-size plus slack-based layout jitter plumbing
- panel scene background/style resolution
```

Do not move the helper during the scene pass unless it already exists at the
domain/shared or repo/shared layer and the scene can simply call it.

At the final domain checkpoint, promote only candidates that:

- appear in at least two cleaned scenes;
- have a scene-neutral name and API;
- do not mention one scene's vocabulary;
- do not branch by public task id, scene id, objective contract, or top-level
  query id;
- do not construct complete `TaskOutput` objects for multiple objectives.

Single current caller is not a reason to move an identity-free scene primitive
out of scene `shared/`. Keep helpers where their semantic ownership is clearest.

File size is not an acceptance gate. Split large files only when the role
boundary is unclear or mixed responsibilities make review harder.

## Migration Acceptance For One Scene

A scene is structurally clean when:

1. each public task file owns one objective program;
2. scene shared code is role-separated enough to inspect;
3. broad catch-all files like `task_support.py`, `tasks.py`, or
   `grid_tasks.py` are removed or split;
4. config defaults live in YAML, with visible code fallbacks only in
   `defaults.py`;
5. prompt schema support is upgraded as needed so prompt wording, static prompt
   slots, JSON examples, and required slot declarations live in prompt assets,
   while task code supplies only dynamic slots and template keys;
6. scene configs contain no `query_id_weights`, `query_variant_weights`,
   `balanced_query_id_sampling`, or equivalent query-sampling knobs;
7. generated prompts and payloads use `annotation`, not `evidence`;
8. scene-owned complexity and task-coverage code/config/docs/trace surfaces are
   removed, with no replacement difficulty or coverage proxy added during the
   scene pass;
9. review artifacts for changed active tasks are regenerated under
   `review/task-reviews/`;
10. a final post-migration review has been done after all code, config, docs,
   taxonomy, tests, and review-artifact updates. This review must re-check the
   final scene package as a whole for stale ids, wrapper-only task files,
   duplicated task logic in shared files, prompt/annotation terminology, retired
   artifact folders, and domain-shared promotion candidates;
11. the scene is added to the explicit objective-complete registry only after
   checks pass. Pending-scene removal alone is not a completion signal.

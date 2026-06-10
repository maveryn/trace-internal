# Domain Audit Playbook For Scene-Package Migration

Use this playbook before implementing a domain migration. The goal is to
understand the domain scene-by-scene, identify split/merge and role-boundary
issues, and produce a domain roadmap that can be implemented without wrapper
files or copy-split code.

This is a tracked migration document. The shared migration contract is:

```text
docs/workflows/SCENE_PACKAGE_MIGRATION/README.md
```

## Audit Output

Each audited domain should produce:

```text
docs/workflows/SCENE_PACKAGE_MIGRATION/<domain>.md
```

The domain roadmap must be scene-by-scene. Do not start implementation from a
flat task list.

## Audit Principles

1. Public taxonomy is `domain -> scene_id -> task_id`.
2. A public task is one stable scene contract plus one stable task contract.
3. Task contract means answer schema, annotation schema, and concrete program
   schema.
4. `query_id` is allowed only for narrow parameter/query axes inside the same
   task contract.
5. Scene-local shared code is the scene-loop target for reusable scene
   mechanics.
6. Domain shared is a final-checkpoint destination inside the same domain pass,
   after cleaned scenes reveal real cross-scene duplication.
7. A task file must own the objective program, not delegate it to a shared
   multi-task dispatcher.
8. New prompts, docs, verifier payloads, and reward payloads must say
   `annotation`, not `evidence`.
9. Migrated domain-owned files must not use `task_group` as routing, metadata,
   docs, or compatibility language.
10. Task-review artifacts remain part of migration acceptance; all
    task-complexity and task-coverage surfaces are retired migration surfaces.
    Audit review artifacts for regeneration/stale cleanup, and do not preserve
    complexity or coverage scoring or replace either one with a new proxy.

## Phase 1: Inventory

Collect the current domain state before making edits.

Recommended commands:

```bash
DOMAIN=games

find trace/tasks/$DOMAIN -maxdepth 2 -type f -name '*.py' | sort
find trace/tasks/$DOMAIN -maxdepth 3 -type f -path '*/shared/*.py' | sort
find configs/domains/$DOMAIN -maxdepth 1 -type f -name '*.yaml' | sort
find review/task-reviews/$DOMAIN -maxdepth 3 -type d | sort  # review regeneration/stale cleanup inventory
```

Build a scene/task source inventory:

```bash
DOMAIN=games
python - <<'PY'
from pathlib import Path
domain = "games"
root = Path("trace/tasks") / domain
scenes = []
for scene in sorted(p for p in root.iterdir() if p.is_dir() and p.name != "shared" and not p.name.startswith("__")):
    tasks = sorted(f.stem for f in scene.glob("*.py") if f.name != "__init__.py")
    if tasks:
        scenes.append((scene.name, tasks))
print("scenes", len(scenes))
print("task_files", sum(len(tasks) for _, tasks in scenes))
for scene, tasks in scenes:
    print(scene, len(tasks), ", ".join(tasks))
PY
```

Registry verification is required, but do not trust it blindly if imports are
known to be broken. Record whether it works:

```bash
DOMAIN=games
PYTHONPATH=. python - <<'PY'
import trace.tasks
from trace.tasks.registry import list_task_ids, list_default_task_ids

domain = "games"
ids = sorted(tid for tid in list_task_ids() if tid.startswith(f"task_{domain}__"))
default_ids = sorted(tid for tid in list_default_task_ids() if tid.startswith(f"task_{domain}__"))
print("registered", len(ids))
print("default", len(default_ids))
for tid in default_ids:
    print(tid)
PY
```

Record in the domain roadmap:

- source scene count;
- source task-file count;
- registered task count;
- default task count;
- mismatch between source and registry;
- import errors or missing import paths.

## Phase 2: Detect Shallow Migration Debt

Run static checks over public task files. The goal is to identify wrapper-only,
copy-split, sibling-task-class, and shared-dispatch patterns.

Suggested AST/source check:

```bash
DOMAIN=games
python - <<'PY'
from pathlib import Path
import ast

domain = "games"
root = Path("trace/tasks") / domain
print("scene\ttasks\tmulti_id_files\tsibling_id_files\tno_id_files\texact_size_groups")
for scene in sorted(p for p in root.iterdir() if p.is_dir() and p.name != "shared" and not p.name.startswith("__")):
    files = sorted(f for f in scene.glob("*.py") if f.name != "__init__.py")
    if not files:
        continue
    multi = []
    sibling = []
    no_id = []
    sizes = {}
    for path in files:
        text = path.read_text()
        sizes.setdefault(len(text.encode()), []).append(path.name)
        try:
            tree = ast.parse(text)
        except SyntaxError:
            multi.append(path.name)
            continue
        ids = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for stmt in node.body:
                if not isinstance(stmt, ast.Assign):
                    continue
                for target in stmt.targets:
                    if (
                        isinstance(target, ast.Name)
                        and target.id == "task_id"
                        and isinstance(stmt.value, ast.Constant)
                    ):
                        ids.append(str(stmt.value.value))
        expected = f"task_{domain}__{scene.name}__{path.stem}"
        if len(ids) > 1:
            multi.append(path.name)
        if not ids:
            no_id.append(path.name)
        if any(tid.startswith(f"task_{domain}__{scene.name}__") and tid != expected for tid in ids):
            sibling.append(path.name)
    exact = [names for names in sizes.values() if len(names) > 1]
    print(scene.name, len(files), len(multi), len(sibling), len(no_id), exact[:3], sep="\t")
PY
```

For each scene, classify:

- `clean_candidate`: source path exists and task files appear objective-owned;
- `copy_split`: sibling files are exact or near-exact copies;
- `wrapper`: public files only subclass/call a shared source task;
- `shared_dispatch`: scene shared code branches by task id/objective and
  returns complete task outputs;
- `multi_public_file`: one public task file defines sibling public task ids or
  sibling public classes;
- `registry_missing`: source exists but tasks are not registered;
- `task_id_unclear`: task id is inherited or assigned through constants in a
  way static checks cannot validate.

Required enforcement coverage for this phase:

- exact byte-size sibling duplicate detection;
- normalized-AST or token-level near-duplicate sibling detection;
- public task files that import `FixedQueryVariantTaskMixin`,
  `QuerySubsetTaskMixin`, `_SourceTask`, or a multi-objective base task;
- public task files that define more than one public task id or registered
  public task class;
- scene `shared/` modules that import `TaskOutput`;
- scene `shared/` modules that contain public task ids or branch on
  `task_id`, `objective_contract`, or top-level `query_id`;
- scene `shared/` modules that build final prompt, answer, and annotation
  together for more than one public objective.

## Phase 3: Scene Contract Audit

For every scene, write a short scene contract:

- visual grammar;
- visible object vocabulary;
- view contract;
- style/layout variation;
- annotation projection assumptions;
- scene-specific constraints that must stay shared.

Examples:

- board game scene: board topology, pieces, legal movement primitives,
  coordinate system, marker and annotation projection;
- card scene: deck/card representation, hand/tableau layout, rank/suit
  renderer, game-specific evaluator helpers;
- chart scene: plot grammar, mark types, axis semantics, panel layout, data
  generation helpers.

The scene contract should not describe task objectives. It describes what
scene-local `shared/` is allowed to own.

## Phase 4: Task Contract Audit

For every public task in the scene, write the task contract:

- answer schema;
- annotation schema;
- concrete program schema;
- candidate set;
- operand roles;
- final operation;
- annotation role template;
- allowed `query_id` axes;
- disallowed branches that would require a split.

Use concrete program schemas, not placeholders.

Bad:

```text
count matching objects
```

Good:

```text
count(destination_cells where legal_move(piece=marked_piece, move_type in {quiet,capture}))
```

Bad:

```text
select best option
```

Good:

```text
select(option_board where option_board == simulate_drop(board, fixed_piece, fixed_column, rotation=shown))
```

## Phase 5: Split/Merge Decision

For each scene, decide whether current public tasks should remain separate,
merge, or split.

Keep separate when any of these differ:

- answer schema;
- annotation schema;
- concrete program schema;
- query-facing view contract;
- candidate set;
- operand roles;
- final operation.

Merge only when:

- the same scene contract holds;
- the same answer schema holds;
- the same annotation schema holds;
- the same concrete program schema holds;
- branches are narrow parameters such as color, direction, threshold side,
  player side, rank mirror, or attribute choice.

Split when:

- one task mixes unrelated query views;
- annotation witness semantics change because the visual grounding job changed;
- a shared generator has one `query_id` branch per real objective;
- one branch counts objects and another selects an option;
- one branch produces a value and another produces an option label.

Record the decision in the domain roadmap with a reason, not only a task list.

## Phase 6: Role Boundary Plan

For each scene, write exactly what goes where.

Scene `shared/` may contain:

- dataclasses for scene state;
- renderer and style helpers;
- board/graph/chart/diagram topology primitives;
- legal move, scoring, formula, or geometry primitives;
- candidate enumeration helpers that do not choose a public objective;
- annotation projection primitives;
- validation helpers.

Public task files must contain:

- registered task class;
- task id;
- objective-specific sampling;
- target construction;
- answer binding;
- annotation binding;
- dynamic prompt slot construction and selected prompt template keys;
- task-specific trace payload.

Flag any proposed helper that would:

- accept `task_id`, `objective_contract`, or top-level `query_id` and return a
  complete `TaskOutput`;
- branch over public tasks;
- bind answer and annotation for several public objectives;
- make public files pure wrappers.

Those helpers must be redesigned before implementation.

## Phase 7: Config, Prompt, Docs, Complexity, And Stale Review Audit

For each scene, record:

- current config file;
- target scene config file;
- task overrides needed;
- fallback defaults currently in scene shared code, split into scene-owned
  grammar/rendering fallbacks versus task-owned answer/option/feasibility
  fallbacks that must move to public task files or `task_overrides.<task_id>`;
- query weighting config to delete. Migrated scenes must not retain
  `query_id_weights`, `query_variant_weights`, `balanced_query_id_sampling`, or
  equivalent query-sampling knobs in either `shared` or `task_overrides`;
- prompt templates to keep, rename, or delete;
- prompt prose, static slots, JSON examples, answer instructions, annotation
  instructions, and required slot declarations that must move into prompt
  assets;
- prompt asset schema upgrades required to make those prompt assets the source
  of truth for static and required slots;
- dynamic prompt slots that must remain task-owned because they come from the
  generated scene state;
- docs/tasks files to update or delete;
- task-complexity config/helper/metadata/doc references to delete, without
  replacing them with a new complexity proxy;
- task-coverage config/helper/metadata/doc references to delete, without
  replacing them with a new coverage proxy;
- task-review artifacts to regenerate for changed active task ids;
- stale task-review artifacts to purge for retired or renamed task ids;
- stale task ids or retired review folders.

Complexity and coverage cleanup have two scopes:

- Domain scope: delete domain-owned complexity and task-coverage config knobs,
  helper calls, metadata, task docs, generated active summaries, and prompt
  references during the domain migration.
- Global/core scope: remove `TaskComplexity`, `TaskOutput.complexity`,
  `TrainInstance.task_complexity`, curriculum complexity fields, and
  complexity-specific scripts/tests, plus active task-coverage code paths and
  docs, in a core cleanup pass. Until that pass is complete, do not put dummy
  complexity or coverage builders in migrated public task files; any temporary
  ABI shim must be isolated and marked as cleanup debt.

Search for prohibited terms:

```bash
DOMAIN=games
rg -n "task_group|evidence|complexity|coverage" trace/tasks/$DOMAIN configs/domains/$DOMAIN docs/domains docs/tasks
```

Also search migrated scene configs for query sampling knobs:

```bash
rg -n "query_id_weights|query_variant_weights|balanced_query_id_sampling" configs/domains/$DOMAIN
```

Interpretation:

- `task_group` is allowed only in historical migration notes or unmigrated
  domains, not in migrated domain-owned active surfaces.
- `evidence` is allowed only in historical migration notes. Prompt-facing and
  verifier-facing language should use `annotation`.
- `complexity` should not remain in migrated domain-owned active code, configs,
  task docs, or prompt/metadata contracts. Do not rename it into another
  difficulty/complexity proxy.
- `coverage` should not remain in migrated domain-owned active code, configs,
  task docs, or prompt/metadata contracts except in historical migration notes
  about retired coverage planning. Do not rename it into another coverage proxy.
- `query_id_weights`, `query_variant_weights`, and
  `balanced_query_id_sampling` should not remain in migrated scene configs.
  Query ids are task-internal mirrors and should be uniformly sampled from
  task-local support by default.
- Do not include `review/task-reviews` in the prohibited-term gate. Regenerate
  changed active task artifacts and purge only folders owned by retired or
  renamed task ids.

## Phase 8: One-Pass Implementation Readiness Gate

Do not implement a domain until the roadmap is executable as one complete
domain pass: preflight once, process every scene in a fixed order, run the final
domain-shared checkpoint, then run whole-domain validation.

Do not implement a scene until its roadmap section answers:

1. What is the scene contract?
2. Which public tasks remain after split/merge review?
3. What is each task's answer schema?
4. What is each task's annotation schema?
5. What is each task's concrete program schema?
6. What exact code belongs in scene `shared/`?
7. What exact code belongs in each public task file?
8. What code must not be promoted to domain shared yet?
9. What configs/prompts/docs and stale review artifacts need cleanup?
   Specifically, what prompt wording/static slots/slot declarations move into
   prompt assets, what prompt schema upgrade is needed, and what dynamic prompt
   slots remain in task code?
10. Which fallback defaults are truly scene-owned, and which task answer/
    option/feasibility fallbacks must move to task files or task-specific
    config overrides?
11. Where are query weighting configs removed, with query ids left task-local?
12. What tests prove this scene is not a wrapper or copy-split migration?
13. What smoke-generation, task-review regeneration, and inventory/doc-sync
    checks complete the scene?

If these are not answered, the domain plan is not ready.

## Phase 9: Final Domain-Shared Checkpoint

After every scene in the domain is clean, but before final whole-domain
validation:

1. Compare scene-local `shared/` helpers for true duplication.
2. Promote only narrow, scene-neutral helpers to domain `shared/`.
3. Keep scene-specific renderers/rules in scene `shared/`.
4. Update imports and docs.
5. Rerun enforcement tests.
6. Confirm no domain shared helper has become a task dispatcher.

This is the only point where broad domain shared cleanup should happen. Do not
do it while scenes are still copy-split. This is still part of the same
migration pass, not a later optional cleanup.

## Domain Roadmap Checklist

Each domain roadmap should contain:

- Status
- Non-negotiable gates
- Preflight fixes before scene loop
- Domain shared boundary
- Current debt summary
- One-pass execution model
- Preflight fixes before scene loop
- Scene loop
- Per-scene roadmap
- Retired complexity/coverage cleanup and task-review refresh
- Final domain-shared checkpoint
- Whole-domain validation plan
- Smoke-generation and task-review refresh
- Active inventory/docs/taxonomy sync checks
- Core complexity ABI cleanup note, if the domain still depends on the old
  core field shape
- Completion criteria

Each scene section should contain:

- task list;
- current risk classification;
- shared scene helpers;
- per-task objective ownership;
- split/merge decisions;
- config/prompt/docs/complexity/coverage cleanup;
- task-review regeneration/stale cleanup;
- tests/checks.
- smoke-generation expectations, if scene-specific runtime checks are needed.

## Acceptance Criteria

A domain audit is complete when:

1. every active scene is listed;
2. every active task is listed under exactly one scene;
3. every scene has a risk classification;
4. every task has answer, annotation, and program schema documented or marked
   blocked for inspection;
5. every split/merge decision is justified;
6. scene-local vs domain-shared boundaries are clear;
7. implementation can proceed scene-by-scene without inventing wrapper files;
8. prompt schema upgrade needs are identified, not deferred outside migration;
9. query weighting config removal is planned for migrated scenes;
10. the plan names smoke-generation, task-review regeneration, inventory, docs,
   and taxonomy checks.

# Pages Shared Boundary

Use this with `SCENE_MIGRATION_GUIDE.md` when migrating a pages scene.

## Purpose

The pages domain exposes public taxonomy as:

```text
pages -> scene_id -> task_id
task_pages__<scene_id>__<objective_contract>
```

The source layout is only partially aligned with that taxonomy. Several public
pages scenes still depend on broad implementation packages such as `counting`,
`relation`, `cross_form`, `arithmetic`, and `infographic`.
Those folders are not public taxonomy nodes. They are legacy implementation
surfaces that must be decomposed as scene packages migrate.

Scene-package migration must separate three layers:

- true pages-domain primitives reused by unrelated page scenes;
- one scene's page grammar, layout, rendering, and reusable scene primitives;
- public task objective code that owns query selection, answer binding,
  annotation binding, prompt slots, trace fields, and final `TaskOutput`.

During migration, each public scene gets its own package under:

```text
trace/tasks/pages/<scene_id>/
```

## Boundary Context

Use `docs/ACTIVE_TASK_INVENTORY.md` and `docs/tasks/pages/` for active pages
scenes and task ids. Record scene-specific migration findings in review
artifacts, not in this shared-boundary policy.

Pages includes several visual scaffold families: calendars, schedules, forms,
records, workspaces, command surfaces, maps, process flows, concept maps,
hierarchies, schemas, timelines, ranked lists, cards, and infographics. Shared
layout mechanics across those families do not create another public taxonomy
axis.

## Domain Shared

`trace/tasks/pages/shared/` is for pages-domain helpers reused by multiple
unrelated scenes. Domain shared code must be scene-neutral and identity-free.
It must not know or branch on public task ids, public query ids, objective
contracts, registered task classes, sibling scene identities, task-specific
answer schemas, or task-specific prompt wording. It must not construct final
public `TaskOutput`.

Approved domain-shared categories:

- short controlled text pools, label assets, and text-generation helpers;
- text fitting, wrapping, and legibility primitives;
- page palette, font, control-style, and visual-default helpers;
- scene-neutral semantic asset pools for fields, sections, controls, statuses,
  icons, people, events, and metrics;
- low-level page geometry, bbox, point, and placement helpers;
- generic annotation artifact adapters when repo-global helpers are not already
  sufficient;
- small reusable render primitives for page chrome, controls, tables, cards,
  section headers, and text blocks, provided they do not choose scene semantics;
- render-audit defaults that apply across unrelated pages scenes.

Domain-shared modules that should generally remain domain-shared:

| Module | Target role |
|---|---|
| `legible_text.py` | Scene-neutral text fitting, wrapping, and font sizing. |
| `text_generation.py` | Controlled short text generation utilities. |
| `page_text_resources.py` | Shared page label and short-text resources. |
| `page_semantic_assets.py` | Shared page entity, status, control, and field vocabularies. |
| `page_visual_assets.py` | Reusable visual glyphs or assets that are not tied to one scaffold. |
| `visual_defaults.py` | Shared visual defaults for pages rendering. |
| `information_style.py` | Shared style resolution for information-dense pages. |
| `gui_render_params.py` | Neutral GUI/control render parameter helpers. |
| `gui_chrome.py` | Scene-neutral GUI chrome, theme, badge, and control drawing primitives reused by GUI-like page scenes. |
| `sampling.py` | Scene-neutral named-axis and integer-support sampling resolvers reused by migrated page scenes. |
| `render_audit_defaults.py` | Cross-scene render-audit defaults. |

Domain-shared modules that should move to scene-local shared when their owning
scene is migrated:

| Module | Scene-local target |
|---|---|
| `calendar_scene.py` | May remain domain-shared while it is used by both `calendar` and `calendar_event_grid`; move scene-local only if that cross-calendar reuse ends. |
| `schedule_scene.py` | `trace/tasks/pages/schedule/shared/{state,layout,rendering,annotations,prompts,output,sampling}.py` as needed. |
| `timeline_scene.py` | `trace/tasks/pages/timeline/shared/{state,layout,rendering,annotations,prompts,output,sampling}.py` as needed. |
| `document_scene.py`, `document_common.py`, `sectioned_document_common.py` | Scene-local shared packages for document-derived public scenes such as `sectioned_infographic`, `profile_card_grid`, or another owning scene. |
| `reconciliation_scene.py`, `reconciliation_common.py` | `trace/tasks/pages/paired_forms/shared/{state,layout,rendering,annotations,prompts,output,sampling}.py` as needed. |
| `arithmetic_common.py` | The owning arithmetic/form scene's local `shared/`, unless a pure arithmetic helper is proven reusable across unrelated pages scenes. |
| `infographic_metric_common.py`, `infographic_metric_dataset.py`, `infographic_metric_rendering.py` | Temporary identity-bound legacy runtime for the migrated `infographic` scene. Move to role-named scene-shared files only after source branch strings are split from public objective names. |
| `diagram/hierarchy_common.py`, `diagram/hierarchy_scene.py` | Temporary identity-bound legacy runtime for the migrated `hierarchy` scene. Move to role-named scene-shared files only after source branch strings are split from public objective names. |

Domain-shared modules that should be retired from migrated scenes:

| Module | Reason |
|---|---|
| `public_query_task.py` | Output rewriting is legacy public-query plumbing. Migrated public task files should produce public task/query metadata directly. |

## Shared Information Styles

Pages uses the shared structured-information style family for scenes with
calendar, table, form, metric, infographic, or dashboard-like surfaces. The
Pages baseline is configured in `configs/domains/pages/base.yaml` and mirrors
the Charts inventory: 25 treatment ids, consisting of 20 light treatments and 5
dark treatments, plus shared palette and chrome weights.

Migrated scenes should resolve these styles through
`trace/tasks/pages/shared/information_style.py` when the scene uses
non-semantic page chrome, panel colors, header colors, guide lines, or
background treatments. Scene renderers may translate shared roles into a
scene-specific theme object, such as a calendar theme, but they should record
the resolved `information_scene_style` metadata in the trace and avoid
parallel local axes such as separate light/dark style samplers unless a
task-specific reason is documented.

All active Pages tasks must honor forced `information_scene_treatments`,
including dark treatments, through their scene renderer or the domain wrapper.
The Pages render-audit wrapper records the selected style for every task and
applies fallback outer chrome for legacy scenes that do not yet translate the
style into their internal page grammar. New scene-package renderers should
prefer first-class style mapping over relying on fallback chrome.
The first-class GUI/control rollout covers `control_board`, `navigation_flow`,
`web_action`, and `workspace`: those scenes should resolve
`information_scene_style`, translate it into scene-local chrome roles, and avoid
reintroducing separate `style_variant` or light/dark sampling axes for palette
changes.

The wrapper should also use the resolved `information_scene_style` roles for
shared context text, side notes, and paragraph distractors whenever that
metadata is present. Explicit task parameters for context colors may override
this, but default distractor/context text should not keep light-theme colors on
dark treatments.

Pages context text should use the same profile/mode contract as Charts. The
canonical defaults live in `rendering.shared` as `pages_context_profile`,
`pages_context_mode_weights`, and `pages_context_mode_configs`. Use
`dense_clean_minimal` when a scene should only have clean/minimal safe-margin
text, and opt into `report_paragraph` only when the scene has enough stable
empty space for paragraph-style side-note distractor boxes. Legacy
`visual.context_text` and `pages_context_density*` keys should not be added to
new scene configs.
If a report-paragraph scene has a broad page, panel, timeline, or diagram box
that is background rather than a witness, set `render_spec.context_text_policy`
so shared context placement can use that interior whitespace while still
blocking overlap with event, node, field, row, and other witness boxes.

## Scene Shared

`trace/tasks/pages/<scene_id>/shared/` owns one scene's page grammar and
reusable scene primitives.

Recommended pages scene-shared role files:

- `state.py`
- `defaults.py`
- `sampling.py`
- `layout.py`
- `rendering.py`
- `annotations.py`
- `prompts.py`
- `output.py`
- `styles.py`
- `assets.py`
- `labels.py`
- `fields.py`
- `sections.py`
- `controls.py`
- `tables.py`
- `forms.py`
- `cards.py`
- `calendar_math.py`
- `routes.py`
- `nodes.py`
- `edges.py`
- `relations.py`
- `metrics.py`
- `option_rendering.py`

The matching scene-package file policy should allow only role files like these
inside a scene `shared/` package, plus `__init__.py`, and should allow only
`_lifecycle.py` as a private scene-root file. Shared subdirectories should stay
disabled unless a later scene has a documented need for a narrower package.

Scene shared may know its visual grammar: a calendar grid, day planner, form
section, record table, workspace, map, process flow, concept
map, schema diagram, timeline, card grid, ranked list, or infographic page. It
must not route behavior by public task id, public query id, objective contract,
public task name, or registered class.

Scene shared must not:

- accept or branch on public `task_id`;
- accept or branch on public `query_id`;
- export public query-id routing tables;
- register public tasks;
- construct final public `TaskOutput`;
- contain task-named runtime files;
- hide copied public task bodies.

If a helper needs to know which public query branch is running, the public task
file should resolve the branch to neutral semantic arguments and pass those
arguments into shared code.

Example:

- Bad shared argument: `query_id="disabled_controls_in_group_count"`.
- Good shared arguments: `control_state="disabled"`,
  `group_name="Export tools"`, `candidate_controls=[...]`.

## Public Task Files

Each public task file owns one objective contract:

- literal public `TASK_ID`;
- `SCENE_ID`;
- local `SUPPORTED_QUERY_IDS`;
- query selection and query validation;
- objective-specific target, candidate, or route construction;
- answer binding;
- `annotation_gt` binding;
- dynamic prompt slots and prompt/query key selection;
- task-specific trace fields;
- retry and final `TaskOutput`.

Public task files may call scene-shared and domain-shared primitives. They must
not delegate objective behavior to a shared base task whose subclasses differ
only by class attributes, forced query ids, scene ids, or task ids.

## Annotation And Prompt Policy

Pages annotations should mark the minimal visible witnesses:

- field/value tasks: the decisive field, value, row, card, or section region;
- count tasks: the matching controls, rows, events, items, nodes, or regions;
- route/path tasks: start, target, route steps, landmarks, or selected endpoint;
- process/schema tasks: source node, target node, row, edge, or relationship;
- option-image tasks: the selected visual option image or source region.

Use scalar `bbox` or `point` when a task always has exactly one visual witness.
Use a set only for multiple unordered homogeneous witnesses. Use keyed maps
when witness roles matter, such as `source_field` vs `target_field`,
`start` vs `end`, `input` vs `output`, or `reference` vs `candidate`.
For zero-count tasks, an empty set is allowed when the queried witness set is
empty.

Prompts should name the queried field, section, event, control, route, node, or
step explicitly. Avoid hidden page-layout conventions and avoid irrelevant
rendering details such as "unlettered" unless they are part of the task
contract. Context text and distractor labels must be short, non-answering, and
visibly separated from the queried elements.

## Config And Prompt Migration

Scene-package migration should create or update one config per public scene:

```text
configs/domains/pages/<scene_id>.yaml
```

Broad legacy config files such as `counting.yaml`, `relation.yaml`, and
`cross_form.yaml` are implementation-era grouping files. Do not use them as
public migration boundaries. Retire them when their active public scenes have
scene-scoped configs.

Prompt bundles should also be scene-scoped:

```text
prompts/pages/<scene_id>/pages_<scene_id>_v1.json
```

Task modules must not hardcode user-facing prompt prose. Public task files own
prompt slot values and template key selection; prompt text itself belongs in
prompt assets.

## Legacy Surfaces To Audit

During pages scene migration, audit these surfaces before making a scene
review-candidate:

- broad source packages such as `counting`, `relation`, `cross_form`,
  `arithmetic`, and `infographic`;
- shared runtime files that construct final public outputs or select public
  query ids;
- public task files that rewrite internal outputs into public task/query ids;
- multi-public-task modules that should become one public task file per
  objective contract;
- broad config or prompt bundles that do not match the public scene id.

Migration should replace legacy routing with scene-owned public task files.
Do not keep compatibility wrappers, disabled legacy tasks, redirect docs, or
stale review folders for retired public ids.

## Review-Ready Definition

A pages scene is review-ready only when:

- public task files own objective behavior and final output construction;
- scene shared files are role-named and identity-free;
- domain shared helpers are scene-neutral and demonstrably reused;
- prompt prose comes from prompt assets;
- answer and annotation come from the same execution trace;
- every supported query branch smoke-generates;
- scene-scoped migration tests pass;
- manual source audit and taxonomy audit status files pass;
- fresh review artifacts exist under `review/task-reviews/`;
- the review app index has been reloaded.

Human acceptance in the browser app is still required before calling the scene
migrated.

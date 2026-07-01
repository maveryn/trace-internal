# Post-Migration Domain Checklist

Use this checklist after a domain has been migrated scene-by-scene and the
browser app shows human review passed for every active task in the domain.
This is a post-migration quality pass. It does not replace the per-scene
migration gates in `SCENE_MIGRATION_GUIDE.md`.

The goal is to confirm that the domain is coherent as a full collection:
task/query taxonomy, prompt conventions, annotation contracts, distribution
checks, rendering policy, and generated review artifacts should all agree.

## Read-Only Rule

This checklist is an audit/reporting pass. Do not change source code, configs,
prompt assets, task docs, review artifacts, review-app state, or human review
status while running it.

Allowed outputs are report files under:

```text
docs/domain-migration-report/<domain>/
```

If the audit finds a required fix, record it in the report. Make the fix in a
separate user-approved implementation task, then rerun the relevant scene
migration gates and review artifacts as that separate task.

## Inputs

Before starting, collect:

- the domain name;
- the active task count from `docs/ACTIVE_TASK_INVENTORY.md`;
- the scene list from `trace/core/scene_package_migration.py`;
- the domain contract doc under `docs/domains/`;
- scene review artifacts under `review/task-reviews/<domain>/`;
- browser app human review status for every active task;
- solve-rate status, if the user asks to include solve-rate acceptance;
- report directory:
  `docs/domain-migration-report/<domain>/`.

Do not call a domain accepted only because this checklist passes. Migration
acceptance still requires human review and migration receipts as described in
`RECEIPT_SCHEMA.md`.

## Automated Gates

Run these first. Any failure becomes a concrete issue to fix or inspect.
Do not repair failures during this pass.

### Inventory And Registry

```bash
PYTHONPATH=. python scripts/generate_active_task_inventory.py --check
PYTHONPATH=. python scripts/check_active_inventory_integrity.py --include-local-cache
PYTHONPATH=. python scripts/audit_active_domain_surfaces.py
```

Check:

- registered task count equals default task count;
- every active task id follows
  `task_<domain>__<scene_id>__<objective_contract>`;
- every active task has a taxonomy mapping;
- active docs/configs/prompts do not mention retired public task ids;
- no stale compatibility alias or disabled legacy task remains.

### Scene Migration Status

For every scene in the domain:

- `manual_code_audit_status.json` exists and has `passed: true`;
- `taxonomy_review_status.json` exists and has `passed: true`;
- `taxonomy_review_status.json` includes every active task id in the scene;
- `taxonomy_review_status.json` has
  `checklist.scalar_annotation_checked: true`;
- `migration_test_status.json` exists and has `passed: true`;
- the required scene-scoped migration command is recorded;
- generated review artifacts are newer than the last source/config/prompt/doc
  change for that scene.

For a spot check or rerun on one scene:

```bash
TRACE_SCENE_PACKAGE_REVIEW_SCENE=<domain>/<scene_id> \
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q \
  tests/test_review_app.py \
  tests/test_run_task_review.py \
  tests/test_scene_package_migration_contracts.py \
  tests/test_scene_package_review_candidate_contracts.py
```

### Distribution Review

For every active task:

- `distribution_review.json` exists under the task review folder;
- the distribution review status is accepted/passing according to the current
  review runner output;
- every supported `query_id` appears in generated samples;
- answer supports are covered well enough for the configured review sample
  size;
- no query branch silently fails generation or has extreme rejection;
- distribution failures are recorded as follow-up generation-logic issues, not
  hidden by changing review artifacts.

If distribution artifacts are missing or stale, regenerate only after all
scene-level migration gates still pass. Regeneration and app reload are not
part of this report-only checklist; record the stale/missing artifact as a
follow-up implementation/review task.

### Annotation Bbox Size

Every bbox-family annotation witness must have width and height at least
`24px`.

```bash
PYTHONPATH=. python scripts/audit_review_bbox_min_side.py \
  --domains <domain> \
  --min-side-px 24 \
  --out-json docs/domain-migration-report/<domain>/bbox_min_side_audit.json \
  --out-md docs/domain-migration-report/<domain>/bbox_min_side_audit.md \
  --fail-on-issue
```

This applies to `bbox`, `bbox_set`, `bbox_sequence`, `bbox_map`, and
`bbox_set_map`. If a true witness is smaller or thinner, expand a centered bbox
only when it remains unambiguous. Otherwise redesign the rendering or use the
correct point/segment-family annotation.

### Sampling And Modulo Audits

Semantic randomness must use explicit supports/ranges and seeded RNG helpers.
It must not use modulo, hash index, cursor cycling, or deterministic
enumeration.

```bash
PYTHONPATH=. python scripts/audit_semantic_sampling_modulo.py \
  --root trace/tasks/<domain> \
  --root trace/core \
  --output docs/domain-migration-report/<domain>/semantic_sampling_modulo_audit.md

PYTHONPATH=. python scripts/audit_visual_candidate_modulo.py \
  --root trace/tasks/<domain> \
  --root trace/core \
  --output docs/domain-migration-report/<domain>/visual_candidate_modulo_audit.md
```

Review every `needs_refactor` and `needs_manual_review` finding. Visual modulo
is allowed only for deterministic assignment from an already-sampled candidate
set, such as cycling through a chosen palette because there are more rendered
objects than available colors.

### Prompt Concision And Annotation Contract Smoke

Run targeted prompt audits for the domain:

```bash
PYTHONPATH=. python scripts/audit_prompt_concision.py \
  --tasks <comma-separated-domain-task-ids> \
  --query-id-coverage \
  --samples-per-query-id 1 \
  --include-all-prompts \
  --output docs/domain-migration-report/<domain>/prompt_concision_audit.md

PYTHONPATH=. python scripts/audit_prompt_annotation_contracts.py \
  --tasks <comma-separated-domain-task-ids> \
  --samples-per-query-id 1 \
  --output-dir docs/domain-migration-report/<domain>/prompt_annotation_contracts
```

Use the output as review input, not as a replacement for manual prompt review.

## Manual Domain Review

Perform these checks scene-by-scene and task-by-task in the browser app. Record
findings as reviewer issues or in the domain post-migration report.

## Taxonomy And Program Schema

For every task, verify:

- the public task is one stable scene contract plus one stable objective
  contract;
- answer schema, annotation schema, and program schema stay fixed across all
  query ids;
- the task doc has a concrete `## Program Contract`;
- the program code names the candidate set, filters, operand roles,
  aggregation/comparison/rank/arithmetic operation, output binding, and
  annotation witness roles;
- program code is not a vague placeholder such as `count(objects)` or
  `select_by_rank(items)`;
- query ids are semantic branches of one objective, not public objectives in
  disguise.

Valid query branches change how or where the model must answer while preserving
the core reasoning pattern. Common valid examples:

- `largest` / `smallest`;
- `earliest` / `latest`;
- `above` / `below`;
- `inside` / `outside`;
- `left` / `right`;
- `inner` / `outer`;
- source versus target role, when that role is prompt-facing;
- first versus last endpoint, when that role is prompt-facing.

For rule-driven domains such as games, a color/player/name may be a valid
query axis when it is a prompt-facing role in the rule system rather than a
pure visual operand. Keep such branches when the queried side changes legal
movement, capture/friendly-opponent relations, goal direction, win/loss
predicate, board-state classification, or threat/completion predicate. For
example, "boards won by X", "boards where O has a winning move", or "pieces
of the active player that can capture" are rule predicates, not simple color
filters.

Invalid query branches include:

- object names, color names, labels, category names, or numeric thresholds when
  those are simply resolved prompt slots;
- style, palette, font, layout, board skin, or renderer preset;
- exact same prompt template where only a sampled object/color/label slot
  changes;
- branches that change answer schema, annotation schema, candidate type,
  witness role structure, or visual scaffold.

Single-query tasks must use `query_id="single"` and
`supported_query_ids=("single",)`.

## Prompt Review

For every task/query prompt:

- the question asks exactly for the generated answer contract;
- the answer hint names the task-specific value, not only the answer range;
- the annotation hint matches the generated annotation type and witness role;
- annotation hints and examples use canonical coordinate variable names:
  `bbox` values are `[x0, y0, x1, y1]`, where `(x0, y0)` is the top-left
  corner and `(x1, y1)` is the bottom-right corner; `segment` values are
  `[[x0, y0], [x1, y1]]`, where the nested arrays are the two endpoints;
- prompt examples are valid for the answer and annotation schema;
- prompt examples do not use one-item arrays for scalar annotation;
- active prompt text uses `annotation`, not retired grounding wording;
- prompt text does not expose hidden sampling internals, task ids, query ids,
  construction modes, or trace fields;
- prompt text is not overly verbose or repetitive;
- the opening prompt sentence describes only task-relevant scene context and
  must not list renderer/style trivia that is not needed to answer the
  question;
- prompt text does not leak answer ranges when the range is not useful task
  information;
- prompt text does not include generic output-protocol boilerplate that belongs
  in the shared/system layer;
- prompt annotation wording may include narrow set-boundary exclusions only
  when they define the requested witness set, such as excluding a source/start
  node from a path or reachability annotation;
- if the prompt names a marker color or style, the renderer always uses that
  primary color/style for the semantic cue.

Treat non-canonical coordinate notation in active task prompts as a
high-severity post-migration issue. Do not use `[x1, y1, x2, y2]` for bboxes
or `[[x1, y1], [x2, y2]]` for segments. These shapes are often parseable, but
they conflict with the repo-wide annotation contract and make prompt/reward
review inconsistent. Pixel-space wording is supplied by the shared/system
prompt layer, so task prompts do not need to repeat that coordinates are pixels
unless the task-specific wording would otherwise be ambiguous.

If two query ids have the same prompt scaffold and only substitute a sampled
object, color, category, or label, they should usually be generation metadata,
not query ids. The exception is a documented rule-role substitution where the
substituted value changes the rule predicate being evaluated, not just which
visible category is counted.

Flag decorative renderer descriptions as prompt defects. A first sentence such
as "The image shows a zebra-striped table with one Name column, several data
columns, alternating row shading, and a shaded header row" is an anti-pattern
unless the task explicitly asks about those visual properties. It should be
rewritten to the semantic surface needed for the question, such as "The image
shows a table of named rows and data columns." Do not mention zebra striping,
header shading, background treatment, font style, palette, panel border,
rounded corners, paper texture, or similar visual implementation details unless
they are answer-verification witnesses.

## Annotation Review

For every task:

- annotation marks minimal visual answer-verification witnesses for the task
  family, not answer labels, decorative context, or the full reasoning proof;
- reference objects, scope regions, candidate lists, intermediate operands,
  ranked candidates, and debug/proof details stay in trace metadata unless
  they are part of the task's answer-verification witness;
- answer and annotation are bound from the same execution trace;
- annotation type matches visual primitive:
  - area-like witnesses use bbox-family;
  - compact centers use point-family;
  - edges, vectors, spans, and routes use segment-family;
- guaranteed single witness uses scalar `point`, `bbox`, or `segment`;
- variable homogeneous witnesses use set types;
- ordered witnesses use sequence types;
- role-bound witnesses use map types;
- set annotations such as `bbox_set`, `point_set`, and `segment_set` contain
  homogeneous witnesses only; use `bbox_map`, `point_map`, `bbox_set_map`, or
  `point_set_map` when witnesses have meaningfully different roles;
- maps are used only when roles matter, not to avoid scalar annotation;
- zero-count tasks use an empty set only when the queried witness set is truly
  empty;
- annotation witnesses are unique given the answer and prompt.

The uniqueness check is important. A generated instance is bad when the answer
is correct but more than one annotation would be equally valid. Examples:

- a plain `bbox_set` mixes different witness roles, such as one source/original
  board and one selected option panel;
- duplicate answer-bearing labels make either duplicate object a valid
  annotation;
- a count answer can be supported by multiple different same-size subsets
  because the prompt does not define the full counted set;
- a prompt asks for "the marked object" but more than one object has the same
  marker;
- option panels contain duplicate correct options.

Fix uniqueness by construction: make labels/objects/options unique, clarify the
prompt, or change the annotation contract to the full minimal witness set.

## Renderer And Style Review

For every scene:

- semantic markers and prompt-facing cues are visible under every style;
- style variation never changes answer semantics;
- annotation projection happens after final layout, jitter, scaling, and
  rendering choices;
- text and labels are legible and not cropped or overlapped;
- semantic colors stay stable when prompt wording depends on color;
- non-semantic colors, fonts, palettes, boards, panels, and backgrounds vary
  safely across the domain;
- post-render noise policy is consistent with the domain contract;
- any scene-specific post-render noise override is documented in config or
  task docs;
- background/theme/treatment selection is recorded in `render_spec`;
- font choice is recorded and stays consistent within one coherent visual unit
  such as a board, page, panel, table, form, option set, or chart.

For domains with shared visual-style layers, verify that every scene uses the
intended family consistently. Do not let one scene bypass shared style/noise
defaults without a documented reason.

## Option Panel Review

For every visual-option task:

- visible option labels are consecutive in display order: `A`, `B`, `C`, ...
  or `1`, `2`, `3`, ... depending on the scene convention;
- option layout does not randomly permute label positions after labels are
  assigned;
- search for suspicious code such as `rng.shuffle(shuffled_labels)` or
  shuffled visible option labels;
- correct option position is sampled by choosing which generated option is
  correct, not by displaying labels in random order;
- option labels are readable and attached to the correct visual panel;
- the correct option is unique by construction;
- annotation marks the selected visual option only when the option image itself
  is the answer-verification witness.

## Distribution And Sampling Manual Review

For every task:

- query ids are sampled uniformly by default unless an approved policy says
  otherwise;
- answer distributions are broad enough for the intended task;
- semantic random axes are independent of answer, query id, correct option, and
  difficulty unless intentionally constrained by the task contract;
- construction does not silently relax constraints to force acceptance;
- repeated generation failures are fixed in sampling/construction logic;
- review distribution artifacts represent current source, prompts, and config.

## Domain Consistency Review

Across the whole domain, verify:

- similar tasks use similar prompt style;
- similar visual witnesses use the same annotation geometry;
- similar option tasks use the same option-label convention;
- scalar annotation decisions are consistent;
- post-render noise defaults and visual-style families are consistent;
- scene configs do not contain query routing, task coverage, or retired
  difficulty gates;
- task docs, domain docs, active inventory, prompt assets, configs, tests, and
  review artifacts describe the same active task surface;
- no stale review folders remain for retired task ids;
- no human review checkbox is considered final if source/prompts/artifacts
  changed after the human review.

## Domain Post-Migration Report

Write an issue-only report under the docs report workspace, for example:

```text
docs/domain-migration-report/<domain>/<domain>_post_migration_checklist.md
```

The report should contain only issues identified for the domain, scene, or
task. Do not list tasks/scenes that passed, do not include "good" findings, and
do not summarize successful checks except as minimal provenance for how the
issues were found.

Allowed minimal provenance:

- domain, date, reviewer/agent;
- commands run and outputs/reports;
- timestamp or source artifact versions if useful for reproduction.

For every issue, include:

- severity: `blocking`, `required_fix`, or `followup`;
- scope: domain, scene, task, and query id when applicable;
- category: taxonomy/program, query split, prompt, annotation, renderer/style,
  distribution, option panel, stale artifact/docs, or automated gate;
- supporting artifact: file path, review sample, generated artifact, or
  command report;
- why it violates the current contract;
- proposed follow-up fix, without applying the fix during this audit pass.

If no issues are found, the report should contain only a short statement such
as `No post-migration issues identified for <domain> in this read-only audit.`
Do not include a long pass narrative.

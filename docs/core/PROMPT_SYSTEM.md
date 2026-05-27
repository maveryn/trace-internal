# TRACE Prompt System

Prompt text is externalized and deterministic.

## 1) Core contract
1. Task modules must not hardcode user-facing prompt strings.
2. Bundles live under `prompts/<domain>/<task_group>/<bundle_id>.json`.
3. Composition layers:
   - scene,
   - task,
   - optional query,
   - output mode (`answer_only`, `answer_and_evidence`).
4. Selection is deterministic from seed namespaces.
5. Each required template list must contain exactly 5 high-quality variants.
6. All active tasks must provide task-specific JSON-format guidance in both output modes:
   - `answer_only` uses `{"answer": ...}`
   - `answer_and_evidence` uses `{"answer": ..., "evidence": ...}`
   - the final JSON-object instruction is supplied by RLVR system prompts and the generic schema sentence is stripped from rendered user prompts
   - rendered output-mode instructions should keep task-specific `evidence_hint` / `answer_hint` lines and JSON examples, not tell the model to respond with only that object or suppress intermediate reasoning
7. Prefer slot-based composition for reusable format rules (for example shared `json_output_contract*` in domain/task-group config for compatibility, with task-level `evidence_hint`/`answer_hint`/example overrides).
8. For mixed-shape tasks, keep one bundle and switch shape-specific wording via slots (`object_description_*`, `question_text_*`, evidence/answer hint families).
9. When a prompt asks about a named color, include the canonical hex code in the prompt-facing color label using the format `<color_name> [#RRGGBB]`.
10. For reference-panel tasks, keep the scene layer responsible for establishing the panel layout so task-layer wording can focus on the matching rule itself.
11. When only some query branches need a slot, declare it under `required_slots_by_key["query:<query_key>"]` rather than under the shared `task:<task_key>` entry.
12. Scene templates should read like ordinary visual framing: use stems such as `The image shows ...`, `The chart shows ...`, `The table shows ...`, `The diagram shows ...`, or `The board shows ...`.
13. Do not use telegraphic or imperative scene stems such as `Shown is`, `Displayed is`, `Use this`, `Read this`, `Look at`, `The image contains`, or `The chart is`.
14. If the query layer already contains the complete question, set the task layer to empty templates with `allow_empty_task_templates: true` instead of adding filler like `Use the visual to answer`.

## 2) Bundle schema (v0)
Required fields:
1. `bundle_id`
2. `schema_version`
3. `scene_templates`
4. `task_templates`
5. `answer_or_evidence_templates`
6. `required_slots_by_key`
7. Optional: `query_templates`
8. Optional: `allow_empty_task_templates`; use only when the query layer is the full question and any visible task-layer text would be redundant. The bundle must still provide exactly 5 task-template entries so deterministic variant metadata stays stable.

## 3) Metadata requirements
Trace `query_spec.prompt_variant` should include:
1. bundle/key identifiers (`scene_key`, `task_key`, optional `query_key`),
2. selected variant indices,
3. variant counts,
4. slot values for declared required slots,
5. output-mode key/index when mode templates exist.

For wrapper tasks that reuse another task group's prompt bundle, `query_spec.prompt_variant` may also include `prompt_domain` and `prompt_task_group`. Validation uses those optional fields to locate the prompt bundle while the train record keeps the wrapper task's own `domain` and `task_group`.

Train records should store:
1. active `prompt`,
2. all rendered mode variants in `prompt_variants`.

## 4) Shared implementation
1. `trace/core/prompts/assets.py` — bundle loading/cache.
2. `trace/core/prompts/schema.py` — schema validation.
3. `trace/core/prompts/select.py` — deterministic variant selection.
4. `trace/core/prompts/render.py` — strict rendering and composition.
5. `trace/tasks/shared/prompt_variants.py` — task-level dual-mode orchestration.

## 4.1 Prompt-quality policy
1. Prefer 5 strong variants over larger padded lists.
2. Keep stems natural and image-focused; avoid awkward scaffolding such as “single/exactly one object” unless the distinction is semantically necessary.
3. Keep output-mode variants concise and structurally consistent so format requirements stay easy to parse.
4. Keep task/query wording focused on the semantic query; format instructions belong in the output-mode layer.
5. Keep layer responsibilities non-overlapping:
   - scene layer: visual context only,
   - task layer: operation hint only when needed,
   - query layer or `question_text`: the actual question,
   - output-mode layer: field hints and JSON examples only.
6. Avoid repeating broad nouns such as image, chart, table, diagram, board, question, or answer across adjacent prompt layers.
7. Scene-layer wording should establish only the visible scaffold; it should not restate the task operation or tell the model how to answer.
8. Task templates that wrap `{question_text}` should stay short, for example `{question_text}` or `Question: {question_text}`. Avoid wrappers that repeat the scene noun unless the task genuinely needs that extra context.
9. Use `scripts/audit_prompt_concision.py` to inspect rendered prompts for length and repeated scaffolding before and after broad prompt edits. For full-registry reviews, run it with `--variant-coverage --samples-per-variant 1 --include-all-prompts` so observed query branches are sampled and written to `samples/prompt_concision_audit_all.md`.

## 5) Active bundles/tasks
Active prompt bundle usage is derived from `configs/domains/**/*.yaml`
`bundle_id` references. Do not maintain an exhaustive task-to-bundle map in
this document; that map drifts quickly as tasks are split, merged, or moved.

Use these source-of-truth surfaces instead:
1. Config references in `configs/domains/<domain>/<task_group>.yaml`.
2. Prompt assets in `prompts/<domain>/<task_group>/<bundle_id>.json`.
3. Runtime prompt metadata in `query_spec.prompt_variant`.
4. Active task inventory in `docs/ACTIVE_TASK_INVENTORY.md`.
5. Task-level contracts in `docs/tasks/<task_id>.md`.

Validation:
```bash
PYTHONPATH=. python scripts/check_active_inventory_integrity.py --include-local-cache
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_prompt_system.py tests/test_docs_consistency.py
```

For prompt wording reviews, use:
```bash
PYTHONPATH=. python scripts/audit_prompt_concision.py --variant-coverage --samples-per-variant 1 --include-all-prompts --output samples/prompt_concision_audit_all.md
```

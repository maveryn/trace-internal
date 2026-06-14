# TRACE Prompt System

Prompt text is externalized, deterministic, and traceable.

## 1) Core Contract
1. Task modules must not hardcode user-facing prompt text.
2. Migrated and review-candidate scene packages use prompt bundles under
   `prompts/<domain>/<scene_id>/<bundle_id>.json`.
3. Transitional prompt bundle locations may remain only for unmigrated scenes.
4. Composition layers are:
   - scene,
   - task,
   - optional query,
   - output mode (`answer_only`, `answer_and_annotation`).
5. Selection is deterministic from seed namespaces.
6. Required template lists contain exactly 5 high-quality variants unless the
   schema declares an approved exception.
7. All active tasks must provide task-specific JSON-format guidance in both
   output modes:
   - `answer_only` uses `{"answer": ...}`
   - `answer_and_annotation` uses `{"annotation": ..., "answer": ...}`
8. Output-mode instructions should keep task-specific `answer_hint`,
   `annotation_hint`, and JSON examples. The generic final JSON-object
   instruction belongs in the RLVR system prompt layer.
9. For named colors, include the canonical hex code in the prompt-facing color
   label using `<color_name> [#RRGGBB]`.
10. If the query layer already contains the full question, the task layer may be
    empty only when the bundle declares `allow_empty_task_templates: true`.

## 2) Bundle Schema
Required fields:

1. `bundle_id`
2. `schema_version`
3. `scene_templates`
4. `task_templates`
5. `answer_or_annotation_templates`
6. `required_slots_by_key`

Optional fields:

1. `query_templates`
2. `allow_empty_task_templates`

Required slots should be declared at the narrowest layer that needs them:

- `scene:<scene_key>` for scene-wide visual framing slots;
- `task:<task_key>` for objective-level slots;
- `query:<query_key>` for branch-specific wording slots;
- output-mode keys for answer/annotation examples and hints.

## 3) Metadata Requirements
Trace `query_spec.prompt_variant` should include:

1. bundle id and layer keys;
2. selected variant indices;
3. query id and query-id count when applicable;
4. slot values for declared required slots;
5. output-mode key/index;
6. prompt asset version when available.

Train records should store the active `prompt` and generated `prompt_variants`
when both output modes are materialized.

## 4) Shared Implementation
1. `trace/core/prompts/assets.py` — bundle loading/cache.
2. `trace/core/prompts/schema.py` — schema validation.
3. `trace/core/prompts/select.py` — deterministic variant selection.
4. `trace/core/prompts/render.py` — strict rendering and metadata.
5. `trace/tasks/shared/prompt_variants.py` — task-level dual-mode orchestration.
6. `trace/tasks/shared/prompt_examples.py` — deterministic JSON-example helpers.
7. `trace/tasks/shared/prompt_slots.py` — shared prompt trace/spec helpers.

## 5) Prompt Quality Policy
1. Keep stems natural and image-focused.
2. Scene layer describes the visible scaffold only.
3. Task layer states the operation only when needed.
4. The query layer owns the actual question; user-facing wording should come
   from prompt templates.
5. Output-mode layer owns field hints and JSON examples.
6. Avoid repeating broad nouns such as image, chart, table, diagram, board,
   question, or answer across adjacent layers.
7. Template examples show valid output format for the active answer and
   annotation contract, not the sampled instance's actual answer.
8. Use `annotation` terminology in prompts.

## 6) Source Of Truth
Do not maintain exhaustive task-to-bundle maps in this document. They drift.

Use:

1. config references under `configs/domains/`;
2. prompt assets under `prompts/`;
3. runtime prompt metadata in `query_spec.prompt_variant`;
4. generated task inventory in `docs/ACTIVE_TASK_INVENTORY.md`;
5. task-level contracts in `docs/tasks/`.

Validation:

```bash
PYTHONPATH=. python scripts/check_active_inventory_integrity.py --include-local-cache
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. pytest -q tests/test_prompt_system.py tests/test_docs_consistency.py
```

Prompt wording audit:

```bash
PYTHONPATH=. python scripts/audit_prompt_concision.py --variant-coverage --samples-per-query-id 1 --include-all-prompts --output samples/prompt_concision_audit_all.md
```

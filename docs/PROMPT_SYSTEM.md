# TRACE Prompt System

## Purpose
Define a scalable prompt-template system so tasks do not hardcode prompt text and can reuse prompt logic across domains/task groups/query types.

This plan is informed by Prism's prompt-component pattern in Tesserae:
1. external JSON prompt assets,
2. deterministic variant sampling,
3. placeholder validation,
4. prompt-variant metadata recording.

## Hard requirements
1. Prompt text must be externalized (no task-local hardcoded prompt strings in production task code).
2. Prompt composition must be layered:
- task-type template layer (shared across similar tasks),
- query-type template layer (specific to query semantics).
3. Each task-type composition bucket must have at least 10 prompt variants.
4. Each query type must have at least 10 prompt variants.
5. Prompt variant selection must be deterministic from seed namespaces.
6. Prompt variant provenance must be stored in trace metadata.

## Template structure
Use template assets under `prompts/` with a stable schema.

Proposed layout:
1. `prompts/<domain>/<task_group>/<bundle_id>.json` for primary bundles.
2. `prompts/shared/*.json` for cross-domain reusable fragments.

Minimum bundle schema (v1):
1. `bundle_id`
2. `schema_version`
3. `task_type_templates`:
- map from `task_type_key` to a list of 10+ strings.
4. `query_type_templates`:
- map from `query_type` to a list of 10+ strings.
5. optional `answer_or_evidence_templates`:
- shared answer/evidence instruction strings (for example integer return format).
6. `required_slots_by_key`:
- explicit placeholder requirements per key to validate formatting inputs.

## Prompt composition model
For each instance:
1. sample one task-type variant from `task_type_templates[task_type_key]`,
2. sample one query-type variant from `query_type_templates[query_type]`,
3. render with strict placeholder substitution using task-provided slots,
4. join sections via deterministic composition rule.

Default composition order:
1. task-type sentence,
2. query-type instruction sentence,
3. optional answer/evidence formatting sentence.

## Deterministic selection policy
Use fixed seed namespaces:
1. `prompt.task_type`
2. `prompt.query_type.<query_type>`
3. `prompt.answer_or_evidence` (if used)

Rules:
1. no call-order-dependent randomness,
2. no hidden global RNG state,
3. record sampled indices.

## Required metadata emission
Per instance, include prompt metadata in trace payload (recommended in `query_spec.prompt_variant`):
1. `prompt_bundle_id`
2. `task_type_key`
3. `query_type_key`
4. `task_type_variant_index`
5. `query_type_variant_index`
6. `variant_count_by_key`
7. `template_paths` (relative asset paths)
8. optional rendered slot map snapshot.

## Shared code
Implemented shared prompt modules:
1. `trace/core/prompts/assets.py`
- load and cache external prompt bundle files.
2. `trace/core/prompts/schema.py`
- bundle dataclasses and schema validation helpers.
3. `trace/core/prompts/render.py`
- strict placeholder rendering and composition.
4. `trace/core/prompts/select.py`
- deterministic variant selection from seed namespaces.

Task code should call a shared entrypoint, for example:
1. `render_prompt(domain, task_group, bundle_id, task_type_key, query_type, slots, instance_seed)`.

## Validation and CI plan
Add build-time and CI checks:
1. prompt bundle file exists and parses,
2. all required keys exist,
3. each required template list has 10+ entries,
4. placeholders required by schema are present in every template,
5. rendered prompt has no unresolved placeholders.

## Implementation status
1. Infrastructure implemented:
- `trace/core/prompts/assets.py`, `schema.py`, `select.py`, `render.py`.
2. Prompt assets implemented:
- `prompts/geometry/measurement/geometry_measurement_v1.json`,
- `prompts/tile/path/tile_path_v1.json`.
3. Task migration implemented:
- `geometry_angle_value_query` now uses bundle rendering with prompt metadata in trace payload.
- `tile_shortest_path` now uses bundle rendering with prompt metadata in trace payload.
4. Remaining enforcement work:
- add lint/test to reject hardcoded prompt literals across all task modules,
- add strict build-time prompt-bundle validation in CI profile.

## Task documentation requirement
Every new task doc (`docs/tasks/<task_id>.md`) must include:
1. `Prompt Bundle` section with `bundle_id`,
2. `task_type_key` used by that task,
3. list of supported `query_type` values and their template keys,
4. required placeholder slot schema,
5. example rendered prompts for at least 2 query types.

## Open questions
1. Should task-type templates be shared at `task_group` scope only, or optionally across groups via `prompts/shared/` aliases?
2. Should answer/evidence instruction templates be bundle-local or centralized per answer/evidence type?
3. Do we enforce uniqueness/diversity constraints across prompt variants beyond count >= 10?

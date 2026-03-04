# TRACE Prompt System

## Purpose
Define the reusable prompt architecture for TRACE so task modules do not hardcode user-facing prompt strings.

## Contract
1. Prompt text is externalized in versioned bundle assets under `prompts/`.
2. Prompt composition is layered:
- task-type template layer (shared composition),
- query-type template layer (query-specific instruction).
3. Deterministic variant selection uses fixed seed namespaces.
4. Prompt provenance metadata is emitted per instance in trace payload.

## Bundle layout
Path:
1. `prompts/<domain>/<task_group>/<bundle_id>.json`

Minimum bundle schema (v1):
1. `bundle_id`
2. `schema_version`
3. `task_type_templates`: `task_type_key -> [templates]`
4. `query_type_templates`: `query_type -> [templates]`
5. optional `answer_or_evidence_templates`
6. `required_slots_by_key`

Variant cardinality rule:
1. task-type template list: at least 10 variants
2. each query-type template list: at least 10 variants

## Composition and determinism
Composition order:
1. task-type sentence
2. query-type sentence
3. optional answer/evidence instruction sentence

Seed namespaces:
1. `prompt.task_type`
2. `prompt.query_type.<query_type>`
3. `prompt.answer_or_evidence` (if used)

Rules:
1. no hidden global RNG state,
2. no call-order-dependent randomness,
3. strict placeholder rendering (missing required slot is a hard error).

## Trace metadata
Prompt variant metadata should be emitted under `trace_payload.query_spec.prompt_variant` with:
1. `prompt_bundle_id`
2. `task_type_key`
3. `query_type_key`
4. `task_type_variant_index`
5. `query_type_variant_index`
6. `variant_count_by_key`
7. optional slot snapshot / asset path references

## Shared implementation
1. `trace/core/prompts/assets.py`: bundle loading + cache
2. `trace/core/prompts/schema.py`: bundle schema checks
3. `trace/core/prompts/select.py`: deterministic variant selection
4. `trace/core/prompts/render.py`: strict placeholder render + composition

Task modules should call shared rendering APIs (for example `render_prompt(...)`), not local prompt concatenation logic.

## Current implementation status
Implemented:
1. shared prompt modules under `trace/core/prompts/`
2. active bundle assets:
- `prompts/geometry/measurement/geometry_measurement_v1.json`
- `prompts/tile/path/tile_path_v1.json`
3. migrated tasks:
- `geometry_angle_value_query`
- `tile_shortest_path`

Pending enforcement:
1. pre-finalize validation checks for prompt bundle metadata conformance across all emitted instances.
2. CI guardrails for prompt-cardinality regressions and unresolved-placeholder regressions at dataset-validation level.

## Task-doc requirement
Each `docs/tasks/<task_id>.md` must include:
1. `prompt_bundle_id`
2. `task_type_key`
3. query-type mapping
4. required slot schema
5. variant counts

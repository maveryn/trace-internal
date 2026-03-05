# TRACE Prompt System

Prompt text is externalized and deterministic.

## 1) Core contract
1. Task modules must not hardcode user-facing prompt strings.
2. Bundles live under `prompts/<domain>/<task_group>/<bundle_id>.json`.
3. Composition layers:
   - task type,
   - query type,
   - output mode (`answer_only`, `answer_and_evidence`).
4. Selection is deterministic from seed namespaces.
5. Each required template list must have at least 10 variants.

## 2) Bundle schema (v1)
Required fields:
1. `bundle_id`
2. `schema_version`
3. `task_type_templates`
4. `query_type_templates`
5. `answer_or_evidence_templates`
6. `required_slots_by_key`

## 3) Metadata requirements
Trace `query_spec.prompt_variant` should include:
1. bundle/key identifiers,
2. selected variant indices,
3. variant counts,
4. slot values for declared required slots,
5. output-mode key/index when mode templates exist.

Train records should store:
1. active `prompt`,
2. all rendered mode variants in `prompt_variants`.

## 4) Shared implementation
1. `trace/core/prompts/assets.py` — bundle loading/cache.
2. `trace/core/prompts/schema.py` — schema validation.
3. `trace/core/prompts/select.py` — deterministic variant selection.
4. `trace/core/prompts/render.py` — strict rendering and composition.
5. `trace/tasks/shared/prompt_variants.py` — task-level dual-mode orchestration.

## 5) Active bundles/tasks
Bundles:
1. `prompts/geometry/measurement/geometry_measurement_v1.json`
2. `prompts/tile/path/tile_path_v1.json`

Tasks:
1. `geometry_angle_value_query`
2. `tile_shortest_path`

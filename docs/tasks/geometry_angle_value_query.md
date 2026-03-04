# `geometry_angle_value_query`

## Overview
1. Domain: `geometry`
2. Task group: `measurement`
3. Task id: `geometry_angle_value_query`
4. Objective: return an angle value based on query type and provide grounded vertex evidence.

## Scene and Query
1. Scene entities: multiple angle entities with unique degree values.
2. Supported query types:
- `min`,
- `max`,
- `median`,
- `closest_to_x`,
- `smallest_above_x`,
- `largest_below_x`,
- `difference_max_min`.
3. Answer type: `integer`.
4. Default evidence type: `point_set` (or `point_path` for `difference_max_min`).
5. Alternate evidence forms: both `point_set` and `point_path` are available in projected trace payload.

## Prompt Bundle
1. `prompt_bundle_id`: `geometry_measurement_v1`.
2. `task_type_key`: `angle_measurement`.
3. Query type template keys:
- one key per supported `query_type` above.
4. Required slot schema:
- `candidate_count`,
- `entity_plural` (for example `angles`),
- `target_x` for threshold/closest variants.
5. Variant counts:
- task-type variants >= 10,
- each query-type variants >= 10.
6. Bundle asset path:
- `prompts/geometry/measurement/geometry_measurement_v1.json`.

## Determinism and Metadata
1. Prompt seed namespaces:
- `prompt.task_type`,
- `prompt.query_type.<query_type>`.
2. Prompt metadata in trace (`trace_payload.query_spec.prompt_variant`):
- bundle id,
- task/query keys,
- variant index and count.

## Generation Constraints
1. Unique-answer-by-construction enforced; duplicate angle values are rejected.
2. Invalid query conditions (for example no value above threshold) are rejected and resampled.
3. No auto-relaxation of semantic constraints.

## Visual Variation
1. Task-group default post-image noise policy (`geometry/measurement`):
- `apply_prob = 0.75`,
- edit types: `blur`, `downsample`, `jpeg`, `noise`,
- edit-count range: `[1, 2]`.
Defaults are defined in task-group config (`configs/task_groups/geometry/measurement.yaml`) and loaded through `trace/tasks/geometry/measurement/noise_defaults.py`.
2. Task-level overrides can be passed via `params.visual.noise` (or flat compatibility keys).
3. Applied noise metadata is emitted in `trace_payload.render_spec.post_image_noise`.

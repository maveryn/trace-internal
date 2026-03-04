# `tile_shortest_path`

## Overview
1. Domain: `tile`
2. Task group: `path`
3. Task id: `tile_shortest_path`
4. Objective: return shortest path length and grounded path evidence in a maze grid.

## Scene and Query
1. Scene entities: grid cells with blocked/open status, start, and goal.
2. Supported query types:
- `shortest_path`.
3. Answer type: `integer`.
4. Default evidence type: `point_path`.
5. Alternate evidence forms: `bbox_set` can be emitted via task config.

## Prompt Bundle
1. `prompt_bundle_id`: `tile_path_v1`.
2. `task_type_key`: `maze_path`.
3. Query type template keys:
- `shortest_path`.
4. Required slot schema:
- `rows`,
- `cols`,
- `evidence_hint`.
5. Variant counts:
- task-type variants >= 10,
- query-type variants >= 10 (for `shortest_path` key).
6. Bundle asset path:
- `prompts/tile/path/tile_path_v1.json`.

## Determinism and Metadata
1. Prompt seed namespaces:
- `prompt.task_type`,
- `prompt.query_type.shortest_path`.
2. Prompt metadata in trace (`trace_payload.query_spec.prompt_variant`):
- bundle id,
- task/query keys,
- variant index and count.

## Generation Constraints
1. Maze sampler enforces a unique shortest path.
2. Candidates without unique shortest path are rejected and resampled.
3. No auto-relaxation of semantic constraints.

## Visual Variation
1. Task-group default background-style policy (`tile/path`):
- deterministic style sampling with weighted presets (for example `solid_light`, `grid_light`),
- defaults are defined in `configs/task_groups/tile/path.yaml` and loaded through `trace/tasks/tile/path/background_defaults.py`,
- applied style metadata is emitted in `trace_payload.render_spec.background_style`.
2. Task-group default post-image noise policy (`tile/path`):
- `apply_prob = 0.0` (disabled by default),
- edit types and ranges follow shared noise presets when enabled.
Defaults are defined in task-group config (`configs/task_groups/tile/path.yaml`) and loaded through `trace/tasks/tile/path/noise_defaults.py`.
3. Task-level overrides can be passed via `params.visual.background` / `params.visual.noise` (or flat compatibility keys).
4. Applied noise metadata is emitted in `trace_payload.render_spec.post_image_noise`.

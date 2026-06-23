# `task_geometry__incircle_tangents__incircle_tangent_perimeter_value`

## Contract
1. Domain: `geometry`
2. Scene id: `incircle_tangents`
3. Query id: `single`
4. Internal query id: `triangle_perimeter_from_tangent_segments`
5. Answer schema: `integer`
6. Annotation schema: `bbox_map` with keys `AD_AF`, `BD_BE`, `CE_CF`

## Program Contract
- `perimeter(incircle_tangent_triangle, tangent_equalities={AD=AF,BD=BE,CE=CF}); scene=incircle_tangents; scope=incircle_tangent_perimeter_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_tangent_polygon_incircle_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space keyed boxes for the three visible tangent-equality labels needed to compute the perimeter. Formula metadata, case ids, and unrendered measurements remain private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/incircle_tangents.yaml`
- Task module: `trace/tasks/geometry/incircle_tangents/incircle_tangent_perimeter_value.py`

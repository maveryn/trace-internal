# `task_geometry__incircle_tangents__incircle_radius_from_area_value`

## Contract
1. Domain: `geometry`
2. Scene id: `incircle_tangents`
3. Query id: `single`
4. Internal query id: `inradius_from_area_and_tangent_segments`
5. Answer schema: `number` rounded to one decimal place
6. Annotation schema: `bbox_map` with keys `AD_AF`, `BD_BE`, `CE_CF`, `area`

## Program Contract
- `radius(area_label, incircle_tangent_triangle, tangent_equalities={AD=AF,BD=BE,CE=CF}); scene=incircle_tangents; scope=incircle_radius_from_area_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_tangent_polygon_incircle_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space keyed boxes for the three visible tangent-equality labels and the visible area label needed to compute the incircle radius. Formula metadata, case ids, and unrendered measurements remain private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/incircle_tangents.yaml`
- Task module: `trace/tasks/geometry/incircle_tangents/incircle_radius_from_area_value.py`

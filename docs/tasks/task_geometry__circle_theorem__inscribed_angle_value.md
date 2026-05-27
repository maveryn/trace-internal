# `task_geometry__circle_theorem__inscribed_angle_value`

## Contract
1. Domain: `geometry`
2. Task group: `circle`
3. Scene id: `circle_theorem`
4. Public query variant: `default`
5. Query ids: `inscribed_angle_from_central`, `central_angle_from_inscribed`, `inscribed_angle_from_arc`
6. Answer type: `integer`
7. Evidence type: `bbox_set`

## Prompt Bundle
- Bundle id: `geometry_circle_theorem_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`
- Prompt variants must be selected through the external prompt bundle metadata and recorded in trace payloads.

## Behavior
Solve a missing central or inscribed angle measure using the inscribed-angle theorem and the visible circle labels.

The public task is a narrowed wrapper around the shared geometry `circle` implementation. The selected query name is retained only in `query_id` and trace diagnostics; it is not a public sampling unit.

## Evidence
Prompt-facing evidence is a `bbox_set`: one pixel bounding box around the visible angle or arc measurement label needed to compute the answer. It excludes unrelated measurements, point labels, and the unknown target angle label. Verifier evidence is projected from the same generated scene metadata used to compute the answer. Verifiers must not infer answer or evidence from pixels.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version. Sampling axes, scene/query IDs, prompt bundle IDs, and render choices must be recorded in trace metadata.

## Source
- Config: `configs/domains/geometry/circle.yaml`
- Task module: `trace/tasks/geometry/circle/theorem_value.py`

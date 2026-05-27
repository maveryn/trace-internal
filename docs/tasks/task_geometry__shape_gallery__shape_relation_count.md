# `task_geometry__shape_gallery__shape_relation_count`

## Contract
1. Domain: `geometry`
2. Task group: `similarity`
3. Scene id: `shape_gallery`
4. Public query variant: `default`
5. Query id: `congruent_count` or `similar_count`
6. Answer type: `integer`
7. Evidence type: `bbox_set`

## Prompt Bundle
- Bundle id: `geometry_similarity_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`
- Prompt variants must be selected through the external prompt bundle metadata and recorded in trace payloads.

## Behavior
Count candidate polygons with the requested relation to the reference polygon.

The public task wraps congruent and similar candidate-count queries over the same reference/candidate gallery. The selected query is retained only in `query_id` and trace diagnostics; it is not a public sampling unit.

## Evidence
Verifier evidence is projected from the same generated scene metadata used to compute the answer. Verifiers must not infer answer or evidence from pixels.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version. Sampling axes, scene/query IDs, prompt bundle IDs, and render choices must be recorded in trace metadata.

## Source
- Config: `configs/domains/geometry/similarity.yaml`
- Task module: `trace/tasks/geometry/similarity/count.py`

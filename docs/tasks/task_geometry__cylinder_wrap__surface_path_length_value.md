# `task_geometry__cylinder_wrap__surface_path_length_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `cylinder_wrap`
4. Query id: `surface_path_length_value`
5. Answer type: `number`
6. Evidence type: `keyed_bbox_map`

## Prompt Bundle
- Bundle id: `geometry_cylinder_wrap_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`
- Prompt variants must be selected through the external prompt bundle metadata and recorded in trace payloads.

## Behavior
Compute the length of a marked path on a cylinder side using the rectangular
unwrapped net. The visible net labels provide the circumference and height,
and cases are sampled from integer Pythagorean triples so the answer is a
unique integer path length.

## Evidence
Prompt-facing evidence is a `keyed_bbox_map` with `marked_surface_path`,
`circumference_dimension`, and `height_dimension`. The dimension bboxes cover
the visible dimension annotation, including its numeric label. Verifier
evidence is projected from the same pixel geometry used to render the scene and
compute the answer.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt
bundle version. Sampling axes, prompt bundle ids, selected visual style, font
family, and render choices are recorded in trace metadata.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Prompt bundle: `prompts/geometry/measurement/geometry_cylinder_wrap_v0.json`
- Task module: `trace/tasks/geometry/measurement/cylinder_wrap.py`

# `task_geometry__cylinder_wrap__wrapped_mark_position_label`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `cylinder_wrap`
4. Query id: `wrapped_mark_position_label`
5. Answer type: `option_letter`
6. Evidence type: `keyed_point_map`

## Prompt Bundle
- Bundle id: `geometry_cylinder_wrap_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`
- Prompt variants must be selected through the external prompt bundle metadata and recorded in trace payloads.

## Behavior
Match one marked position on an unwrapped cylinder strip to a labeled candidate
point on the top-view rim. Candidate labels are sampled from the safe global
uppercase label pool and drawn directly in the image. The answer is the single
matching candidate label.

## Evidence
Prompt-facing evidence is a `keyed_point_map` with `source_strip_mark` and
`matching_rim_candidate`, each at the center of the visible mark/candidate.
Verifier evidence is projected from the same pixel geometry used to render the
scene and compute the answer.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt
bundle version. Sampling axes, prompt bundle ids, selected visual style, font
family, candidate labels, and render choices are recorded in trace metadata.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Prompt bundle: `prompts/geometry/measurement/geometry_cylinder_wrap_v0.json`
- Task module: `trace/tasks/geometry/measurement/cylinder_wrap.py`

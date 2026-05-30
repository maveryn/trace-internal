# `task_geometry__measuring_tools__ruler_length_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `measuring_tools`
4. Query id: `ruler_length_value`
5. Answer type: `number`
6. Evidence type: `bbox_set`

## Prompt Bundle
- Bundle id: `geometry_measuring_tools_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`
- Prompt variants must be selected through the external prompt bundle metadata and recorded in trace payloads.

## Behavior
Read the length of a marked segment from a visible ruler. The segment endpoints
are aligned to ruler tick marks, with a nonzero ruler offset sampled separately
from the target length. Answers are integer centimeters.

## Evidence
Prompt-facing evidence is a `bbox_set` containing the marked segment and the
ruler interval used to read it. Verifier evidence is projected from the same
pixel geometry used to render the scene and compute the answer.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt
bundle version. Sampling axes, prompt bundle ids, and render choices are
recorded in trace metadata.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/measuring_tools.py`

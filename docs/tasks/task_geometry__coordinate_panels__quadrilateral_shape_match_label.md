# `task_geometry__coordinate_panels__quadrilateral_shape_match_label`

## Contract
1. Domain: `geometry`
2. Task group: `coordinate`
3. Scene id: `coordinate_panels`
4. Public query id: `default`
5. Query id: `square_shape_match_label`, `rectangle_shape_match_label`, `rhombus_shape_match_label`, or `parallelogram_shape_match_label`
6. Answer type: `option_letter`
7. Evidence type: `bbox_set`

## Prompt Bundle
- Bundle id: `geometry_coordinate_quadrilateral_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`
- Prompt variants must be selected through the external prompt bundle metadata and recorded in trace payloads.

## Behavior
Choose the labeled mini coordinate panel whose four unlabeled points form the requested quadrilateral.

Each image contains six panels. The target panel has exactly one requested shape, while distractor panels use other exact quadrilateral families or non-matching four-point sets. Rectangle and rhombus branches avoid square ambiguity, and the parallelogram branch uses a non-rectangle/non-rhombus parallelogram target with non-parallelogram distractors.

## Evidence
Verifier evidence is the final-image pixel bounding box around the selected panel. The four graph coordinates and exact classification for each panel are retained in trace metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version. Query IDs, panel labels, point sets, marker style/color, prompt bundle IDs, and render choices are recorded in trace metadata.

## Source
- Config: `configs/domains/geometry/coordinate.yaml`
- Prompt bundle: `prompts/geometry/coordinate/geometry_coordinate_quadrilateral_v0.json`
- Task module: `trace/tasks/geometry/coordinate/quadrilateral.py`

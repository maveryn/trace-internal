# `task_geometry__coordinate_plane__locus_panel_match_label`

## Contract
1. Domain: `geometry`
2. Task group: `coordinate`
3. Scene id: `coordinate_plane`
4. Public query variant: `default`
5. Query id: `circle_inequality_panel_match`, `vertical_strip_panel_match`, `horizontal_halfplane_panel_match`, or `two_inequality_panel_match`
6. Answer type: `option_letter`
7. Evidence type: `bbox_set`

## Prompt Bundle
- Bundle id: `geometry_coordinate_locus_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`
- Prompt variants must be selected through the external prompt bundle metadata and recorded in trace payloads.

## Behavior
Choose the labeled mini coordinate panel whose shaded region matches the
condition shown in the condition box.

Each image contains six coordinate panels. The target panel has the exact
circle inequality, strip, half-plane, or two-inequality intersection described
by the condition box. Distractor panels use related but nonmatching regions,
such as shifted strips, opposite half-planes, shifted circles, or rings.

## Evidence
Verifier evidence is the final-image pixel bounding box around the selected
panel. Each panel's semantic region specification and answer flag are recorded
in trace metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt
bundle version. Query IDs, panel labels, region specs, prompt bundle IDs, and
render choices are recorded in trace metadata.

## Source
- Config: `configs/domains/geometry/coordinate.yaml`
- Prompt bundle: `prompts/geometry/coordinate/geometry_coordinate_locus_v0.json`
- Task module: `trace/tasks/geometry/coordinate/locus_region.py`

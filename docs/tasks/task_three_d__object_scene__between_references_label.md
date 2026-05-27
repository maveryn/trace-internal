# `task_three_d__object_scene__between_references_label`

## Summary
- Domain: `three_d`
- Scene id: `object_scene`
- Task group: `spatial`
- Query id: `between_references`
- Answer type: `option_letter`
- Evidence type: one-box `bbox_set`
- Status: accepted

## Contract
The image shows the shared open synthetic perspective 3D object scene: a gridded floor or platform, perspective camera cues, two unlettered reference props named in the question, and `6` lettered answer candidates.

The prompt asks which lettered object is between the two named reference objects. Generation places exactly one lettered candidate in the floor-plane corridor between the references. The remaining lettered candidates are placed outside that corridor and are constrained away from heavy visual overlap with either reference.

The answer is computed from metadata using each candidate's projected position along the reference-to-reference floor segment, lateral distance from that segment, and endpoint margin. Pixels are render output, not the verifier source of truth.

## Evidence Contract
Evidence is the bounding box of the selected lettered 3D object. The two named reference objects are present in the trace and render map, but they are not part of the answer evidence.

## Prompt And Trace
The prompt bundle is `three_d_spatial_v0` under `prompts/three_d/spatial/`. The trace records camera pose, projection frame, object world coordinates, sampled dimensions, prompt-facing names, reference ids/names/shapes, per-label between metrics, per-label between truth values, and projected object bboxes.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and evidence come from the same finalized 3D scene trace.

## Calibration
Accepted on qwen25vl7b `100x24` with seed `20260521`: `hard=0.000`, `easy=0.090`, `band=0.910`, and mean solve `0.502`. The exact parquet distribution passed with `6` unique answers and max answer frequency `0.170`.

Artifacts:
- Calibration parquet and distribution report live under `out/calibration/current/three_d/object_scene/task_three_d__object_scene__between_references_label/`.
- Review workbook: `plans/task-reviews/three_d/object_scene/task_three_d__object_scene__between_references_label/task_three_d__object_scene__between_references_label.xlsx`
- Solve workbook lives under the same task-review directory.

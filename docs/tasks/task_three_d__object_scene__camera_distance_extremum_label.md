# `task_three_d__object_scene__camera_distance_extremum_label`

## Summary
- Domain: `three_d`
- Scene id: `object_scene`
- Task group: `spatial`
- Query id: `closest_to_camera|farthest_from_camera`
- Answer type: `option_letter`
- Evidence type: one-box `bbox_set`
- Status: accepted after full-bleed floor update

## Contract
The image shows an open synthetic perspective 3D scene with a full-canvas gridded floor/tabletop, small lettered 3D answer-candidate objects, and larger unlettered context props. The full-bleed grid is drawn from screen-ray intersections with the floor plane, so visible grid lines continue to the canvas bounds instead of ending at a projected platform square. The prompt asks which lettered small object is closest to or farthest from the camera.

Closest/farthest is resolved from true camera-to-small-candidate-object-center distances in the generated 3D scene metadata. Larger unlettered props such as tables or shelves can be present, but are not answer candidates for this task. The query branch is recorded in `query_id`; public outputs use `query_variant="default"`.

The camera is sampled from several oblique orbit bands around the scene, covering front, side, and rear viewpoints while avoiding nearly straight-on views that flatten the perspective.

Each instance renders `6` small lettered objects sampled from internal geometry types `sphere`, `cube`, `cylinder`, `cone`, `arrow`, `sword`, `shield`, `diamond`, `heart`, `key`, `crown`, `hourglass`, `anchor`, `horseshoe`, `hammer`, `gear`, `bell`, `trophy`, `open_book`, `dumbbell`, `mushroom`, `lantern`, `wrench`, `torus`, `pyramid`, `wedge`, `star_prism`, `cross_prism`, `hexagonal_prism`, and `half_cylinder`. It also renders larger unlettered context props sampled from `arch`, `table`, `shelf`, `open_box`, `pedestal`, `cabinet`, `sofa`, `barrel`, and `chair`. The answer remains the visible option letter, not the object name.

The trace records natural `object_name` / `prompt_name` values separately from geometry. Safe prompt-facing small names include `ball`, `cube`, `cylinder`, `cone`, `arrow`, `sword`, `shield`, `diamond`, `heart`, `key`, `crown`, `hourglass`, `anchor`, `horseshoe`, `hammer`, `gear`, `bell`, `trophy`, `open book`, `dumbbell`, `mushroom`, `lantern`, `wrench`, `ring`, `pyramid`, `ramp`, `star`, `cross`, `hexagon`, and `half cylinder`.

Object dimensions are not fixed: each generated object records a deterministic `dimension_scale`, with small candidates sampled from a compact size range and context props sampled from a larger prop-size range.

## Evidence Contract
Evidence is the bounding box of the selected small lettered 3D object. The floor grid, shadows, larger props, and depth guides are scene context only.

## Prompt And Trace
The prompt bundle is `three_d_spatial_v0` under `prompts/three_d/spatial/`. The trace records camera pose, projection frame, object world coordinates, sampled dimensions, dimension scale, shape type, natural object name, prompt-name safety flag, object role, object camera coordinates, candidate-only camera distances/order, context prop specs, and projected object bboxes.

## Calibration
The full-bleed rendering review workbook, distribution report, and combined object-scene review have been regenerated. The exact calibration parquet distribution passed with `6` unique answers and max answer frequency `0.220`.

qwen25vl7b `100x24` calibration on seed `20260523` gave `hard=0.120`, `easy=0.060`, `band=0.820`, mean solve `0.288`, cap `0.000`, and prompt max `144`. The previous bounded-platform run on seed `20260521` gave `hard=0.100`, `easy=0.030`, `band=0.870`, mean solve `0.287`, cap `0.000`, and prompt max `143`.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and evidence come from the same finalized 3D scene trace.

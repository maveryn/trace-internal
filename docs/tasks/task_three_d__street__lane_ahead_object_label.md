# `task_three_d__street__lane_ahead_object_label`

## Summary
- Domain: `three_d`
- Scene id: `street`
- Task group: `street`
- Query id: `ahead_along_lane`
- Answer type: `option_letter`
- Evidence type: one-box `bbox_set`
- Status: accepted

## Contract
The image shows a synthetic perspective 3D street intersection or T intersection with roads, sidewalks, crosswalk markings, unlettered street context, one red-boxed reference street object with a red travel-direction arrow, and lettered street objects. The street surface renders full-bleed: sidewalk ground fills the canvas and road strips are clipped to the visible floor-plane polygon, so the roads continue to the image edges rather than ending at a finite stage boundary. The prompt asks which lettered street object is directly ahead of the red-boxed object along the lane indicated by the arrow.

Each instance renders `5` lettered candidate street objects plus unlettered street context. The reference object is an unlettered car marked with a red bounding box and a red direction arrow. Unlettered context reserves more slots for large buildings/storefronts, including shopfront facades with awnings, and adds off-road tree/shrub slots while remaining excluded from candidate and evidence semantics. Exactly one lettered candidate is ahead of the reference along the same finalized lane corridor and travel direction. Distractors include objects behind the reference, objects ahead in an adjacent lane, objects off the lane, and objects on other present road arms.

The verifier uses finalized metadata, not pixels: reference road arm, lane id, travel direction vector, candidate forward distance from the reference, candidate lateral distance from the reference lane, and candidate road arm. The task supports four-way and T-intersection layouts.

## Evidence Contract
Evidence is the bounding box of the selected lettered street object. The bbox includes the option letter when rendered. The red reference box, red arrow, road markings, and other unlettered context objects are not evidence.

## Prompt And Trace
The prompt bundle is `three_d_street_v0` under `prompts/three_d/street/`. The trace records camera pose, projection frame, scene variant, intersection layout, full-bleed floor polygon mode/bounds, present/missing road arms, travel mode, reference road arm/lane/direction, candidate road arms by label, forward and lateral lane distances by label, ahead flags by label, selected object id/type, and projected object bboxes.

## Calibration
The manual review workbook, distribution report, and combined street scene review have been regenerated. Distribution passed on `100` samples with `5` unique answers and max answer frequency `0.240`. qwen25vl7b `100x24` calibration on seed `20260522` gave `hard=0.060`, `easy=0.000`, `band=0.940`, `mean=0.219`, `cap=0.000`, and prompt max `167`; the task is accepted.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and evidence come from the same finalized 3D street scene trace.

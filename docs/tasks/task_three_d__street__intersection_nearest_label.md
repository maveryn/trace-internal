# `task_three_d__street__intersection_nearest_label`

## Summary
- Domain: `three_d`
- Scene id: `street`
- Task group: `street`
- Query id: `closest_to_intersection`
- Answer type: `option_letter`
- Annotation type: one-box `bbox_set`
- Status: pending_v0_review

## Contract
The image shows a synthetic perspective 3D street intersection or T intersection with roads, sidewalks, crosswalk markings, unlettered street context, unlettered street-object candidates, and a below-scene text option panel. The street surface renders full-bleed: sidewalk ground fills the canvas and road strips are clipped to the visible floor-plane polygon, so the roads continue to the image edges rather than ending at a finite stage boundary. The prompt asks which option describes the street object closest to the center of the intersection.

Each instance renders `6` unlettered candidate street objects, such as cars, taxis, vans, buses, trucks, scooters, motorcycles, bicycles, male pedestrians, female pedestrians, traffic cones, fire hydrants, trash bins, mailboxes, construction barriers, or road barrels. Exactly one candidate has the smallest finalized ground-plane distance from its object center to the intersection center, with a margin from the next-nearest candidate.

The street context includes unlettered objects such as buildings, storefronts, trees, shrubs, traffic lights, street signs, and benches. Buildings have recorded non-semantic `building_style` attrs such as glass office, brick apartment, glass tower, corner shop, cafe storefront, market storefront, bookstore storefront, concrete midrise, or stucco walkup, with style-specific facades and proportions. The context sampler reserves more slots for large buildings/storefronts and adds off-road greenery slots so full-bleed sidewalk regions are visually populated without changing answer semantics. These context objects are visual context only and are excluded from the answer candidates. The finalized trace records the sampled `intersection_layout`, the sampled intersection-center world coordinate, and jittered context placement.

## Annotation Contract
Annotation is the bounding box of the selected street object in the scene. Road markings, the intersection center, unlettered context objects, the option panel, and option text are not annotation.

## Prompt And Trace
The prompt bundle is `three_d_street_v0` under `prompts/three_d/street/`. The trace records camera pose, projection frame, scene variant, intersection layout, intersection center, full-bleed floor polygon mode/bounds, candidate ground positions, candidate ground distances to the intersection center, near-to-far ground-distance order, selected object id/type, context building styles, projected object bboxes, and option-panel descriptors/bboxes.

## Calibration
Fresh v0 task review, distribution check, scene review, and qwen25vl7b solve-rate calibration are pending. Only artifacts generated from current code/config with `calibration_baseline: "v0"` should be used as current acceptance annotation.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and annotation come from the same finalized 3D street scene trace.

# `task_three_d__street__intersection_nearest_label`

## Summary
- Domain: `three_d`
- Scene id: `street`
- Task group: `street`
- Query id: `closest_to_intersection`
- Answer type: `option_letter`
- Evidence type: one-box `bbox_set`
- Status: reviewed_pending_probe

## Contract
The image shows a synthetic perspective 3D street intersection or T intersection with roads, sidewalks, crosswalk markings, unlettered street context, and lettered street objects. The street surface renders full-bleed: sidewalk ground fills the canvas and road strips are clipped to the visible floor-plane polygon, so the roads continue to the image edges rather than ending at a finite stage boundary. The prompt asks which lettered street object is closest to the center of the intersection.

Each instance renders `6` lettered candidate street objects, such as cars, taxis, vans, buses, trucks, scooters, motorcycles, bicycles, pedestrians, traffic cones, fire hydrants, trash bins, mailboxes, construction barriers, or road barrels. Exactly one candidate has the smallest finalized ground-plane distance from its object center to the intersection center, with a margin from the next-nearest candidate.

The street context includes unlettered objects such as buildings, storefronts, trees, shrubs, traffic lights, street signs, and benches. Buildings have recorded non-semantic `building_style` attrs such as glass office, brick apartment, glass tower, corner shop, cafe storefront, market storefront, bookstore storefront, concrete midrise, or stucco walkup, with style-specific facades and proportions. The context sampler reserves more slots for large buildings/storefronts and adds off-road greenery slots so full-bleed sidewalk regions are visually populated without changing answer semantics. These context objects are visual context only and are excluded from the answer candidates. The finalized trace records the sampled `intersection_layout`, the sampled intersection-center world coordinate, and jittered context placement.

## Evidence Contract
Evidence is the bounding box of the selected lettered street object. The bbox includes the option letter when rendered. Road markings, the intersection center, and unlettered context objects are not evidence.

## Prompt And Trace
The prompt bundle is `three_d_street_v0` under `prompts/three_d/street/`. The trace records camera pose, projection frame, scene variant, intersection layout, intersection center, full-bleed floor polygon mode/bounds, candidate ground positions, candidate ground distances to the intersection center, near-to-far ground-distance order, selected object id/type, context building styles, and projected object bboxes.

## Calibration
The manual review workbook, distribution report, and combined street scene review have been regenerated. Distribution review passed with `6` unique answers and max answer frequency `0.210`; solve-rate calibration is pending.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and evidence come from the same finalized 3D street scene trace.

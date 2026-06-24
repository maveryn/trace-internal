# `task_illustrations__isometric_harbor__boat_heading_status_count`

## Summary
- Domain: `illustrations`
- Scene id: `isometric_harbor`
- Implementation scene package: `isometric_harbor`
- Implementation source: `trace/tasks/illustrations/isometric_harbor/boat_heading_status_count.py`

## Task Contract
Counts open-water boats by whether their bow faces toward or away from the shoreline in an isometric harbor scene.

## Program Contract
`count(boat where heading_relative_to_shoreline(boat)=heading_status); scene=isometric_harbor; scope=boat_heading_status_count`

## Query Branches

| Query id | Program schema |
| --- | --- |
| `toward_shoreline_boat_count` | `count(boat where heading_relative_to_shoreline(boat)=toward_shoreline); scene=isometric_harbor; scope=boat_heading_status_count` |
| `away_from_shoreline_boat_count` | `count(boat where heading_relative_to_shoreline(boat)=away_from_shoreline); scene=isometric_harbor; scope=boat_heading_status_count` |

## Program Metadata
- Program signatures: `count.directional_orientation_filter`
- Base program contract: `count(boat where heading_relative_to_shoreline(boat)=heading_status); scene=isometric_harbor; scope=boat_heading_status_count`
- Parameter axes: `canvas_profile`, `target_count`, `heading_status_counts`, `dock_position`, `candidate_boat_tile_placement`, `boat_palette`, `shoreline_tiles`, `water_palette`
- Arguments:
  - `heading_status`: shoreline-relative heading; allowed `toward_shoreline|away_from_shoreline`; source `query_id`
  - `boat`: open-water entity with `object_type=boat`; source `scene_ir.entities[]`
  - `heading_relative_to_shoreline`: renderer-assigned heading metadata from the boat orientation; source `scene_ir.entities[].metadata.heading_status`
  - `shoreline`: land-water boundary at the top of the harbor water field; source `scene_ir.relations`
- Argument metadata status: `curated`
- Supported query ids: `toward_shoreline_boat_count`, `away_from_shoreline_boat_count`
- `scalar_annotation_checked`: not applicable; annotation schema is `bbox_set`

## Answer Contract
- Answer schema: `integer`
- Generator `answer_gt.type`: `integer`
- Answer range: `1..5`

## Annotation Contract
- Annotation schema: `bbox_set`
- Generator `annotation_gt.type`: `bbox_set`
- Annotation contains one bounding box for each counted boat.

## Prompt And Trace Requirements
- Prompt text must come from `prompts/illustrations/isometric_harbor/illustrations_isometric_harbor_v1.json`.
- Prompts must refer to boats facing toward or away from the shoreline, not screen-up/down.
- Render-only attributes such as boat color, exact open-water tile, dock jitter, canvas profile, opposite-heading count, and water/land palette must not be query ids.

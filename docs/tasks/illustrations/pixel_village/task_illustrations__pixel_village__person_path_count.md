# `task_illustrations__pixel_village__person_path_count`

## Summary
- Domain: `illustrations`
- Scene id: `pixel_village`
- Implementation scene package: `pixel_village`
- Implementation source: `trace/tasks/illustrations/pixel_village/person_path_count.py`

## Task Contract
Counts people whose occupied tile footprint intersects a visible path tile in a top-down pixel village.

## Program Contract
`count(filter(pixel_village_people, intersects(tile_footprint(person), path_tiles))); scene=pixel_village; scope=person_path_count`

## Query Branches

| Query id | Program schema |
| --- | --- |
| `single` | `count(filter(pixel_village_people, intersects(tile_footprint(person), path_tiles))); scene=pixel_village; scope=person_path_count` |

## Program Metadata
- Program signatures: `count.spatial_relation`
- Base program contract: `count(filter(pixel_village_people, intersects(tile_footprint(person), path_tiles))); scene=pixel_village; scope=person_path_count`
- Parameter axes: `path_person_count`
- Arguments:
  - `person`: semantic_role; allowed `pixel_village_person`; source `program_schema_concrete`
  - `pixel_village_people`: semantic_role; allowed `visible_pixel_village_people`; source `program_schema_concrete`
  - `path_tiles`: semantic_role; allowed `visible_pixel_village_path_tiles`; source `scene_trace`
- Argument metadata status: `curated`
- Supported query ids: `single`

## Answer Contract
- Answer schema: `integer_count`
- Generator `answer_gt.type`: `integer`
- The answer value is a positive integer derived from the same execution trace as the annotation.
- Non-counted background people must be rendered outside the configured one-tile path clearance neighborhood.

## Annotation Contract
- Annotation schema: `point_set`
- Generator `annotation_gt.type`: `point_set`
- Annotation is an unordered set of final-image pixel points, one near the center of each counted person on a path.
- Annotation must not include the path tiles themselves or context-only village regions.

## Prompt And Trace Requirements
- Prompt text must come from the illustrations counting prompt bundle.
- Public prompts use `people` or `person`, not the internal renderer label `villager`.
- Path membership is defined by metadata tile-footprint intersection, not pixel-color inference.
- Counted person ids, path tiles, background-person path clearance, renderer metadata, projected points, and diagnostic bboxes must be recorded in the trace.

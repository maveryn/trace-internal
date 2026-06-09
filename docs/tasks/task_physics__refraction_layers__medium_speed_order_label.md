# `task_physics__refraction_layers__medium_speed_order_label`

## Summary
- Domain: `physics`
- Scene id: `refraction_layers`
- Implementation task group: `optics`
- Implementation source: `trace/tasks/physics/optics/refraction_layers.py`
- Contract-v0 migration decision: `new_extension_task`
- Public mapping: `task_physics__refraction_layers__medium_speed_order_label` -> `task_physics__refraction_layers__medium_speed_order_label`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Selects the visible option that orders three labeled media by light speed from fastest to slowest, inferred from ray bending at the media interfaces.

This public task id is a stable contract-v0 unit: one physics scene id plus one objective contract. Query ids may vary only narrow operands or parameters inside that same program contract.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `three_medium_speed_order` | `option_letter(order_by_speed(media_m1_m2_m3, inferred_from=ray_bending_at_interfaces)); scene=refraction_layers; scope=medium_speed_order_label; query_branch=three_medium_speed_order` |

## Program Metadata
- Program signatures: `physics.refraction_medium_speed_order_label`
- Base program contract: `option_letter(order_by_speed(media_m1_m2_m3, inferred_from=ray_bending_at_interfaces)); scene=refraction_layers; scope=medium_speed_order_label`
- Parameter axes: `fixed_query`
- Arguments:
  - `media_m1_m2_m3`: semantic_role; allowed `visible_labeled_media_regions`; source `program_schema_concrete`
  - `ray_bending_at_interfaces`: semantic_role; allowed `visible_ray_path_and_normals`; source `program_schema_concrete`
  - `option_map`: semantic_role; allowed `visible_speed_order_options`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `three_medium_speed_order`

## Answer Contract
- Answer schema: `option_letter`
- Generator `answer_gt.type`: `option_letter`
- The answer value is the selected visible option letter.

## Annotation Contract
- Annotation schema: `keyed_bbox_map`
- Generator `annotation_gt.type`: `keyed_bbox_map`
- Annotation is keyed because the two interface bends are ordered witnesses; keys include `interface_1_bend` and `interface_2_bend`.
- Annotation must mark minimal visual witnesses from the final rendered diagram, not answer labels, option choices, decorative chrome, full media regions, or derived hidden speed ranks.
- Annotation and answer must be projected from the same generated execution trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the physics prompt bundles, with scene and task/query layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, query operands, hidden medium speed ranks, option placement, and verifier payloads must be explicit in the instance trace.
- Diagrams must keep the media labels, ray path, interface normals, and answer options visible; numeric refractive-index or speed labels are intentionally omitted.

## Review Artifacts
- Task review artifacts: `review/task-reviews/physics/refraction_layers/task_physics__refraction_layers__medium_speed_order_label/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.

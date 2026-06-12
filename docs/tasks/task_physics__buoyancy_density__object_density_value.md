# `task_physics__buoyancy_density__object_density_value`

## Summary
- Domain: `physics`
- Scene id: `buoyancy_density`
- Implementation scene: `fluids`
- Implementation source: `trace/tasks/physics/fluids/buoyancy_density.py`
- Contract-v0 migration decision: `new_extension_task`
- Public mapping: `task_physics__buoyancy_density__object_density_value` -> `task_physics__buoyancy_density__object_density_value`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Computes the density of a floating object from the visible submerged fraction and the shown liquid density.

This public task id is a stable contract-v0 unit: one physics scene id plus one objective contract. Query ids may vary only narrow operands such as submerged fraction, liquid density, scene variant, object shape, and target answer inside that same program contract.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `floating_object_density_value` | `liquid_density * submerged_fraction(floating_object, waterline, equal_part_marker); scene=buoyancy_density; scope=object_density_value; query_branch=floating_object_density_value` |

## Program Metadata
- Program signatures: `physics.buoyancy_object_density`
- Base program contract: `liquid_density * submerged_fraction(floating_object, waterline, equal_part_marker); scene=buoyancy_density; scope=object_density_value`
- Parameter axes: `scene_variant`, `object_shape`, `submerged_fraction`, `liquid_density`, `target_answer`
- Arguments:
  - `floating_object`: semantic_role; allowed `visible_divided_floating_body`; source `program_schema_concrete`
  - `waterline`: semantic_role; allowed `visible_liquid_surface_crossing_object`; source `program_schema_concrete`
  - `equal_part_marker`: semantic_role; allowed `visible_equal_division_marker`; source `program_schema_concrete`
  - `liquid_density`: query_operand; allowed `visible_density_label_g_cm3`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `floating_object_density_value`

## Answer Contract
- Answer schema: `number`
- Generator `answer_gt.type`: `number`
- The answer value is the object density in `g/cm^3` as a decimal number.

## Annotation Contract
- Annotation schema: `keyed_bbox_map`
- Generator `annotation_gt.type`: `keyed_bbox_map`
- Annotation is keyed because witness roles are distinct; keys are `floating_object`, `waterline`, `fluid_density_label`, and `submerged_fraction_marker`.
- Annotation must mark minimal visual witnesses from the final rendered diagram. It must not mark derived answer text, decorative tank chrome, background grid lines, title text, or non-witness labels.
- Annotation and answer must be projected from the same generated execution trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the physics prompt bundles, with scene and task/query layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, scene variant, object shape, submerged fraction, liquid density, target answer, and verifier payloads must be explicit in the instance trace.
- Diagrams must keep the liquid surface, floating object divisions, fraction marker, and liquid-density label readable.
- Object color, liquid color, object shape, and scene variant are non-semantic visual variation axes and must not be tied to the answer.

## Review Artifacts
- Task review artifacts: `review/task-reviews/physics/buoyancy_density/task_physics__buoyancy_density__object_density_value/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.

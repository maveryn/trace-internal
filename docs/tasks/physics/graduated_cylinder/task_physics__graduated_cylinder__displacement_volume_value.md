# `task_physics__graduated_cylinder__displacement_volume_value`

## Summary
- Domain: `physics`
- Scene id: `graduated_cylinder`
- Implementation scene: `fluids`
- Implementation source: `trace/tasks/physics/fluids/graduated_cylinder.py`

## Task Contract
Computes displaced volume from before/after graduated-cylinder readings.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `before_after_displacement_volume` | `read_scale_value(after_meniscus, graduated_scale) - read_scale_value(before_meniscus, graduated_scale); scene=graduated_cylinder; scope=displacement_volume_value; query_branch=before_after_displacement_volume` |

## Program Metadata
- Program signatures: `physics.graduated_cylinder_displacement_volume`
- Base program contract: `read_scale_value(after_meniscus, graduated_scale) - read_scale_value(before_meniscus, graduated_scale); scene=graduated_cylinder; scope=displacement_volume_value`
- Parameter axes: `fixed_query`
- Arguments:
  - `before_meniscus`: semantic_role; allowed `visible_before_liquid_level`; source `program_schema_concrete`
  - `after_meniscus`: semantic_role; allowed `visible_after_liquid_level`; source `program_schema_concrete`
  - `graduated_scale`: semantic_role; allowed `matched_visible_tick_scales_with_mL_units`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `before_after_displacement_volume`

## Answer Contract
- Answer schema: `integer_value`
- Generator `answer_gt.type`: `integer`
- The answer value is the exact integer mL increase from the before reading to the after reading.

## Annotation Contract
- Annotation schema: `keyed_bbox_map`
- Generator `annotation_gt.type`: `keyed_bbox_map`
- Annotation is keyed because before/after witness roles are distinct; keys include `before_meniscus`, `before_scale_region`, `after_meniscus`, and `after_scale_region`.
- Annotation must mark minimal visual witnesses from the final rendered diagram, not answer labels, option choices, decorative chrome, or derived numeric annotations unless those are the queried visual witnesses.
- Annotation and answer must be projected from the same generated execution trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the physics prompt bundles, with scene and task/query layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, query operands, formula quantities, and verifier payloads must be explicit in the instance trace.
- Diagrams must keep all quantities required for the physics computation visible or explicitly stated by the task prompt contract.

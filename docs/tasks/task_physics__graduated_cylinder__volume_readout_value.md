# `task_physics__graduated_cylinder__volume_readout_value`

## Summary
- Domain: `physics`
- Scene id: `graduated_cylinder`
- Implementation task group: `fluids`
- Implementation source: `trace/tasks/physics/fluids/graduated_cylinder.py`
- Contract-v0 migration decision: `new_extension_task`
- Public mapping: `task_physics__graduated_cylinder__volume_readout_value` -> `task_physics__graduated_cylinder__volume_readout_value`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Reads the liquid volume from one visible graduated cylinder using the meniscus and scale.

This public task id is a stable contract-v0 unit: one physics scene id plus one objective contract. Query ids may vary only narrow operands or parameters inside that same program contract.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `single_cylinder_volume_readout` | `read_scale_value(meniscus, graduated_scale, unit=mL); scene=graduated_cylinder; scope=volume_readout_value; query_branch=single_cylinder_volume_readout` |

## Program Metadata
- Program signatures: `physics.graduated_cylinder_volume_readout`
- Base program contract: `read_scale_value(meniscus, graduated_scale, unit=mL); scene=graduated_cylinder; scope=volume_readout_value`
- Parameter axes: `fixed_query`
- Arguments:
  - `meniscus`: semantic_role; allowed `visible_liquid_level`; source `program_schema_concrete`
  - `graduated_scale`: semantic_role; allowed `visible_tick_scale_with_mL_units`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `single_cylinder_volume_readout`

## Answer Contract
- Answer schema: `integer_value`
- Generator `answer_gt.type`: `integer`
- The answer value is the exact integer mL value shown by the scale.

## Annotation Contract
- Annotation schema: `keyed_bbox_map`
- Generator `annotation_gt.type`: `keyed_bbox_map`
- Annotation is keyed because witness roles are distinct; keys include `meniscus` and `scale_region`.
- Annotation must mark minimal visual witnesses from the final rendered diagram, not answer labels, option choices, decorative chrome, or derived numeric annotations unless those are the queried visual witnesses.
- Annotation and answer must be projected from the same generated execution trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the physics prompt bundles, with scene and task/query layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, query operands, formula quantities, and verifier payloads must be explicit in the instance trace.
- Diagrams must keep all quantities required for the physics computation visible or explicitly stated by the task prompt contract.

## Review Artifacts
- Task review artifacts: `review/task-reviews/physics/graduated_cylinder/task_physics__graduated_cylinder__volume_readout_value/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.

# `task_physics__fluid_flow__continuity_speed_value`

## Summary
- Domain: `physics`
- Scene id: `fluid_flow`
- Implementation scene: `fluids`
- Implementation source: `trace/tasks/physics/fluids/fluid_flow.py`

## Task Contract
Computes a missing steady-flow speed from a two-station pipe/nozzle diagram using incompressible-flow continuity.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `continuity_missing_speed` | `integer(solve(A1 * v1 = A2 * v2, unknown_speed)); scene=fluid_flow; scope=continuity_speed_value` |

## Program Metadata
- Program signatures: `physics.fluid_flow_continuity_speed`
- Base program contract: `integer(solve_continuity_speed(area_1_cm2, speed_1_m_s, area_2_cm2, speed_2_m_s, unknown_speed_slot)); scene=fluid_flow; scope=continuity_speed_value`
- Parameter axes: `orientation`, `missing_speed_station`, `area_1_cm2`, `area_2_cm2`, `speed_1_m_s`, `speed_2_m_s`
- Arguments:
  - `station_1`: query_operand; allowed `visible_station_1_area_and_speed_labels`; source `program_schema_concrete`
  - `station_2`: query_operand; allowed `visible_station_2_area_and_speed_labels`; source `program_schema_concrete`
  - `flow_path`: semantic_role; allowed `visible_pipe_or_nozzle_with_flow_arrow`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `continuity_missing_speed`

## Answer Contract
- Answer schema: `integer`
- Generator `answer_gt.type`: `integer`
- The answer value is the missing positive integer flow speed in `m/s`.

## Annotation Contract
- Annotation schema: `keyed_bbox_map`
- Generator `annotation_gt.type`: `keyed_bbox_map`
- Annotation keys: `station_1`, `station_2`, `flow_path`
- Annotation must mark the minimal visible witnesses needed to compute the missing speed. It must not mark decorative background grid lines, panel framing, or derived answer text.
- Annotation and answer must be projected from the same generated execution trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the physics fluids prompt bundle, with scene and task/query layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, station areas, station speeds, missing station, orientation, fluid color, and verifier payloads must be explicit in the instance trace.
- Diagrams must keep both station labels readable, show one clear missing speed label, and use explicit area labels rather than diameter labels in the first calibrated version.

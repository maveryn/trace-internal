# `task_physics__circuit_equivalent__total_capacitance_value`

## Summary
- Domain: `physics`
- Scene id: `circuit_equivalent`
- Implementation scene: `circuits`
- Implementation source: `trace/tasks/physics/circuits/equivalent_resistance.py`

## Task Contract
Computes equivalent capacitance for a visible mixed series-parallel capacitor network between terminals A and B.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `total_capacitance` | `equivalent_capacitance(components=capacitor_components_between_terminals, topology=series_parallel_network); scene=circuit_equivalent; scope=total_capacitance_value; query_branch=total_capacitance` |

## Program Metadata
- Program signatures: `physics.equivalent_circuit_value`
- Base program contract: `equivalent_capacitance(components=capacitor_components_between_terminals, topology=series_parallel_network); scene=circuit_equivalent; scope=total_capacitance_value`
- Parameter axes: `fixed_query`
- Arguments:
  - `capacitor_components_between_terminals`: semantic_role; allowed `visible_capacitors_between_A_B`; source `program_schema_concrete`
  - `series_parallel_network`: semantic_role; allowed `mixed_series_parallel_topology`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `total_capacitance`

## Answer Contract
- Answer schema: `integer_value`
- Generator `answer_gt.type`: `integer`
- The answer value is an exact integer produced by the symbolic physics construction.

## Annotation Contract
- Annotation schema: `keyed_bbox_map`
- Generator `annotation_gt.type`: `keyed_bbox_map`
- Annotation is keyed because witness roles are distinct; each key maps to the minimal final-image pixel box for that role.
- Annotation must mark minimal visual witnesses from the final rendered diagram, not answer labels, option choices, decorative chrome, or derived numeric annotations unless those are the queried visual witnesses.
- Annotation and answer must be projected from the same generated execution trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the physics prompt bundles, with scene and task/query layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, query operands, formula quantities, and verifier payloads must be explicit in the instance trace.
- Diagrams must keep all quantities required for the physics computation visible or explicitly stated by the task prompt contract.

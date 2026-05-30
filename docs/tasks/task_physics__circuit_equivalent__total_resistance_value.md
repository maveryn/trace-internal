# `task_physics__circuit_equivalent__total_resistance_value`

- Domain: `physics`
- Task group: `circuits`
- Scene id: `circuit_equivalent`
- Query id: `total_resistance`
- Answer type: integer
- Evidence type: `keyed_bbox_map`

Technical circuit diagram with labeled zigzag resistors between terminals `A` and `B`. Every generated diagram contains at least one resistor in series with one or two parallel resistor blocks.

Evidence maps each visible resistor label, such as `R1` or `R2`, to the bounding box around that resistor symbol and its value label. Wires and terminal labels are not separate evidence.

The mixed topology filters configured integer answer support to constructively feasible values; with the default component-value range this yields total resistance answers `2..20`.

Prompt bundle: `physics_circuits_v0`; scene key: `equivalent_circuit_diagram`; task key: `equivalent_component_query`; query key: `total_resistance`.

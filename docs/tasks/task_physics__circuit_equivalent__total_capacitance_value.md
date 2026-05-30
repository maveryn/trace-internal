# `task_physics__circuit_equivalent__total_capacitance_value`

- Domain: `physics`
- Task group: `circuits`
- Scene id: `circuit_equivalent`
- Query id: `total_capacitance`
- Answer type: integer
- Evidence type: `keyed_bbox_map`

Technical circuit diagram with labeled parallel-plate capacitors between terminals `A` and `B`. Every generated diagram contains at least one capacitor in series with one or two parallel capacitor blocks.

Evidence maps each visible capacitor label, such as `C1` or `C2`, to the bounding box around that capacitor symbol and its value label. Wires and terminal labels are not separate evidence.

Prompt bundle: `physics_circuits_v0`; scene key: `equivalent_circuit_diagram`; task key: `equivalent_component_query`; query key: `total_capacitance`.

# `task_physics__pv_diagram__pv_work_value`

## Summary
- Domain: `physics`
- Scene id: `pv_diagram`
- Task group: `thermodynamics`
- Query id: `work_value`
- Answer type: `integer`
- Evidence type: unordered `bbox_set`

## Contract
The image shows a pressure-volume diagram with pressure in `kPa`, volume in `L`, and a highlighted PV process or rectangular cycle. The prompt asks for signed work done by the gas in joules, using `1 kPa*L = 1 J`.

The calibrated public sampling uses the `single_process` work mode. For a single horizontal process, work is `P * (V_final - V_initial)`; expansion is positive and compression is negative. The renderer still supports explicit rectangular-cycle construction for regression coverage, but rectangular cycles are not part of the current default numeric-work calibration mix.

## Evidence
Prompt-facing evidence is one bounding box around the highlighted PV process or cycle used to compute the work.

## Prompt And Trace
Prompt bundle: `physics_thermodynamics_v0`; scene key: `thermodynamics_pv_diagram`; task key: `pv_diagram_query`; query key: `work_value`.

Public outputs use `query_variant="default"` and `query_id="work_value"`. The current calibrated task uses the single horizontal process mode: the answer is `pressure * (final volume - initial volume)` with expansion positive and compression negative. The trace records the resolved work mode, pressure/volume values, signed work value, axis metadata, rendered witness bbox, and evidence entity ids.

## Determinism
Generation is deterministic from `instance_seed`. Answers and evidence come from the same finalized PV scenario.

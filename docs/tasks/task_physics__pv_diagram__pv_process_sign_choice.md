# `task_physics__pv_diagram__pv_process_sign_choice`

## Summary
- Domain: `physics`
- Scene id: `pv_diagram`
- Task group: `thermodynamics`
- Query id: `process_sign_choice`
- Answer type: `option_letter`
- Evidence type: unordered `bbox_set`

## Contract
The image shows eight labeled mini pressure-volume process diagrams. Each candidate process has a direction arrow on PV axes. The task asks which labeled process has the requested work sign for work done by the gas.

The internal `target_sign` is `positive|negative|zero`. The generator constructs exactly one candidate whose sign matches the target: rightward volume change is positive, leftward volume change is negative, and vertical constant-volume motion is zero.

## Evidence
Prompt-facing evidence is one bounding box around the correct labeled candidate process.

## Prompt And Trace
Prompt bundle: `physics_thermodynamics_v0`; scene key: `thermodynamics_pv_diagram`; task key: `pv_diagram_query`; query key: `process_sign_choice`.

Public outputs use `query_variant="default"` and `query_id="process_sign_choice"`. The trace records the target sign, candidate option letters, per-option start/end pressure and volume, per-option sign, the correct option letter, and evidence entity ids.

## Determinism
Generation is deterministic from `instance_seed`. Answers and evidence come from the same finalized candidate set.

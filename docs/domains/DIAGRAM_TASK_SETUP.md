# Diagrams Task Setup

This document captures the concrete reusable setup for the first `diagrams` task family.

## 1) Domain scope
1. `domain=diagrams` is for schematic visual reasoning over process diagrams, swimlanes, hierarchies, cycles, and set-overlap diagrams.
2. The first family focuses on `flow` reasoning over labeled process nodes connected by visible arrows.
3. Diagram tasks should stay diagram-native:
   - explicit node/connector semantics,
   - short visible labels,
   - local evidence on the target diagram element.
4. Avoid treating generic graph tasks with free node placement as `diagrams`; those belong in `graph`.

## 2) First reusable scene contract
1. V1 flow scenes use one diagram panel on a light background.
2. The first active scene variants are:
   - `flowchart`
   - `swimlane`
3. Every scene variant keeps the same semantic contract:
   - visible labeled steps,
   - visible arrows between steps,
   - one queried next-step relationship grounded on the rendered connectors.
4. The swimlane scene adds horizontal lane bands and lane labels, but it should not change the meaning of the process arrows.

## 3) Active family
1. `task_group=flow`
2. Active task:
   - `task_diagrams_flow_next_step_label`
3. Active semantic variants:
   - `direct_next_step`
   - `branch_next_step`
4. Active visual variants:
   - `flowchart`
   - `swimlane`

## 4) Evidence policy
1. Flow next-step tasks should keep prompt-facing evidence local:
   - `bbox_set` with exactly one bbox for the target next-step node.
2. Keep query-node, lane, and edge-label geometry in trace for review/debugging, but do not widen prompt-facing evidence to the whole path when the answer is one visible target node.

## 5) Reuse guidance
1. Keep diagram-axis resolution and prompt-facing bbox projection under `trace/tasks/diagrams/shared/common.py`.
2. Keep shared diagrams complexity helpers under `trace/tasks/diagrams/shared/complexity.py`.
3. Keep diagrams background/noise fallback loading under `trace/tasks/diagrams/shared/visual_defaults.py`.
4. Keep flow-specific dataset construction, axis resolution, and render-param resolution under `trace/tasks/diagrams/shared/flow_common.py`.
5. Keep flowchart/swimlane rendering, node/edge/lane tracing, and panel chrome under `trace/tasks/diagrams/shared/flow_scene.py`.
6. Future flow-family tasks should reuse the same diagram grammar before adding a second renderer.

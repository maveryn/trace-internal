# Diagrams Task Setup

This document captures the concrete reusable setup for the active early `diagrams` task families.

## 1) Domain scope
1. `domain=diagrams` is for schematic visual reasoning over process diagrams, swimlanes, hierarchies, cycles, and set-overlap diagrams.
2. The first active families focus on:
   - `flow` reasoning over labeled process nodes connected by visible arrows,
   - `hierarchy` reasoning over labeled org charts connected by visible parent-child lines.
3. Diagram tasks should stay diagram-native:
   - explicit node/connector semantics,
   - short visible labels,
   - local evidence on the target diagram element.
4. Avoid treating generic graph tasks with free node placement as `diagrams`; those belong in `graph`.

## 2) First reusable scene contracts
1. V1 diagram scenes use one diagram panel on a light background.
2. The first active flow scene variants are:
   - `flowchart`
   - `swimlane`
3. The first active hierarchy scene variants are:
   - `org_chart`
4. Every flow scene variant keeps the same semantic contract:
   - visible labeled steps,
   - visible arrows between steps,
   - one queried next-step relationship grounded on the rendered connectors.
5. The swimlane scene adds horizontal lane bands and lane labels, but it should not change the meaning of the process arrows.
6. The org-chart scene adds top-down rooted-tree structure, but it should not change the meaning of the parent-child connectors.

## 3) Active family
1. `task_group=flow`
2. Active flow task:
   - `task_diagrams_flow_next_step_label`
3. Active flow semantic variants:
   - `direct_next_step`
   - `branch_next_step`
4. Active flow visual variants:
   - `flowchart`
   - `swimlane`
5. `task_group=hierarchy`
6. Active hierarchy task:
   - `task_diagrams_hierarchy_ancestor_label`
7. Active hierarchy semantic variants:
   - `parent_of_node`
   - `lowest_common_ancestor_of_two_nodes`
8. Active hierarchy visual variants:
   - `org_chart`

## 4) Evidence policy
1. Flow next-step tasks should keep prompt-facing evidence local:
   - `bbox_set` with exactly one bbox for the target next-step node.
2. Hierarchy ancestor tasks should keep prompt-facing evidence local:
   - `bbox_set` with exactly one bbox for the target parent or common-ancestor node.
3. Keep query-node, lane, edge-label, and connector geometry in trace for review/debugging, but do not widen prompt-facing evidence to whole paths or full subtrees when the answer is one visible target node.

## 5) Reuse guidance
1. Keep diagram-axis resolution, prompt-facing bbox projection, and reusable panel/title helpers under `trace/tasks/diagrams/shared/common.py`.
2. Keep shared diagrams complexity helpers under `trace/tasks/diagrams/shared/complexity.py`.
3. Keep diagrams background/noise fallback loading under `trace/tasks/diagrams/shared/visual_defaults.py`.
4. Keep flow-specific dataset construction, axis resolution, and render-param resolution under `trace/tasks/diagrams/shared/flow_common.py`.
5. Keep flowchart/swimlane rendering, node/edge/lane tracing, and panel chrome under `trace/tasks/diagrams/shared/flow_scene.py`.
6. Keep hierarchy-specific dataset construction, axis resolution, and render-param resolution under `trace/tasks/diagrams/shared/hierarchy_common.py`.
7. Keep org-chart rendering, connector routing, and traced node/edge bbox maps under `trace/tasks/diagrams/shared/hierarchy_scene.py`.
8. Future flow-family tasks should reuse the same diagram grammar before adding a second renderer, and future hierarchy tasks should reuse the same org-chart grammar before adding a second hierarchy renderer.

# Diagrams Task Setup

This document captures the concrete reusable setup for the active early `diagrams` task families.

## 1) Domain scope
1. `domain=diagrams` is for schematic visual reasoning over process diagrams, swimlanes, hierarchies, cycles, set-overlap diagrams, and annotated schematics.
2. The first active families focus on:
   - `flow` reasoning over labeled process nodes connected by visible arrows,
   - `hierarchy` reasoning over labeled org charts connected by visible parent-child lines,
   - `cycle` reasoning over labeled directed stage rings,
   - `set_diagram` reasoning over explicit set-overlap regions,
   - `schematic` reasoning over annotated parts connected to visible external callouts.
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
7. The cycle-ring scene adds a single clockwise stage loop, but it should not change the meaning of the directed cycle order across the `before` and `after` query variants.
8. The set-diagram scene adds one numeric `3`-set overlap layout, but it should not change the meaning of the explicit set-sum semantics named in the prompt.
9. The schematic scene adds one annotated part-and-callout layout, but it should not change the meaning of the target-part-to-callout mapping named in the prompt.

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
9. `task_group=cycle`
10. Active cycle task:
   - `task_diagrams_cycle_offset_stage_label`
11. Active cycle semantic variants:
   - `after_k_steps`
   - `before_k_steps`
12. Active cycle visual variants:
   - `cycle_ring`
13. `task_group=set_diagram`
14. Active set-diagram task:
   - `task_diagrams_set_diagram_region_sum_value`
15. Active set-diagram semantic variants:
   - `sum_only_in_named_set`
   - `sum_in_named_set`
   - `sum_in_named_union`
   - `sum_in_named_intersection`
   - `sum_in_exactly_two_sets`
16. Active set-diagram visual variants:
   - `set_diagram`
17. `task_group=schematic`
18. Active schematic task:
   - `task_diagrams_schematic_callout_target_label`
19. Active schematic semantic variants:
   - `callout_for_named_part`
   - `callout_for_highlighted_part`
20. Active schematic visual variants:
   - `annotated_schematic`

## 4) Evidence policy
1. Flow next-step tasks should keep prompt-facing evidence local:
   - `bbox_set` with exactly one bbox for the target next-step node.
2. Hierarchy ancestor tasks should keep prompt-facing evidence local:
   - `bbox_set` with exactly one bbox for the target parent or common-ancestor node.
3. Cycle offset-stage tasks should keep prompt-facing evidence local:
   - `bbox_set` with exactly one bbox for the target stage.
4. Set-diagram region-sum tasks should keep prompt-facing evidence local:
   - `bbox_set` with one bbox per contributing digit, ordered from top to bottom and then left to right.
5. Schematic callout-target tasks should keep prompt-facing evidence local:
   - `bbox_set` with exactly one bbox for the queried target part.
6. Keep query-node, lane, edge-label, connector, and region geometry in trace for review/debugging, but do not widen prompt-facing evidence to whole paths, full subtrees, whole loops, or whole regions when the answer depends on a local set of visible digits.
7. Keep callout-badge and leader-line geometry in trace for review/debugging, but do not widen prompt-facing evidence to the answer badge when the reasoning target is the part itself.

## 5) Reuse guidance
1. Keep diagram-axis resolution, prompt-facing bbox projection, and reusable panel/title helpers under `trace/tasks/diagrams/shared/common.py`.
2. Keep shared diagrams complexity helpers under `trace/tasks/diagrams/shared/complexity.py`.
3. Keep diagrams background/noise fallback loading under `trace/tasks/diagrams/shared/visual_defaults.py`.
4. Keep flow-specific dataset construction, axis resolution, and render-param resolution under `trace/tasks/diagrams/shared/flow_common.py`.
5. Keep flowchart/swimlane rendering, node/edge/lane tracing, and panel chrome under `trace/tasks/diagrams/shared/flow_scene.py`.
6. Keep hierarchy-specific dataset construction, axis resolution, and render-param resolution under `trace/tasks/diagrams/shared/hierarchy_common.py`.
7. Keep org-chart rendering, connector routing, and traced node/edge bbox maps under `trace/tasks/diagrams/shared/hierarchy_scene.py`.
8. Keep cycle-specific dataset construction, axis resolution, and render-param resolution under `trace/tasks/diagrams/shared/cycle_common.py`.
9. Keep cycle-ring rendering, directed-edge routing, and traced stage/edge bbox maps under `trace/tasks/diagrams/shared/cycle_scene.py`.
10. Keep set-diagram-specific dataset construction, axis resolution, and render-param resolution under `trace/tasks/diagrams/shared/set_common.py`.
11. Keep set-overlap rendering, digit placement, sampled set-palette handling, and traced region/number bbox maps under `trace/tasks/diagrams/shared/set_scene.py` and `trace/tasks/diagrams/shared/set_common.py`.
12. Keep schematic-specific dataset construction, axis resolution, and render-param resolution under `trace/tasks/diagrams/shared/schematic_common.py`.
13. Keep annotated schematic rendering, callout routing, and traced part/callout/leader bbox maps under `trace/tasks/diagrams/shared/schematic_scene.py`.
14. Future flow-family tasks should reuse the same diagram grammar before adding a second renderer, future hierarchy tasks should reuse the same org-chart grammar before adding a second hierarchy renderer, future cycle tasks should reuse the same ring grammar before adding a second cycle renderer, future set-diagram tasks should reuse the same overlap grammar before adding a second set renderer, and future schematic tasks should reuse the same annotated part-and-callout grammar before adding a second schematic renderer.

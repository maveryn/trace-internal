# Diagrams Task-Unit Audit

Task-unit audit for `domain=diagrams` using `docs/workflows/TASK_UNIT_AUDIT.md`.

## Domain summary
1. The diagrams domain is healthy as a task-unit inventory.
2. The active diagrams tasks are narrower than many chart tasks, but that narrowness is mostly appropriate because each task corresponds to a distinct diagram grammar and grounding pattern.
3. No current diagrams task looks like a merge, split, or retire candidate.
4. Recommended domain outcome:
   - `Keep`: `5`
   - `Split`: `0`
   - `Merge`: `0`
   - `Retire`: `0`

## Task findings

### `task_diagrams_flow_next_step_label`
- Outcome: `Keep`
- Why: one coherent process-diagram grounding family with stable local next-step semantics across the flowchart and swimlane renderers.
- Scene variety: moderate (`flowchart|swimlane`) with meaningful diagram-chrome variation.
- Query variety: moderate (`direct_next_step|branch_next_step`)
- Grounding necessity: strong; the model must ground node labels, arrow structure, and optional branch labels in the rendered process diagram.
- Evidence fit: good; single target-node `bbox_set` is local and natural.
- Follow-up: none required now.

### `task_diagrams_hierarchy_ancestor_label`
- Outcome: `Keep`
- Why: one coherent org-chart grounding family with two related hierarchy queries over the same rooted-tree scaffold.
- Scene variety: moderate; fixed org-chart grammar but varied tree shape, depth, and node placement.
- Query variety: moderate (`parent_of_node|lowest_common_ancestor_of_two_nodes`)
- Grounding necessity: strong; the model must identify labeled nodes and reason over visible parent-child structure.
- Evidence fit: good; single target-node `bbox_set` is local and natural.
- Follow-up: none required now.

### `task_diagrams_cycle_offset_stage_label`
- Outcome: `Keep`
- Why: one coherent directed-cycle grounding family with stable ring semantics.
- Scene variety: moderate; fixed cycle-ring scaffold with varied stage count, labels, and offset distance.
- Query variety: moderate (`after_k_steps|before_k_steps`)
- Grounding necessity: strong; the model must use visible direction cues and labeled stage positions.
- Evidence fit: good; single target-stage `bbox_set` is local and natural.
- Follow-up: none required now.

### `task_diagrams_set_diagram_region_sum_value`
- Outcome: `Keep`
- Why: one distinct set-overlap grounding family with consistent region-sum semantics across the active query variants.
- Scene variety: moderate; fixed 3-set scaffold but varied region digits and target-set semantics.
- Query variety: strong (`sum_only_in_named_set|sum_in_named_set|sum_in_named_union|sum_in_named_intersection|sum_in_exactly_two_sets`)
- Grounding necessity: strong; requires matching set semantics to the correct visible regions and digits.
- Evidence fit: good; ordered contributing-digit `bbox_set` stays local and non-vacuous.
- Follow-up: none required now.

### `task_diagrams_schematic_callout_target_label`
- Outcome: `Keep`
- Why: one coherent annotated-schematic grounding family with stable part-to-callout semantics.
- Scene variety: moderate; fixed annotated-schematic grammar with varied part layouts, labels, and leader routing.
- Query variety: moderate (`callout_for_named_part|callout_for_highlighted_part`)
- Grounding necessity: strong; the model must locate the part and follow the matching leader to the callout.
- Evidence fit: good; target-part `bbox_set` is local and keeps the witness on the grounded object rather than the answer badge.
- Follow-up: none required now.

## Recommended next action
1. Leave the diagrams task-unit inventory unchanged for now.
2. Revisit only if future diagrams growth starts adding new tasks that are too thin relative to these core grammar-specific families.

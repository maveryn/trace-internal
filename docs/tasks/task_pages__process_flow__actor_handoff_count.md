# `task_pages__process_flow__actor_handoff_count`

## 1) Identity
1. Domain: `pages`
2. Scene: `process_flow`
3. Task group: `process_flow`
4. Task id: `task_pages__process_flow__actor_handoff_count`
5. Objective: count arrows that transfer work between process lanes.

## 2) Scene + task contract
1. Branch metadata: `query_id`
2. `query_id`: `all_cross_lane_handoff_count|lane_outgoing_handoff_count|lane_involved_handoff_count`
3. `answer_gt.type`: `integer`
4. `evidence_gt.type`: `point_pair_set`
5. Scene contract:
   - process lanes identify actors/work areas,
   - arrows connect visible process steps,
   - a handoff arrow has source and destination steps in different lanes,
   - lane-specific query branches restrict outgoing handoffs or all handoffs involving one lane.

## 3) Evidence + trace contract
1. Evidence is the unordered set of counted handoff-arrow endpoint pairs.
2. `execution_trace.query` records the selected lane condition, answer count, and counted edge ids.
3. `render_map.edge_point_pairs_px` is the source for prompt-facing handoff evidence.

## 4) Visual policy
1. This task stays separate from graph-domain edge counting because the criterion is actor/lane transfer, not graph degree or connectivity.
2. The renderer varies lane orientation, process context, node/arrow text, palettes, and side-arrow styling.
3. Evidence point pairs are generated from rendered arrow geometry after final layout.

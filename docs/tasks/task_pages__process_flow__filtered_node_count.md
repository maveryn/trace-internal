# `task_pages__process_flow__filtered_node_count`

## 1) Identity
1. Domain: `pages`
2. Scene: `process_flow`
3. Task group: `process_flow`
4. Task id: `task_pages__process_flow__filtered_node_count`
5. Objective: count process-flow steps selected by one visible diagram-level include/exclude filter.

## 2) Scene + task contract
1. Branch metadata: `query_id`
2. `query_id`: `shape_node_count|status_node_count|role_node_count`
3. `answer_gt.type`: `integer`
4. `evidence_gt.type`: `bbox_set`
5. Scene contract:
   - a lane-based process-flow diagram is shown,
   - nodes have short labels, visible shapes, and status badges,
   - lane headers define actor/work-area membership,
   - the task asks for a document/process count, not graph reachability or degree.

## 3) Evidence + trace contract
1. Evidence is the unordered set of counted process-step bboxes.
2. `execution_trace.query` records the visible filter, include/exclude mode, answer count, and counted node ids.
3. `render_map.node_bboxes_px` is the source for prompt-facing evidence.

## 4) Visual policy
1. The renderer varies process context, lane names, layout orientation, node labels, shape mix, status badges, palettes, and arrow styling.
2. Visual variation is nonsemantic and deterministic from `instance_seed`.
3. Evidence remains in final-image pixel coordinates after coordinate-preserving post-image noise.

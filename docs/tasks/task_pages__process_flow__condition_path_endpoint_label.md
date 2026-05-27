# `task_pages__process_flow__condition_path_endpoint_label`

## 1) Identity
1. Domain: `pages`
2. Scene: `process_flow`
3. Task group: `process_flow`
4. Task id: `task_pages__process_flow__condition_path_endpoint_label`
5. Objective: follow visible decision-arrow labels in a process-flow diagram and return the reached step label.

## 2) Scene + task contract
1. Public `query_variant`: `default`
2. `query_id`: `condition_path_endpoint_label`
3. `answer_gt.type`: `string`
4. `evidence_gt.type`: `bbox_set`
5. Scene contract:
   - the diagram has ordinary process arrows and labeled decision arrows,
   - the prompt gives the decision labels to follow,
   - unlabeled arrows connect ordinary process steps between decisions,
   - the target answer is the exact visible step label after the final requested decision choice.

## 3) Evidence + trace contract
1. Evidence is ordered path support: followed step boxes plus the used decision-label boxes.
2. `execution_trace.query.condition_labels` records the visible decision labels used by the prompt.
3. `execution_trace.query.path_node_labels` records the symbolic path for audit.

## 4) Visual policy
1. This is intentionally process-semantics traversal, not a graph shortest-path, reachability, cycle, or degree task.
2. The renderer varies process domain, lanes, node labels, layout orientation, palette, and arrow-label vocabulary.
3. All labels are short enough to remain readable in the generated scene review workbook.

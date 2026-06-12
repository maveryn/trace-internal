# `task_pages__process_flow__condition_path_endpoint_label`

## 1) Identity
1. Domain: `pages`
2. Scene: `process_flow`
3. Scene: `process_flow`
4. Task id: `task_pages__process_flow__condition_path_endpoint_label`
5. Objective: follow visible decision-arrow labels in a process-flow diagram and return the reached step label.

## 2) Scene + task contract
1. Branch metadata: `query_id`
2. `query_id`: `condition_path_endpoint_label`
3. `answer_gt.type`: `string`
4. `annotation_gt.type`: `keyed_bbox_map`
5. Scene contract:
   - the diagram has ordinary process arrows and labeled decision arrows,
   - the prompt gives the decision labels to follow,
   - unlabeled arrows connect ordinary process steps between decisions,
   - the target answer is the exact visible step label after the final requested decision choice.

## 3) Annotation + trace contract
1. Annotation is compact keyed path support: `start_step` binds the starting step box, `first_decision_label` and `second_decision_label` bind the two used decision-arrow label boxes, `intermediate_step` binds the step reached after the first choice, and `endpoint_step` binds the final answer step box.
2. `execution_trace.query.condition_labels` records the visible decision labels used by the prompt.
3. `execution_trace.query.path_node_labels` records the symbolic path for audit.

## 4) Visual policy
1. This is intentionally process-semantics traversal, not a graph shortest-path, reachability, cycle, or degree task.
2. The renderer varies process domain, lanes, node labels, layout orientation, palette, and arrow-label vocabulary.
3. All labels are short enough to remain readable in the generated browser-review sidecars.

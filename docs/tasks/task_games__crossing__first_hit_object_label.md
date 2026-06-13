# `task_games__crossing__first_hit_object_label`

## Contract
1. Domain: `games`
2. Scene id: `crossing`
3. Public task id: `task_games__crossing__first_hit_object_label`
4. Supported `query_id` values: `first_hit_object_label`
5. Answer schema: `label_string`
6. Annotation schema: `bbox_set`
7. Program schema: `label(first_collision(marked_route, labeled_moving_objects)); scene=crossing; scope=first_hit_object_label`

## Generation Notes
1. Exactly four moving objects are labeled `A` through `D`; the answer is one of those labels.
2. At least two labeled moving objects collide with the marked route at different ticks.
3. Start pads use numeric labels so they do not conflict with moving-object option labels.
4. Annotation marks only the labeled moving object that reaches the marked route first.

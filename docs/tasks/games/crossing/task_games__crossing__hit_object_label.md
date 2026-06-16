# `task_games__crossing__hit_object_label`

## Contract
1. Domain: `games`
2. Scene id: `crossing`
3. Public task id: `task_games__crossing__hit_object_label`
4. Supported `query_id` values: `single`
5. Answer schema: `label_string`
6. Annotation schema: `point`
7. Program schema: `label(collision(marked_route, labeled_moving_objects)); scene=crossing; scope=hit_object_label`

## Program Contract
- `label(collision(marked_route, labeled_moving_objects)); scene=crossing; scope=hit_object_label`

## Generation Notes
1. Exactly four moving objects are labeled `A` through `D`; the answer is one of those labels.
2. Start pads use numeric labels so they do not conflict with moving-object option labels.
3. Annotation is the center point of the single labeled moving object that reaches the marked route at the matching tick.

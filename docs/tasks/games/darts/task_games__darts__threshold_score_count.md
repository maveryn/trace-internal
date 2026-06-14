# `task_games__darts__threshold_score_count`

## Contract
1. Domain: `games`
2. Scene: `darts`
3. Scene id: `darts`
4. Public task id: `task_games__darts__threshold_score_count`
5. Supported `query_id` values: `single`
6. Answer schema: `integer_count`
7. Annotation schema: `point_set`
8. Program schema: `count(filter(darts, compare(score(dart), threshold, direction))); scene=darts; scope=threshold_score_count`

## Program Contract
- `count(filter(darts, compare(score(dart), threshold, direction))); scene=darts; scope=threshold_score_count`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.

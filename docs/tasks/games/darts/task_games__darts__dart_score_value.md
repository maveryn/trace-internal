# `task_games__darts__dart_score_value`

## Contract
1. Domain: `games`
2. Scene: `darts`
3. Scene id: `darts`
4. Public task id: `task_games__darts__dart_score_value`
5. Supported `query_id` values: `single`
6. Answer schema: `integer_value`
7. Annotation schema: `point_set`
8. Program schema: `value(score(marked_dart)); scene=darts; scope=dart_score_value`

## Program Contract
- `value(score(marked_dart)); scene=darts; scope=dart_score_value`

## Generation Notes
1. The scene renders a simplified dartboard with 20 numbered sectors and one center bullseye.
2. A dart in a numbered sector scores that number; a dart in the center bullseye scores `50`.
3. Query ids are internal replay/sampling keys and do not define public task units.
4. Annotation is projected from the same generated game state used for answer verification.

# `task_games__darts__sector_dart_count`

## Contract
1. Domain: `games`
2. Scene: `darts`
3. Scene id: `darts`
4. Public task id: `task_games__darts__sector_dart_count`
5. Supported `query_id` values: `single`
6. Answer schema: `integer_count`
7. Annotation schema: `point_set`
8. Program schema: `count(filter(darts, sector_value(dart)=target_sector)); scene=darts; scope=sector_dart_count`

## Program Contract
- `count(filter(darts, sector_value(dart)=target_sector)); scene=darts; scope=sector_dart_count`

## Generation Notes
1. The scene renders a simplified dartboard with 20 numbered sectors and one center bullseye.
2. The target sector is sampled as a generation argument and highlighted in the image.
3. The answer support is `0..4`; non-target distractor dart count is sampled from `1..6`.
4. Query ids are internal replay/sampling keys and do not define public task units.
5. Annotation is projected from the same generated game state used for answer verification.

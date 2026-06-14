# `task_games__darts__total_score_option_label`

## Contract
1. Domain: `games`
2. Scene: `darts`
3. Scene id: `darts`
4. Public task id: `task_games__darts__total_score_option_label`
5. Supported `query_id` values: `total_score`
6. Answer schema: `string_label`
7. Annotation schema: `point_set`
8. Program schema: `label(select_option(score_options, option_score = score(marked_dart))); scene=darts; scope=total_score_option_label; query_branch=total_score`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.

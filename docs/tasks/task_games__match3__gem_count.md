# `task_games__match3__gem_count`

## Contract
1. Domain: `games`
2. Task group: `match3`
3. Scene id: `match3`
4. Public task id: `task_games__match3__gem_count`
5. Supported `query_id` values: `grid_color_gem_count`, `row_color_gem_count`, `column_color_gem_count`
6. Answer schema: `integer`
7. Annotation schema: `point_set`
8. Program schema: `count(filter(gems(scope), color_name=target_color)); scene=match3; scope=gem_count`

## Generation Notes
1. Gem colors are sampled from the repo-wide canonical named-color palette.
2. Prompt-facing color labels include the canonical hex value, for example `red [#E63232]`.
3. Annotation is projected from the matching gem centers in the same generated board used for answer verification.

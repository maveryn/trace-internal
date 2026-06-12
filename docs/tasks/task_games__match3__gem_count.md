# `task_games__match3__gem_count`

## Contract
1. Domain: `games`
2. Scene id: `match3`
3. Public task id: `task_games__match3__gem_count`
4. Supported `query_id` values: `grid_color_gem_count`, `row_color_gem_count`, `column_color_gem_count`
5. Answer schema: `integer`
6. Annotation schema: `point_set`
7. Program schema: `count(filter(gems(scope), color_name=target_color)); scene=match3; scope=gem_count`

## Generation Notes
1. Gem colors are sampled from the repo-wide canonical named-color palette.
2. Prompt-facing color labels include the canonical hex value, for example `red [#E63232]`.
3. Annotation is projected from the matching gem centers in the same generated board used for answer verification.

# `task_games__darts__bullseye_membership_count`

## Contract
1. Domain: `games`
2. Scene: `darts`
3. Scene id: `darts`
4. Public task id: `task_games__darts__bullseye_membership_count`
5. Supported `query_id` values: `inside_bullseye_count`, `outside_bullseye_count`
6. Answer schema: `integer_count`
7. Annotation schema: `point_set`
8. Program schema: `count(filter(darts, bullseye_membership(dart)=inside|outside)); scene=darts; scope=bullseye_membership_count`

## Program Contract
- `count(filter(darts, bullseye_membership(dart)=inside|outside)); scene=darts; scope=bullseye_membership_count`

## Generation Notes
1. The scene renders a simplified dartboard with 20 numbered sectors and one center bullseye.
2. Query ids switch only the user-facing membership predicate: inside vs outside the bullseye.
3. Annotation is projected from the same generated game state used for answer verification.

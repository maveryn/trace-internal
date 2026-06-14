# `task_games__marble_chain__shot_effect_value`

## Contract
1. Domain: `games`
2. Scene id: `marble_chain`
3. Public task id: `task_games__marble_chain__shot_effect_value`
4. Supported `query_id` values: `pop_count_after_marked_shot`
5. Answer schema: `integer_count`
6. Annotation schema: `point_set`
7. Program schema: `count(popped_chain_marbles(transform(chain, marked_shot))); scene=marble_chain; scope=shot_effect_value; query_branch=pop_count_after_marked_shot`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.

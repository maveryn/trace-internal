# `task_games__platformer__jump_landing_label`

## Contract
1. Domain: `games`
2. Scene id: `platformer`
3. Public task id: `task_games__platformer__jump_landing_label`
4. Supported `query_id` values: `single`
5. Answer schema: `string_label`
6. Annotation schema: `bbox`
7. Program schema: `label(landing_platform(marked_jump)); scene=platformer; scope=jump_landing_label`

## Program Contract
`scene=platformer; scope=jump_landing_label; program=label(landing_platform(shown_jump_arc))`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.

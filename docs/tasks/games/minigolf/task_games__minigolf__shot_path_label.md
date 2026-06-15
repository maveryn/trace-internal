# `task_games__minigolf__shot_path_label`

## Contract
1. Domain: `games`
2. Scene id: `minigolf`
3. Public task id: `task_games__minigolf__shot_path_label`
4. Supported `query_id` values: `single`
5. Answer schema: `string_label`
6. Annotation schema: `segment`

## Program Contract
`label(select_option(shot_paths, option_rule=path_satisfies_target)); scene=minigolf; scope=shot_path_label`

The rendered course shows one ball, a hole, obstacles, and numbered shot cues.
Each cue defines the initial putt direction. The program traces each putt with
mirror-like wall bounces, selects the only cue that reaches the hole before an
obstacle, returns that cue label, and annotates the selected visible cue segment
with one segment.

## Generation Notes
1. Query ids are internal replay/sampling keys and do not define public task units.
2. Annotation is projected from the same generated game state used for answer verification.

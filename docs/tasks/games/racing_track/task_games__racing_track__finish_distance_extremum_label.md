# task_games__racing_track__finish_distance_extremum_label

## Taxonomy
- Domain: games
- Scene: racing_track
- Task: finish_distance_extremum_label

## Objective
Select the labeled car with an extremal remaining distance to the finish line, measured along the track direction.

## Program Contract
Program schema: `select_extremum(racing_cars, remaining_distance_to_finish, operator=closest|farthest); scene=racing_track; scope=finish_distance_extremum_label`.

## Query IDs
- `closest_to_finish_label`
- `farthest_from_finish_label`

## Answer
String car label.

## Annotation
`point` at the selected car center.

## Notes
The scene is a single-lane loop track with a direction arrow and checkered finish line. Remaining distance is based on circular progress along the track, not straight-line image distance.

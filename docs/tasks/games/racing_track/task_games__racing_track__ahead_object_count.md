# task_games__racing_track__ahead_object_count

## Taxonomy
- Domain: games
- Scene: racing_track
- Task: ahead_object_count

## Objective
Count other cars ahead of the marked car before the finish line, following the track direction.

## Query IDs
- `car_ahead_count`

## Answer
Integer count.

## Annotation
`point_set` containing centers of every counted car. Empty annotation is valid when the answer is `0`.

## Notes
The marked car is not counted.

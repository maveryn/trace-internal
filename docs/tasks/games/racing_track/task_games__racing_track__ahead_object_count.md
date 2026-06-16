# task_games__racing_track__ahead_object_count

## Taxonomy
- Domain: games
- Scene: racing_track
- Task: ahead_object_count

## Objective
Count other cars ahead of the marked car before the finish line, following the track direction.

## Program Contract
Program schema: `count(filter(racing_cars, progress_after(marked_car) and before_finish)); scene=racing_track; scope=ahead_object_count`.

## Query IDs
- `single`

## Answer
Integer count.

## Annotation
Annotation schema: `point_set`.

`point_set` containing centers of every counted car. Empty annotation is valid when the answer is `0`.

## Notes
The marked car is not counted.

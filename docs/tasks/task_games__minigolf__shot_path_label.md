# `task_games__minigolf__shot_path_label`

1. Domain: `games`
2. Task group: `minigolf`
3. Scene id: `minigolf`
4. Query id: `shot_path_label`
5. Prompt bundle: `games_minigolf_v0`

The image shows a mini-golf putting course with a ball, hole, obstacles, and several numbered shot cues. Each cue shows only the starting direction. The task asks which numbered cue reaches the hole when the shot travels straight and bounces off course walls like a mirror.

The answer is a string numbered shot label. Evidence is `bbox_set`: one pixel bounding box around the selected numbered shot marker.

Generation is deterministic for a fixed seed and records the hidden path traces, obstacle geometry, unique hole-reaching cue, prompt keys, render style, and projected evidence in the trace payload.

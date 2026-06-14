# `task_icons__named_strip__shape_run_length`

- domain: `icons`
- scene_id: `named_strip`
- scene_id: `sequence`
- task: `shape_run_length`
- module: `trace/tasks/icons/sequence/named_shape_run_length.py`

## Contract
1. The image shows one horizontal row of boxed procedural named icons.
2. The prompt names one target icon shape in quotes.
3. The task asks for the longest or shortest consecutive run of the target
   shape in the row.
4. The target-shape run that determines the answer is unique by construction.
5. `answer_gt.type = integer`.
6. `annotation_gt.type = bbox_set` over the icons in the selected target-shape
   run only. `projected_annotation` mirrors this as typed bbox-set annotation with
   `bbox_set`, `pixel_bbox_set`, and bbox-center `pixel_point_set`.

## Query IDs
- `longest_shape_run_length`
- `shortest_shape_run_length`

## Generation
The target shape is sampled from the full procedural named-icon vocabulary in
`trace/tasks/icons/shared/procedural_named_icons.py`.

Default answer support:
- longest run length: `2..6`
- shortest run length: `1..5`

The strip length is sampled from `12..16`. Longest-run rows contain one target
run of the answer length and any other target runs are shorter. Shortest-run
rows contain one target run of the answer length and at least one other target
run that is longer.

Fill style and color are rendered as non-semantic visual variation.

## Trace
The trace records:
- every cell and rendered named icon,
- the target shape id/name,
- all target-shape runs with start/end/length,
- the selected run indices and instance ids,
- render-style metadata including text-legibility records for visible panel
  text,
- query, answer, strip-length, shape, and fill-style probability metadata.

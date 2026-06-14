# `task_icons__named_path__path_neighbor_label`

- domain: `icons`
- scene_id: `named_path`
- scene_id: `relation`
- task: `named_path_neighbor_label`
- module: `trace/tasks/icons/relation/named_path_neighbor_label.py`

## Contract
1. The image shows a single continuous open path marked from `START` to `END`.
2. Procedural named icons are placed on ordered path stops.
3. Exactly six non-target stop icons are option icons labeled `A` through `F`; the answer is one option letter.
4. The queried named icon occurrence is selected by path order and is not one of the option icons.
5. `answer_gt.type = option_letter`.
6. `annotation_gt.type = keyed_bbox_map` with `queried_icon` for the queried named-icon occurrence and `selected_neighbor` for the selected labeled neighbor.
   Annotation marks the two visual icon witnesses, not the numeric path stops or
   standalone label text.

## Query IDs
- `after_first_shape_label`
- `before_first_shape_label`
- `after_last_shape_label`
- `before_last_shape_label`
- `after_second_shape_label`
- `before_second_shape_label`

## Generation
The target shape is sampled from the full procedural named-icon vocabulary in
`trace/tasks/icons/shared/procedural_named_icons.py`. The path contains six
labeled option stops, `4..8` other non-target stops, and `2..4`
occurrences of the target shape. Target occurrences are non-adjacent and never
placed on the path endpoints. The selected neighbor is always a labeled
non-target option.

Prompt text quotes the target shape name, for example `"guitar"` icons.

## Trace
The trace records:
- ordered path points in pixel coordinates,
- every icon stop with `position_index`, label, shape, color, fill style, bbox,
  and target-occurrence metadata,
- the queried target occurrence,
- the selected answer option,
- render-style metadata for panel title, option-label, and START/END text
  legibility,
- query probabilities and sampled support metadata.

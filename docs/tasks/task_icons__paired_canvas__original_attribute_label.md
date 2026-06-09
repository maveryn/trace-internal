# `task_icons__paired_canvas__original_attribute_label`

## Identity
- domain: `icons`
- scene_id: `paired_canvas`
- task_group: `relation`
- task: `named_original_attribute_label`
- module: `trace/tasks/icons/relation/named_original_attribute_label.py`
- prompt bundle: `prompts/icons/relation/icons_relation_v0.json`

## Scene And Query
The task renders two open icon panels labeled `Original` and `Right`. The
Right panel contains six tracked option icons labeled `A`..`F` plus `4..8`
other icons. The Original panel shows the original state of the same icon
field. Tracked icons preserve approximate panel position across the two panels
but may change shape, color, or fill style in the Right panel.

Supported query ids:
- `original_shape_label`
- `original_color_shape_label`
- `original_fill_shape_label`

The prompt asks which labeled Right-panel icon was originally the named shape,
color+shape, or fill-style+shape described in the prompt. It never asks for
three-attribute bindings such as color+fill-style+shape.

## Answer Contract
- `answer_gt.type = option_letter`
- answer support is the six Right-panel option labels `A`..`F`
- the queried original descriptor is unique in the Original panel

## Annotation Contract
- `annotation_gt.type = keyed_bbox_map`
- annotation contains `original_icon` for the original matching icon in the
  Original panel and `right_icon` for its corresponding labeled icon in the
  Right panel
- `projected_annotation` mirrors this as typed keyed-bbox-map annotation with
  `keyed_bbox_map` and `pixel_keyed_bbox_map`

## Trace Contract
- `scene_ir.entities` contains serialized Original-panel and Right-panel icon
  entities for all tracked and other pairs.
- `execution_trace.pair_records` records original and right-side attributes for
  every pair.
- `witness_symbolic.answer_pair_id` identifies the shared pair linking the
  annotation boxes.
- `render_spec.style.text_legibility` records panel-title and Right-panel
  candidate-label text legibility.

## Prompt Contract
- `scene_key = paired_named_original_relation`
- `task_key = relation_query`
- answer-only and answer+annotation modes both include contract-valid JSON
  examples

## Review Artifacts
Use `review/task-reviews/icons/paired_canvas/scene_review.xlsx` as the current
paired-canvas browser-review sidecars.

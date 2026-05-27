# `task_icons__paired_canvas__original_attribute_label`

Status: accepted.

## Identity
- domain: `icons`
- scene_id: `paired_canvas`
- task_group: `relation`
- task: `named_original_attribute_label`
- module: `trace/tasks/icons/relation/named_original_attribute_label.py`
- prompt bundle: `prompts/icons/relation/icons_relation_v0.json`

## Scene And Query
The task renders two open icon panels labeled `Original` and `Right`. The
Right panel contains six tracked icons labeled `A`..`F` plus `4..8` unlabeled
distractor icons. The Original panel shows the original state of the same icon
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
- answer support is the six Right-panel labels `A`..`F`
- the queried original descriptor is unique in the Original panel

## Evidence Contract
- `evidence_gt.type = bbox_set`
- evidence contains one bbox for the original matching icon in the Original
  panel and one bbox for its corresponding labeled icon in the Right panel

## Trace Contract
- `scene_ir.entities` contains serialized Original-panel and Right-panel icon
  entities for all tracked and distractor pairs.
- `execution_trace.pair_records` records original and right-side attributes for
  every pair.
- `witness_symbolic.answer_pair_id` identifies the shared pair linking the
  evidence boxes.

## Prompt Contract
- `scene_key = paired_named_original_relation`
- `task_key = relation_query`
- answer-only and answer+evidence modes both include contract-valid JSON
  examples

## Calibration
- qwen25vl7b `100 x 24`, seed `20260507`: hard `0.100`, easy `0.050`,
  mean solve rate `0.291`, response cap `0.000`, prompt max `146`
- distribution gate: `6` unique answers, max answer frequency `0.190`

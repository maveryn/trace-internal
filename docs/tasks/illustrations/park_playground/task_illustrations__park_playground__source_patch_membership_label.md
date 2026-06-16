# `task_illustrations__park_playground__source_patch_membership_label`

## Summary
- Domain: `illustrations`
- Scene id: `park_playground`
- Implementation scene package: `park_playground`
- Implementation source: `trace/tasks/illustrations/park_playground/source_patch_membership_label.py`

## Task Contract
Render a complete park/playground illustration and a set of lettered patch options. Depending on the query branch, exactly one option is either an exact crop from the complete image or an altered patch that does not appear exactly in the image. The model selects the option letter.

## Program Contract
`select_label(match_patch_membership(source_image, patch_options, target_membership)); scene=park_playground; scope=source_patch_membership_label`

## Query Branches

| Query id | Program schema |
| --- | --- |
| `exact_source_patch_label` | `select_label(option where provenance == exact_source_crop); scene=park_playground; scope=source_patch_membership_label` |
| `altered_patch_label` | `select_label(option where provenance == altered_not_exact_source_crop); scene=park_playground; scope=source_patch_membership_label` |

## Program Metadata
- Program signatures: `selection.visual_correspondence`, `selection.visual_anomaly`
- Base program contract: `select_label(match_patch_membership(source_image, patch_options, target_membership)); scene=park_playground; scope=source_patch_membership_label`
- Parameter axes: `target_membership`, `source_person_count`, `source_equipment_count`, `option_count`, `patch_size`, `canvas_profile`, `alteration_families`
- Arguments:
  - `source_image`: semantic_role; allowed `complete_park_playground_illustration`; source `program_schema_concrete`
  - `patch_options`: semantic_role; allowed `lettered_patch_options`; source `program_schema_concrete`
  - `target_membership`: semantic_operand; allowed `exact_source_crop`, `altered_not_exact_source_crop`; source `query_id`
  - `option_count`: render_parameter; allowed `4`, `6`; source `trace_metadata`
  - `canvas_profile`: render_parameter; allowed `landscape`, `square`, `portrait`; source `trace_metadata`
  - `alteration_families`: render_parameter; allowed `small_object_presence_edit`, `object_recolor`, `object_placement_change`; source `trace_metadata`
- Argument metadata status: `curated`
- Supported query ids: `exact_source_patch_label`, `altered_patch_label`

## Answer Contract
- Answer schema: `option_letter`
- Generator `answer_gt.type`: `option_letter`
- The answer value is one of the visible patch option letters.

## Annotation Contract
- Annotation schema: `bbox`
- Generator `annotation_gt.type`: `bbox`
- Annotation contains exactly one final-image pixel box around the selected patch option. Do not include the source image, source crop region, all options, option letters, altered object boxes, or park-scene object boxes.

## Prompt And Trace Requirements
- Prompt text comes from `prompts/illustrations/park_playground/illustrations_park_playground_v0.json`.
- Render randomness, sampled park setting/style, patch-option label font, selected option, option provenance, source crop boxes, and alteration records are explicit in the instance trace.
- Alteration family and canvas profile are trace metadata, not public query ids.
- Altered patch options must apply one or two transformation families drawn from object add/remove, recolor, and placement-change edits, with visible pixel-delta thresholds.
- The complete source image remains intact; only the lettered option patches may be exact or altered.
- The selected option bbox, answer label, option provenance, and alteration records must all come from the same patch-membership composition trace.

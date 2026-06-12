# `task_physics__lens_optics__image_property_choice`

## Summary
- Domain: `physics`
- Scene id: `lens_optics`
- Implementation scene: `optics`
- Implementation source: `trace/tasks/physics/optics/lens_optics.py`
- Contract-v0 migration decision: `new_extension_task`
- Public mapping: `task_physics__lens_optics__image_property_choice` -> `task_physics__lens_optics__image_property_choice`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Selects the visible option that describes the image formed by a converging thin lens from the object's position relative to `F` and `2F`.

This public task id is a stable contract-v0 unit: one physics scene id plus one objective contract. Query ids may vary only narrow operands or parameters inside that same program contract.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `converging_lens_image_property_choice` | `option_letter(classify_converging_lens_image_property(object_position_relative_to_focal_marks)); scene=lens_optics; scope=image_property_choice; query_branch=converging_lens_image_property_choice` |

## Program Metadata
- Program signatures: `physics.lens_optics_image_property_choice`
- Base program contract: `option_letter(classify_converging_lens_image_property(object_position_relative_to_focal_marks)); scene=lens_optics; scope=image_property_choice`
- Parameter axes: `scene_variant`, `object_position_case`, `correct_option_letter`, `accent_color_name`
- Arguments:
  - `lens`: semantic_role; allowed `visible_converging_thin_lens`; source `program_schema_concrete`
  - `object_arrow`: semantic_role; allowed `single_visible_left_side_object_arrow`; source `program_schema_concrete`
  - `focal_marks`: semantic_role; allowed `F_and_2F_marks_on_both_sides`; source `program_schema_concrete`
  - `option_map`: semantic_role; allowed `visible_image_property_option_cards`; source `program_schema_concrete`
  - `object_position_case`: query_operand; allowed `beyond_2f|at_2f|between_f_2f|inside_f`; source `sampled_axis`
- Argument metadata status: `curated`
- Supported query ids: `converging_lens_image_property_choice`

## Answer Contract
- Answer schema: `option_letter`
- Generator `answer_gt.type`: `option_letter`
- The answer value is the selected visible option letter. The four supported image properties are `real_inverted_smaller`, `real_inverted_same_size`, `real_inverted_larger`, and `virtual_upright_larger`.

## Annotation Contract
- Annotation schema: `keyed_bbox_map`
- Generator `annotation_gt.type`: `keyed_bbox_map`
- Annotation keys are `lens`, `object_arrow`, and `focal_marks`.
- Annotation must mark minimal visual witnesses from the final rendered diagram. It must not mark option cards, option letters, title text, decorative grid lines, hidden image-position metadata, or a solved image arrow.
- Annotation and answer must be projected from the same generated execution trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the physics prompt bundles, with scene and task/query layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, object-position case, option mapping, option letter, accent color, and verifier payloads must be explicit in the instance trace.
- V0 is converging-lens only and excludes diverging-lens, object-at-F, and no-image cases.
- The rendered prompt image must show the lens, principal axis, `F` and `2F` marks on both sides, one object arrow, and visible image-property option cards. It must not draw the final image arrow or name the sampled object-position case in visible text.

## Review Artifacts
- Task review artifacts: `review/task-reviews/physics/lens_optics/task_physics__lens_optics__image_property_choice/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.

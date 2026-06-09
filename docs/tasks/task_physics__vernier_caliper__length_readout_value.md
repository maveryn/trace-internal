# `task_physics__vernier_caliper__length_readout_value`

## Summary
- Domain: `physics`
- Scene id: `vernier_caliper`
- Implementation task group: `measurement`
- Implementation source: `trace/tasks/physics/measurement/vernier_caliper.py`
- Contract-v0 migration decision: `new_extension_task`
- Public mapping: `task_physics__vernier_caliper__length_readout_value` -> `task_physics__vernier_caliper__length_readout_value`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Reads a length from a visible Vernier caliper by combining the main-scale position of the vernier zero with the aligned vernier tick.

This public task id is a stable contract-v0 unit: one physics scene id plus one objective contract. Query variation is limited to the sampled main-scale reading and aligned vernier tick inside the same readout program.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `main_scale_vernier_mm` | `read_vernier_caliper(main_scale_at_vernier_zero, aligned_vernier_tick, resolution=0.1 mm); scene=vernier_caliper; scope=length_readout_value` |

## Program Metadata
- Program signatures: `physics.vernier_caliper_length_readout`
- Base program contract: `read_vernier_caliper(main_scale_at_vernier_zero, aligned_vernier_tick, resolution=0.1 mm); scene=vernier_caliper; scope=length_readout_value`
- Parameter axes: `main_mm`, `aligned_vernier_tick`, `target_answer`
- Arguments:
  - `main_scale_region`: semantic_role; allowed `local_visible_main_mm_scale_near_vernier_zero`; source `program_schema_concrete`
  - `vernier_zero`: semantic_role; allowed `visible_vernier_zero_tick`; source `program_schema_concrete`
  - `vernier_scale_region`: semantic_role; allowed `visible_sliding_vernier_scale`; source `program_schema_concrete`
  - `aligned_vernier_tick`: semantic_role; allowed `visible_vernier_tick_aligned_to_main_scale`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `main_scale_vernier_mm`

## Answer Contract
- Answer schema: `number`
- Generator `answer_gt.type`: `number`
- The answer value is the measured length in millimeters with one decimal place and no unit string.

## Annotation Contract
- Annotation schema: `keyed_bbox_map`
- Generator `annotation_gt.type`: `keyed_bbox_map`
- Annotation keys: `main_scale_region`, `vernier_zero`, `vernier_scale_region`, `aligned_vernier_tick`
- Annotation must mark the minimal visible witnesses needed to read the caliper. It must not mark derived answer text, decorative caliper casing alone, or the measured object as a substitute for the scale reading.
- Annotation and answer must be projected from the same generated execution trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the physics measurement prompt bundle, with scene and task/query layers selected deterministically and recorded in metadata.
- The prompt or scene must state the `0.1 mm` vernier resolution so the task does not depend on hidden instrument trivia.
- Render randomness, sampled fonts/styles, main-scale reading, aligned vernier tick, target answer, and verifier payloads must be explicit in the instance trace.
- Color, object fill, layout jitter, stroke width, font, and background style are non-semantic and must never determine the answer.

## Review Artifacts
- Task review artifacts: `review/task-reviews/physics/vernier_caliper/task_physics__vernier_caliper__length_readout_value/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.

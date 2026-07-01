# `task_physics__vernier_caliper__length_readout_value`

## Summary
- Domain: `physics`
- Scene id: `vernier_caliper`
- Implementation scene: `vernier_caliper`
- Implementation source: `trace/tasks/physics/vernier_caliper/length_readout_value.py`

## Task Contract
Reads a length from a visible Vernier caliper by combining the main-scale position of the vernier zero with the aligned vernier tick.

## Program Contract

Program: `read_vernier_caliper(main_scale_at_vernier_zero, aligned_vernier_tick, resolution=0.1 mm); scene=vernier_caliper; scope=length_readout_value`

Candidate set: the visible caliper jaws, main scale, vernier scale, zero tick, and aligned tick mark inside the `length_readout_value` objective scope.
Operands: `vernier_zero_tick` (semantic_role, allowed `visible_vernier_zero_tick_center`, source `program_schema_concrete`); `aligned_vernier_tick` (semantic_role, allowed `visible_aligned_vernier_tick_center`, source `program_schema_concrete`); `main_scale_context` (context_operand, allowed `local_visible_main_mm_scale_near_vernier_zero`, source `trace_metadata`); `vernier_scale_context` (context_operand, allowed `visible_sliding_vernier_scale`, source `trace_metadata`).
Operation: evaluate `read_vernier_caliper` over the candidate set using the visible quantities, relations, branch semantics, and formulas encoded in the program expression; generation enforces a unique final answer.
Output binding: `answer` uses the `number` schema; Answer precision: `one_decimal`
Annotation witnesses: `point_map` witnesses from the finalized render. Annotation keys: `vernier_zero_tick`, `aligned_vernier_tick` Annotation marks the center points of the vernier zero tick and the aligned vernier tick.
Query ids: `single`.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `single` | `read_vernier_caliper(main_scale_at_vernier_zero, aligned_vernier_tick, resolution=0.1 mm); scene=vernier_caliper; scope=length_readout_value` |

## Program Metadata
- Program signatures: `physics.vernier_caliper_length_readout`
- Base program contract: `read_vernier_caliper(main_scale_at_vernier_zero, aligned_vernier_tick, resolution=0.1 mm); scene=vernier_caliper; scope=length_readout_value`
- Parameter axes: `main_mm`, `aligned_vernier_tick`, `target_answer`
- Arguments:
  - `vernier_zero_tick`: semantic_role; allowed `visible_vernier_zero_tick_center`; source `program_schema_concrete`
  - `aligned_vernier_tick`: semantic_role; allowed `visible_aligned_vernier_tick_center`; source `program_schema_concrete`
  - `main_scale_context`: context_operand; allowed `local_visible_main_mm_scale_near_vernier_zero`; source `trace_metadata`
  - `vernier_scale_context`: context_operand; allowed `visible_sliding_vernier_scale`; source `trace_metadata`
- Argument metadata status: `curated`
- Supported `query_id`s: `single`

## Answer Contract
- Answer schema: `number`
- Answer precision: `one_decimal`
- Generator `answer_gt.type`: `number`
- The answer value is the measured length in millimeters with one decimal place and no unit string.

## Annotation Contract
- Annotation schema: `point_map`
- Generator `annotation_gt.type`: `point_map`
- Annotation keys: `vernier_zero_tick`, `aligned_vernier_tick`
- Annotation marks the center points of the vernier zero tick and the aligned vernier tick.
- Annotation must not mark whole scale regions, derived answer text, decorative caliper casing alone, or the measured object as a substitute for the scale reading.
- Annotation and answer must be projected from the same generated execution trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the physics Vernier-caliper v1 prompt bundle, with scene and task/query layers selected deterministically and recorded in metadata.
- The prompt or scene must state the `0.1 mm` vernier resolution so the task does not depend on hidden instrument trivia.
- Render randomness, sampled fonts/styles, main-scale reading, aligned vernier tick, target answer, and verifier payloads must be explicit in the instance trace.
- Color, object fill, layout jitter, stroke width, font, and background style are non-semantic and must never determine the answer.

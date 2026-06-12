# `task_physics__signal_transform__pulse_width_spectrum_match_label`

## Summary
- Domain: `physics`
- Scene id: `signal_transform`
- Implementation scene: `waves`
- Implementation source: `trace/tasks/physics/waves/signal_transform.py`
- Contract-v0 migration decision: `split_after_audit`
- Public mapping: `task_physics__signal_transform__pulse_width_spectrum_match_label` -> `task_physics__signal_transform__pulse_width_spectrum_match_label`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Selects the labeled magnitude-spectrum option whose main-lobe width corresponds to a visible rectangular pulse width.

This public task id is a stable contract-v0 unit: one physics scene id plus one objective contract. It must remain pulse-width lobe matching only; sinusoid-component matching and periodic-wave harmonic-pattern matching are separate public tasks.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `pulse_width_spectrum` | `option_letter(select(spectrum_options, spectrum_lobe_width=inverse_pulse_width(input_waveform))); scene=signal_transform; scope=pulse_width_spectrum_match_label` |

## Program Metadata
- Program signatures: `physics.pulse_width_spectrum_match`
- Base program contract: `option_letter(select(spectrum_options, spectrum_lobe_width=inverse_pulse_width(input_waveform))); scene=signal_transform; scope=pulse_width_spectrum_match_label`
- Parameter axes: `scene_variant`, `waveform_family`, `correct_option_letter`
- Arguments:
  - `input_waveform`: semantic_role; allowed `visible_narrow_or_wide_rectangular_pulse`; source `program_schema_concrete`
  - `spectrum_options`: semantic_role; allowed `visible_labeled_one_sided_magnitude_spectra`; source `program_schema_concrete`
  - `spectrum_lobe_width`: query_operand; allowed `wide_lobe_for_narrow_pulse|narrow_lobe_for_wide_pulse`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `pulse_width_spectrum`

## Answer Contract
- Answer schema: `option_letter`
- Generator `answer_gt.type`: `option_letter`
- The answer value is the selected visible spectrum option letter.

## Annotation Contract
- Annotation schema: `keyed_bbox_map`
- Generator `annotation_gt.type`: `keyed_bbox_map`
- Annotation keys are `input_waveform` and `selected_spectrum`.
- Annotation must mark the input time-domain waveform panel and the selected matching spectrum option panel. It must not mark every option, decorative axes/grid lines, title text, or hidden semantic labels.
- Annotation and answer must be projected from the same generated execution trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the physics waves prompt bundle, with scene and task/query layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, waveform family, option order, selected option letter, spectrum signatures, and verifier payloads must be explicit in the instance trace.
- Diagrams use one-sided magnitude spectra in the initial public version. Equation choices, phase spectra, dense tick labels, and hidden waveform-family text are intentionally excluded.

## Review Artifacts
- Task review artifacts: `review/task-reviews/physics/signal_transform/task_physics__signal_transform__pulse_width_spectrum_match_label/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.

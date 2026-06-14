# `task_physics__signal_transform__sinusoid_component_spectrum_match_label`

## Summary
- Domain: `physics`
- Scene id: `signal_transform`
- Implementation scene: `waves`
- Implementation source: `trace/tasks/physics/waves/signal_transform.py`

## Task Contract
Selects the labeled magnitude-spectrum option matching the frequency spikes of a visible sinusoidal input waveform.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `sinusoid_component_spectrum` | `option_letter(select(spectrum_options, spike_components=sinusoid_components(input_waveform))); scene=signal_transform; scope=sinusoid_component_spectrum_match_label` |

## Program Metadata
- Program signatures: `physics.sinusoid_component_spectrum_match`
- Base program contract: `option_letter(select(spectrum_options, spike_components=sinusoid_components(input_waveform))); scene=signal_transform; scope=sinusoid_component_spectrum_match_label`
- Parameter axes: `scene_variant`, `waveform_family`, `correct_option_letter`
- Arguments:
  - `input_waveform`: semantic_role; allowed `visible_single_or_two_tone_sinusoidal_waveform`; source `program_schema_concrete`
  - `spectrum_options`: semantic_role; allowed `visible_labeled_one_sided_magnitude_spectra`; source `program_schema_concrete`
  - `spike_components`: query_operand; allowed `single_frequency_spike|two_frequency_spikes`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `sinusoid_component_spectrum`

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

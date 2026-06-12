# `task_physics__waveform_panel__wave_property_extremum_label`

## Summary
- Domain: `physics`
- Scene id: `waveform_panel`
- Implementation scene: `waves`
- Implementation source: `trace/tasks/physics/waves/waveform_panel.py`
- Contract-v0 migration decision: `new_extension_task`
- Public mapping: `task_physics__waveform_panel__wave_property_extremum_label` -> `task_physics__waveform_panel__wave_property_extremum_label`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Selects the labeled waveform panel with the requested highest or lowest wave property.

This public task id is a stable contract-v0 unit: one physics scene id plus one objective contract. Query ids may vary only narrow operands such as queried property, extremum direction, panel count, scene style, and selected panel label inside that same program contract.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `highest_amplitude_label` | `option_letter(arg_extreme(waveform_panels, amplitude, direction=highest)); scene=waveform_panel; scope=wave_property_extremum_label` |
| `lowest_amplitude_label` | `option_letter(arg_extreme(waveform_panels, amplitude, direction=lowest)); scene=waveform_panel; scope=wave_property_extremum_label` |
| `highest_frequency_label` | `option_letter(arg_extreme(waveform_panels, frequency, direction=highest)); scene=waveform_panel; scope=wave_property_extremum_label` |
| `lowest_frequency_label` | `option_letter(arg_extreme(waveform_panels, frequency, direction=lowest)); scene=waveform_panel; scope=wave_property_extremum_label` |
| `longest_wavelength_label` | `option_letter(arg_extreme(waveform_panels, wavelength, direction=longest)); scene=waveform_panel; scope=wave_property_extremum_label` |
| `shortest_wavelength_label` | `option_letter(arg_extreme(waveform_panels, wavelength, direction=shortest)); scene=waveform_panel; scope=wave_property_extremum_label` |

## Program Metadata
- Program signatures: `physics.waveform_property_extremum`
- Base program contract: `option_letter(arg_extreme(waveform_panels, property=amplitude_or_frequency_or_wavelength, direction=highest_or_lowest)); scene=waveform_panel; scope=wave_property_extremum_label`
- Parameter axes: `query_id`, `scene_variant`, `panel_count`, `correct_option_letter`
- Arguments:
  - `waveform_panels`: semantic_role; allowed `visible_labeled_sinusoid_panels_on_shared_scale`; source `program_schema_concrete`
  - `amplitude`: query_operand; allowed `vertical_displacement_from_midline`; source `program_schema_concrete`
  - `frequency`: query_operand; allowed `cycle_count_over_shared_horizontal_span`; source `program_schema_concrete`
  - `wavelength`: query_operand; allowed `crest_spacing_over_shared_horizontal_span`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `highest_amplitude_label`, `lowest_amplitude_label`, `highest_frequency_label`, `lowest_frequency_label`, `longest_wavelength_label`, `shortest_wavelength_label`

## Answer Contract
- Answer schema: `option_letter`
- Generator `answer_gt.type`: `option_letter`
- The answer value is the selected visible panel letter.

## Annotation Contract
- Annotation schema: `bbox_set`
- Generator `annotation_gt.type`: `bbox_set`
- Annotation is an unordered set containing one bounding box around the selected waveform panel.
- Annotation must mark the minimal selected panel witness from the final rendered diagram. It must not mark every panel, background grid lines, title text, or derived property annotations.
- Annotation and answer must be projected from the same generated execution trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the physics prompt bundles, with scene and task/query layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, panel count, waveform amplitudes, cycle counts, selected panel label, and verifier payloads must be explicit in the instance trace.
- Diagrams must keep all panels on a shared horizontal scale, with labels and midlines readable.

## Review Artifacts
- Task review artifacts: `review/task-reviews/physics/waveform_panel/task_physics__waveform_panel__wave_property_extremum_label/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.

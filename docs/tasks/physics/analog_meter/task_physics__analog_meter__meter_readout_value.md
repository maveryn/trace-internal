# `task_physics__analog_meter__meter_readout_value`

## Summary
- Domain: `physics`
- Scene id: `analog_meter`
- Implementation scene: `circuits`
- Implementation source: `trace/tasks/physics/circuits/analog_meter.py`

## Task Contract
Reads the integer value shown by an analog meter needle from the visible tick scale and unit label.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `ammeter_readout` | `integer(read_analog_meter(needle, scale_region, unit_label)); scene=analog_meter; meter=ammeter; scope=meter_readout_value` |
| `voltmeter_readout` | `integer(read_analog_meter(needle, scale_region, unit_label)); scene=analog_meter; meter=voltmeter; scope=meter_readout_value` |

## Program Metadata
- Program signatures: `physics.analog_meter_readout`
- Base program contract: `integer(read_analog_meter(needle_position, tick_scale, displayed_unit)); scene=analog_meter; scope=meter_readout_value`
- Parameter axes: `query_id`, `meter_profile`, `readout_value`
- Arguments:
  - `needle`: semantic_role; allowed `visible_meter_needle`; source `program_schema_concrete`
  - `scale_region`: query_operand; allowed `visible_tick_scale_with_numeric_labels`; source `program_schema_concrete`
  - `unit_label`: query_operand; allowed `A|mA|V`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `ammeter_readout`, `voltmeter_readout`

## Answer Contract
- Answer schema: `integer`
- Generator `answer_gt.type`: `integer`
- The answer value is the integer readout in the displayed unit.

## Annotation Contract
- Annotation schema: `keyed_bbox_map`
- Generator `annotation_gt.type`: `keyed_bbox_map`
- Annotation keys: `needle`, `scale_region`, `unit_label`
- Annotation must mark the minimal visible witnesses needed to read the meter. It must not mark only the selected tick label, the whole decorative casing, or derived answer text.
- Annotation and answer must be projected from the same generated execution trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the physics circuits prompt bundle, with scene and task/query layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, query id, meter profile, readout value, needle angle, unit, and verifier payloads must be explicit in the instance trace.
- First-version diagrams must use conventional clockwise left-to-right analog scales and integer tick-aligned needle positions.

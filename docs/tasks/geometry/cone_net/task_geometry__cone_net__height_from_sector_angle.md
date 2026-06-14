# `task_geometry__cone_net__height_from_sector_angle`

## Contract
1. Domain: `geometry`
2. Scene id: `cone_net`
5. Query id: `height_from_sector_angle`
6. Answer schema: `decimal_value_1dp`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `derive_geometry_metric(visible_cone_net_measurements, derivation_rule=height_from_sector_angle, output_role=height_length); scene=cone_net; scope=height_from_sector_angle`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `cone_net`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/cone_net.yaml`
- Task module: `trace/tasks/geometry/cone_net/height_from_sector_angle.py`

# Grounding Benchmark Smoke Test

- Date: 2026-07-13 UTC
- Model: `Qwen/Qwen2.5-VL-3B-Instruct`
- Suite: `trace_grounding`
- Decode: greedy, `max_tokens=256`
- Smoke rows: 2 per benchmark
- Artifacts: `/dev/shm/trace_rlvr/grounding_smoke_qwen25vl3b_20260713T220738Z`

| Benchmark key | VLMEvalKit alias | Full rows | Smoke rows | Primary metric | Smoke score |
| --- | --- | ---: | ---: | --- | ---: |
| `refspatial_wo_unseen` | `RefSpatial_wo_unseen` | 200 | 2 | mask point accuracy | 0.00 |
| `osworld_g` | `OSWorld_G` | 564 | 2 | overall click accuracy | 0.00 |
| `refcoco` | `RefCOCO` | 57457 | 2 | `Precision@1` at IoU >= 0.5 | 0.00 |
| `groundingme` | `GroundingME` | 1005 | 2 | `ACC@0.5` | 0.00 |
| `tdbench_grounding` | `tdbench_grounding_rot0` | 200 | 2 | average centroid containment | 0.00 |

Smoke purpose was build/generation/scoring validation, not accuracy estimation.
All five benchmarks generated predictions and produced `scores.json` through the
local scoring queue. `TDBenchGrounding` is configured as rot0 only; its evaluator
prints warnings about missing rot90/rot180/rot270 files when only rot0 is run.

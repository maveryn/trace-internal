# Qwen2.5-VL-3B TRACE Candidate-23 Step-500 Results

Generated on 2026-07-12 UTC.

Model comparison:
- Base: `Qwen/Qwen2.5-VL-3B-Instruct`
- TRACE RLVR: `trace-qwen25vl3b-easyr1-all1000-answer-nokl-step500`

Artifacts:
- Generation/score logs: `logs/benchmark/trace_candidate23_step500_20260712T031153Z/`
- Step-500 merged HF checkpoint: `/dev/shm/trace_rlvr/merged_hf/trace-qwen25vl3b-easyr1-all1000-answer-nokl-step500`
- Scores: `benchmark/<benchmark>/<model_slug>/<run_name>/scores.json`

| Benchmark | Rows | Base | Step 500 | Delta |
|---|---:|---:|---:|---:|
| ChartMuseum | 200 | 22.50 | 27.50 | +5.00 |
| Game-QA-Lite | 200 | 20.50 | 31.00 | +10.50 |
| ScreenSpot | 200 | 43.66 | 41.20 | -2.46 |
| ScreenSpot-Pro | 200 | 22.88 | 15.10 | -7.78 |
| ChartQAPro | 200 | 30.38 | 28.41 | -1.97 |
| PuzzleVQA | 200 | 31.00 | 33.50 | +2.50 |
| LogicVista | 200 | 34.00 | 41.00 | +7.00 |
| MathVista | 200 | 68.50 | 68.50 | +0.00 |
| CV-Bench 3D | 200 | 49.50 | 53.50 | +4.00 |
| WeMath | 200 | 48.50 | 64.00 | +15.50 |
| MathVision | 200 | 17.50 | 15.00 | -2.50 |
| ERQA | 200 | 30.50 | 30.50 | +0.00 |
| TreeBench | 200 | 40.00 | 35.00 | -5.00 |
| CountBenchQA | 200 | 71.00 | 73.00 | +2.00 |
| MathVerse | 200 | 15.50 | 22.50 | +7.00 |
| CharXivReason | 200 | 30.50 | 36.00 | +5.50 |
| PhyX mini MC | 200 | 34.00 | 34.00 | +0.00 |
| Physics | 200 | 11.00 | 16.50 | +5.50 |
| MMMU-ProVis | 200 | 24.00 | 32.50 | +8.50 |
| BLINK | 200 | 40.00 | 44.50 | +4.50 |
| VisionGraph-Q3 | 200 | 14.14 | 13.58 | -0.56 |
| VStarBench | 191 | 71.73 | 71.20 | -0.52 |
| VLMBias | 200 | 20.50 | 19.50 | -1.00 |

## Averages

| Average | Count | Base | Step 500 | Delta |
|---|---:|---:|---:|---:|
| Overall-23 | 23 | 34.43 | 36.85 | +2.42 |
| Excluding ScreenSpot and ScreenSpot-Pro | 21 | 34.54 | 37.68 | +3.14 |
| Excluding ScreenSpot, ScreenSpot-Pro, and VLMBias | 20 | 35.24 | 38.58 | +3.35 |

## Notes

- `VisionGraph-Q3` support was smoke-tested before the full run. The adapter now prefers `unrar` and extracts only task test images into `VISIONGRAPH_ROOT=/dev/shm/trace_rlvr/visiongraph`.
- Base was already complete for the prior 22 metrics; the missing base `VisionGraph-Q3` number was generated and scored in this run.
- `VStarBench` is full-set because its fixed candidate subset has 191 rows.

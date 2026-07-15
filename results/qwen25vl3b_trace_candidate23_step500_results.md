# Qwen2.5-VL-3B Trace Candidate-23 Step-400/500 Results

Generated on 2026-07-12 UTC.

Model comparison:
- Base: `Qwen/Qwen2.5-VL-3B-Instruct`
- Trace RLVR step 400: `trace-qwen25vl3b-easyr1-all1000-answer-nokl-step400`
- Trace RLVR step 500: `trace-qwen25vl3b-easyr1-all1000-answer-nokl-step500`

Artifacts:
- Step-400 generation/score logs: `logs/benchmark/trace_candidate23_step400_20260712T034819Z/`
- Step-500 generation/score logs: `logs/benchmark/trace_candidate23_step500_20260712T031153Z/`
- Step-400 merged HF checkpoint: `/dev/shm/trace_rlvr/merged_hf/trace-qwen25vl3b-easyr1-all1000-answer-nokl-step400`
- Step-500 merged HF checkpoint: `/dev/shm/trace_rlvr/merged_hf/trace-qwen25vl3b-easyr1-all1000-answer-nokl-step500`
- Scores: `benchmark/<benchmark>/<model_slug>/<run_name>/scores.json`

| Benchmark | Rows | Base | Step 400 | Step 500 | Delta 400 | Delta 500 | 500 - 400 |
|---|---:|---:|---:|---:|---:|---:|---:|
| ChartMuseum | 200 | 22.50 | 27.50 | 27.50 | +5.00 | +5.00 | +0.00 |
| Game-QA-Lite | 200 | 20.50 | 28.00 | 31.00 | +7.50 | +10.50 | +3.00 |
| ScreenSpot | 200 | 43.66 | 42.09 | 41.20 | -1.57 | -2.46 | -0.89 |
| ScreenSpot-Pro | 200 | 22.88 | 16.24 | 15.10 | -6.64 | -7.78 | -1.14 |
| ChartQAPro | 200 | 30.38 | 27.12 | 28.41 | -3.26 | -1.97 | +1.29 |
| PuzzleVQA | 200 | 31.00 | 37.50 | 33.50 | +6.50 | +2.50 | -4.00 |
| LogicVista | 200 | 34.00 | 39.50 | 41.00 | +5.50 | +7.00 | +1.50 |
| MathVista | 200 | 68.50 | 68.00 | 68.50 | -0.50 | +0.00 | +0.50 |
| CV-Bench 3D | 200 | 49.50 | 53.50 | 53.50 | +4.00 | +4.00 | +0.00 |
| WeMath | 200 | 48.50 | 56.00 | 64.00 | +7.50 | +15.50 | +8.00 |
| MathVision | 200 | 17.50 | 20.50 | 15.00 | +3.00 | -2.50 | -5.50 |
| ERQA | 200 | 30.50 | 35.00 | 30.50 | +4.50 | +0.00 | -4.50 |
| TreeBench | 200 | 40.00 | 37.00 | 35.00 | -3.00 | -5.00 | -2.00 |
| CountBenchQA | 200 | 71.00 | 71.50 | 73.00 | +0.50 | +2.00 | +1.50 |
| MathVerse | 200 | 15.50 | 17.50 | 22.50 | +2.00 | +7.00 | +5.00 |
| CharXivReason | 200 | 30.50 | 30.50 | 36.00 | +0.00 | +5.50 | +5.50 |
| PhyX mini MC | 200 | 34.00 | 43.00 | 34.00 | +9.00 | +0.00 | -9.00 |
| Physics | 200 | 11.00 | 15.00 | 16.50 | +4.00 | +5.50 | +1.50 |
| MMMU-ProVis | 200 | 24.00 | 27.50 | 32.50 | +3.50 | +8.50 | +5.00 |
| BLINK | 200 | 40.00 | 54.00 | 44.50 | +14.00 | +4.50 | -9.50 |
| VisionGraph-Q3 | 200 | 14.14 | 15.50 | 13.58 | +1.36 | -0.56 | -1.92 |
| VStarBench | 191 | 71.73 | 67.54 | 71.20 | -4.19 | -0.52 | +3.66 |
| VLMBias | 200 | 20.50 | 23.00 | 19.50 | +2.50 | -1.00 | -3.50 |

## Averages

| Average | Count | Base | Step 400 | Step 500 | Delta 400 | Delta 500 | 500 - 400 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Overall-23 | 23 | 34.43 | 37.09 | 36.85 | +2.66 | +2.42 | -0.24 |
| Excluding ScreenSpot and ScreenSpot-Pro | 21 | 34.54 | 37.84 | 37.68 | +3.31 | +3.14 | -0.16 |
| Excluding ScreenSpot, ScreenSpot-Pro, and VLMBias | 20 | 35.24 | 38.58 | 38.58 | +3.35 | +3.35 | +0.00 |

## Notes

- `VisionGraph-Q3` support was smoke-tested before the full run. The adapter now prefers `unrar` and extracts only task test images into `VISIONGRAPH_ROOT=/dev/shm/trace_rlvr/visiongraph`.
- Base was already complete for the prior 22 metrics; the missing base `VisionGraph-Q3` number was generated and scored in the step-500 report run.
- Step 400 and step 500 are from the all-1000-task answer-only no-KL run, not the earlier task-split runs.
- The first step-400 scoring pass used a shared scoring queue and exposed that `--gpu` controls physical GPU assignment inside `scripts/run_external_benchmark_score_queue.py`; failed judge-backed jobs were rerun with one physical GPU per judge scorer.
- `VStarBench` is full-set because its fixed candidate subset has 191 rows.

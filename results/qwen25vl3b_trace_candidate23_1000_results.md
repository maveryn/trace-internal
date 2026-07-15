# Qwen2.5-VL-3B Trace Candidate23 Stage 2 Results

Date: 2026-07-12

Stage: cumulative 1000 samples per benchmark where available. Benchmarks with fewer than 1000 examples use the full available subset.

Models:
- Base: `Qwen/Qwen2.5-VL-3B-Instruct`
- Trace step500: `/dev/shm/trace_rlvr/merged_hf/trace-qwen25vl3b-easyr1-all1000-answer-nokl-step500`

Artifacts:
- Subset root: `benchmark/subsets/trace_candidate23_1000`
- Generation logs: `logs/benchmark/trace_candidate23_1000_20260712T050300Z`
- Score logs: `logs/benchmark/trace_candidate23_1000_20260712T055500Z`
- Score root: `benchmark/stages/trace_candidate23_1000`
- Score queue: `benchmark/queues/score_multi_trace_candidate23_1000_base_vs_step500_20260712T055500Z.json`

Notes:
- Generation coverage was verified against the 1000-stage subset manifests for both models.
- ScreenSpot-Pro base predictions include extra historical/retry rows in the raw prediction file, but all manifest rows are present and scoring uses the staged subset.
- Judge-backed benchmarks were scored with `Qwen/Qwen3-32B`.

## Averages

| Slice | Benchmarks | Base | Step500 | Delta |
|---|---:|---:|---:|---:|
| Overall | 23 | 36.17 | 38.23 | +2.06 |
| Excluding ScreenSpot and ScreenSpot-Pro | 21 | 34.60 | 37.10 | +2.50 |
| Excluding ScreenSpot, ScreenSpot-Pro, and VLMBias | 20 | 35.36 | 37.97 | +2.61 |

## Benchmark Scores

| Benchmark | Prompt/run | N | Base | Step500 | Delta |
|---|---|---:|---:|---:|---:|
| ChartMuseum | `vlmevalkit_defaults_qwen32b_judge_test` | 1000 | 21.30 | 24.30 | +3.00 |
| Game-QA-Lite | `vlmevalkit_cot_boxed` | 1000 | 20.90 | 25.30 | +4.40 |
| ScreenSpot | `vlmevalkit_defaults_sample200` | 1000 | 87.94 | 85.11 | -2.83 |
| ScreenSpot-Pro | `vlmevalkit_defaults_sample200` | 1000 | 17.33 | 15.01 | -2.31 |
| ChartQAPro | `vlmevalkit_faithful_cot` | 1000 | 29.04 | 27.47 | -1.57 |
| PuzzleVQA | `vlmevalkit_reasoning` | 1000 | 32.60 | 36.50 | +3.90 |
| LogicVista | `vlmevalkit_defaults_qwen32b_judge` | 447 | 36.02 | 43.40 | +7.38 |
| MathVista | `vlmevalkit_defaults_qwen32b_judge` | 1000 | 62.80 | 65.30 | +2.50 |
| CV-Bench 3D | `vlmevalkit_defaults` | 1000 | 49.50 | 53.50 | +4.00 |
| WeMath | `vlmevalkit_cot_qwen32b_judge` | 1000 | 43.70 | 60.10 | +16.40 |
| MathVision | `vlmevalkit_defaults_qwen32b_judge` | 1000 | 21.50 | 23.80 | +2.30 |
| ERQA | `vlmevalkit_defaults` | 400 | 31.00 | 33.25 | +2.25 |
| TreeBench | `vlmevalkit_defaults` | 405 | 40.00 | 35.00 | -5.00 |
| CountBenchQA | `vlmevalkit_defaults` | 487 | 69.61 | 72.28 | +2.67 |
| MathVerse | `vlmevalkit_defaults_qwen32b_judge` | 788 | 20.94 | 20.05 | -0.89 |
| CharXivReason | `vlmevalkit_defaults_qwen32b_judge` | 1000 | 29.90 | 34.90 | +5.00 |
| PhyX mini MC | `vlmevalkit_defaults` | 1000 | 32.90 | 33.40 | +0.50 |
| Physics | `vlmevalkit_reasoning` | 1000 | 12.10 | 13.80 | +1.70 |
| MMMU-ProVis | `vlmevalkit_cot_max2048` | 1000 | 24.90 | 27.50 | +2.60 |
| Blink | `vlmevalkit_defaults` | 1000 | 43.90 | 43.90 | +0.00 |
| VisionGraph-Q3 | `vlmevalkit_q3` | 1000 | 12.85 | 14.36 | +1.51 |
| VStarBench | `vlmevalkit_defaults` | 191 | 71.73 | 71.20 | -0.52 |
| VLMBias | `vlmevalkit_defaults` | 1000 | 19.40 | 19.80 | +0.40 |

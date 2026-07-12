# Qwen2.5-VL-3B TRACE Candidate24 Full Benchmark Results

This full stage carries forward the 1000-row candidate23 stage, adds all remaining rows for those 23 benchmarks, and adds regular `ChartQA_TEST` as the 24th benchmark.

- Subset root: `benchmark/subsets/trace_candidate24_full`
- Score root: `benchmark/stages/trace_candidate24_full`
- Generation logs: `logs/benchmark/trace_candidate24_full_20260712T055957Z`
- Score logs: `logs/benchmark/trace_candidate24_full_score_20260712T062908Z`
- Models: `Qwen/Qwen2.5-VL-3B-Instruct` vs `/dev/shm/trace_rlvr/merged_hf/trace-qwen25vl3b-easyr1-all1000-answer-nokl-step500`

Scoring notes:
- `ChartQA_TEST` uses VLMEvalKit deterministic relaxed accuracy, not an LLM judge.
- `MathVision` and `Physics` required Qwen3-32B judge reruns with tensor parallelism because the first judge attempts hit memory/context limits.
- `ScreenSpot` and `ScreenSpot-Pro` are reported as weighted overall accuracy from VLMEvalKit group `Overall_Accuracy` and `cnt` fields; the generic numeric fallback is invalid for these because it averages count fields.
- Scores are percentages when the evaluator reports accuracy-like metrics.

| Benchmark | Prompt / Dataset | Rows | Base | Step 500 | Step 500 - Base |
| --- | --- | ---: | ---: | ---: | ---: |
| ChartMuseum | `vlmevalkit_defaults_qwen32b_judge_test` | 1000 | 21.30 | 24.30 | 3.00 |
| ChartQA | `vlmevalkit_defaults` | 2500 | 82.72 | 83.00 | 0.28 |
| Game-QA-Lite | `vlmevalkit_cot_boxed` | 2633 | 19.98 | 23.17 | 3.19 |
| ScreenSpot | `vlmevalkit_defaults_sample200` | 1272 | 67.14 | 61.01 | -6.13 |
| ScreenSpot-Pro | `vlmevalkit_defaults_sample200` | 1581 | 14.61 | 8.16 | -6.45 |
| ChartQAPro | `vlmevalkit_faithful_cot` | 1948 | 30.73 | 28.08 | -2.65 |
| PuzzleVQA | `vlmevalkit_reasoning` | 2000 | 32.60 | 36.15 | 3.55 |
| LogicVista | `vlmevalkit_defaults_qwen32b_judge` | 447 | 36.02 | 43.40 | 7.38 |
| MathVista | `vlmevalkit_defaults_qwen32b_judge` | 1000 | 62.80 | 65.30 | 2.50 |
| CV-Bench 3D | `vlmevalkit_defaults` | 1200 | 49.50 | 53.50 | 4.00 |
| WeMath | `vlmevalkit_cot_qwen32b_judge` | 1740 | 44.37 | 58.56 | 14.20 |
| MathVision | `vlmevalkit_defaults_qwen32b_judge` | 3040 | 21.71 | 25.03 | 3.32 |
| ERQA | `vlmevalkit_defaults` | 400 | 31.00 | 33.25 | 2.25 |
| TreeBench | `vlmevalkit_defaults` | 405 | 40.00 | 35.00 | -5.00 |
| CountBenchQA | `vlmevalkit_defaults` | 487 | 69.61 | 72.28 | 2.67 |
| MathVerse | `vlmevalkit_defaults_qwen32b_judge` | 788 | 20.94 | 20.05 | -0.89 |
| CharXivReason | `vlmevalkit_defaults_qwen32b_judge` | 1000 | 29.90 | 34.90 | 5.00 |
| PhyX mini MC | `vlmevalkit_defaults` | 1000 | 32.90 | 33.40 | 0.50 |
| Physics | `vlmevalkit_reasoning` | 1297 | 11.57 | 13.96 | 2.39 |
| MMMU-ProVis | `vlmevalkit_cot_max2048` | 1730 | 24.68 | 25.84 | 1.16 |
| Blink | `vlmevalkit_defaults` | 1901 | 46.03 | 45.55 | -0.47 |
| VisionGraph-Q3 | `vlmevalkit_q3` | 1000 | 12.85 | 14.36 | 1.51 |
| VStarBench | `vlmevalkit_defaults` | 191 | 71.73 | 71.20 | -0.52 |
| VLMBias | `vlmevalkit_defaults` | 2782 | 18.87 | 19.55 | 0.68 |
| Average |  |  | 37.23 | 38.71 | 1.48 |
| Average excl. ScreenSpot |  |  | 36.90 | 39.08 | 2.18 |
| Average excl. ScreenSpot/VLMBias |  |  | 37.76 | 40.01 | 2.26 |

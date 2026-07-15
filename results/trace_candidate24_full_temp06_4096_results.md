# Qwen2.5-VL Trace Candidate24 Full Temp0.6-4096 Benchmark Results

Subset manifest root: `benchmark/subsets/trace_candidate24_full`

Each benchmark has exactly one normalized score. Scores are percentages when the evaluator reports accuracy-like metrics.

| Benchmark | Prompt / Dataset | Rows | Base | trace-qwen25vl3b-easyr1-all1000-answer-nokl-step500 | qwen25vl7b-base | trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500 | trace-qwen25vl3b-easyr1-all1000-answer-nokl-step500 - Base | qwen25vl7b-base - Base | trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500 - Base |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ChartMuseum | `vlmevalkit_defaults_qwen32b_judge_test` | 1000 | 0.00 | 0.00 | 0.10 | 0.00 | 0.00 | 0.10 | 0.00 |
| Game-QA-Lite | `vlmevalkit_cot_boxed` | 2633 | 18.99 | 20.77 | 25.07 | 29.09 | 1.79 | 6.08 | 10.10 |
| ScreenSpot | `vlmevalkit_defaults_sample200` | 1272 | 50.00 | 54.32 | 77.12 | 77.83 | 4.32 | 27.12 | 27.83 |
| ScreenSpot-Pro | `vlmevalkit_defaults_sample200` | 1581 | 10.44 | 10.44 | 13.41 | 10.25 | 0.00 | 2.97 | -0.19 |
| ChartQAPro | `vlmevalkit_faithful_cot` | 1948 | 32.49 | 33.27 | 46.38 | 49.59 | 0.78 | 13.89 | 17.10 |
| PuzzleVQA | `vlmevalkit_reasoning` | 2000 | 33.55 | 42.55 | 46.70 | 53.40 | 9.00 | 13.15 | 19.85 |
| VStarBench | `vlmevalkit_defaults` | 191 | 70.16 | 72.77 | 75.39 | 75.92 | 2.62 | 5.24 | 5.76 |
| LogicVista | `vlmevalkit_defaults_qwen32b_judge` | 447 | 35.57 | 42.28 | 42.51 | 48.55 | 6.71 | 6.94 | 12.98 |
| MathVista | `vlmevalkit_defaults_qwen32b_judge` | 1000 | 61.90 | 66.60 | 69.30 | 73.30 | 4.70 | 7.40 | 11.40 |
| CV-Bench 3D | `vlmevalkit_defaults` | 1200 | 57.17 | 64.17 | 76.08 | 81.92 | 7.00 | 18.92 | 24.75 |
| WeMath | `vlmevalkit_cot_qwen32b_judge` | 1740 | 47.70 | 59.20 | 64.54 | 67.53 | 11.49 | 16.84 | 19.83 |
| MathVision | `vlmevalkit_defaults_qwen32b_judge` | 3040 | 19.87 | 25.26 | 25.33 | 28.55 | 5.39 | 5.46 | 8.68 |
| ERQA | `vlmevalkit_defaults` | 400 | 33.25 | 34.00 | 39.75 | 40.75 | 0.75 | 6.50 | 7.50 |
| TreeBench | `vlmevalkit_defaults` | 405 | 38.27 | 39.75 | 39.26 | 42.72 | 1.48 | 0.99 | 4.44 |
| CountBenchQA | `vlmevalkit_defaults` | 487 | 68.79 | 70.02 | 83.57 | 85.83 | 1.23 | 14.78 | 17.04 |
| MathVerse | `vlmevalkit_defaults_qwen32b_judge` | 788 | 19.04 | 21.32 | 25.25 | 24.75 | 2.28 | 6.22 | 5.71 |
| CharXivReason | `vlmevalkit_defaults_qwen32b_judge` | 1000 | 29.90 | 33.70 | 38.50 | 45.50 | 3.80 | 8.60 | 15.60 |
| PhyX mini MC | `vlmevalkit_defaults` | 1000 | 32.90 | 37.10 | 38.10 | 46.10 | 4.20 | 5.20 | 13.20 |
| Physics | `vlmevalkit_reasoning` | 1297 | 21.67 | 20.89 | 22.28 | 24.36 | -0.77 | 0.62 | 2.70 |
| MMMU-ProVis | `vlmevalkit_cot_max2048` | 1730 | 26.94 | 31.79 | 35.38 | 40.35 | 4.86 | 8.44 | 13.41 |
| Blink | `vlmevalkit_defaults` | 1901 | 44.56 | 46.50 | 53.29 | 58.65 | 1.95 | 8.73 | 14.10 |
| VLMBias | `vlmevalkit_defaults` | 2782 | 23.51 | 23.80 | 24.34 | 23.18 | 0.29 | 0.83 | -0.32 |
| VisionGraph-Q3 | `vlmevalkit_q3` | 1000 | 12.45 | 13.61 | 15.02 | 14.36 | 1.17 | 2.57 | 1.92 |
| Average |  |  | 34.31 | 37.57 | 42.46 | 45.33 | 3.26 | 8.16 | 11.02 |
| Average excl. ScreenSpot |  |  | 34.68 | 38.04 | 42.21 | 45.44 | 3.36 | 7.53 | 10.76 |

Normalization notes:
- `MM-HELIX`: weighted mean over category `items * average_score` from the generated results TSV.
- `TableVQABench`: macro mean over the reported split `average_scores` values.
- `SEEPhys`: nested `Overall / Accuracy (%)` value.
- Judge-backed datasets use the local Qwen3-32B judge configured by the queue.

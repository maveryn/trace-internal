# Qwen2.5-VL Trace Candidate24 Full Greedy-4096 Benchmark Results

Subset manifest root: `benchmark/subsets/trace_candidate24_full`

Each benchmark has exactly one normalized score. Scores are percentages when the evaluator reports accuracy-like metrics.

| Benchmark | Prompt / Dataset | Rows | Base | trace-qwen25vl3b-easyr1-all1000-answer-nokl-step500 | qwen25vl7b-base | trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500 | trace-qwen25vl3b-easyr1-all1000-answer-nokl-step500 - Base | qwen25vl7b-base - Base | trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500 - Base |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ChartMuseum | `vlmevalkit_defaults_qwen32b_judge_test` | 1000 | 19.40 | 22.10 | 25.60 | 33.60 | 2.70 | 6.20 | 14.20 |
| Game-QA-Lite | `vlmevalkit_cot_boxed` | 2633 | 22.75 | 23.85 | 26.40 | 28.45 | 1.10 | 3.65 | 5.70 |
| ScreenSpot | `vlmevalkit_defaults_sample200` | 1272 | 72.72 | 61.87 | 75.71 | 79.56 | -10.85 | 2.99 | 6.84 |
| ScreenSpot-Pro | `vlmevalkit_defaults_sample200` | 1581 | 19.86 | 11.45 | 13.92 | 11.76 | -8.41 | -5.95 | -8.10 |
| ChartQAPro | `vlmevalkit_faithful_cot` | 1948 | 34.29 | 34.21 | 46.99 | 49.87 | -0.08 | 12.70 | 15.58 |
| PuzzleVQA | `vlmevalkit_reasoning` | 2000 | 31.40 | 40.00 | 46.85 | 53.20 | 8.60 | 15.45 | 21.80 |
| VStarBench | `vlmevalkit_defaults` | 191 | 74.35 | 74.87 | 76.44 | 73.82 | 0.52 | 2.09 | -0.52 |
| LogicVista | `vlmevalkit_defaults_qwen32b_judge` | 447 | 40.49 | 42.73 | 45.19 | 48.10 | 2.24 | 4.70 | 7.61 |
| MathVista | `vlmevalkit_defaults_qwen32b_judge` | 1000 | 62.10 | 65.60 | 69.70 | 74.20 | 3.50 | 7.60 | 12.10 |
| CV-Bench 3D | `vlmevalkit_defaults` | 1200 | 65.83 | 72.42 | 75.58 | 81.75 | 6.58 | 9.75 | 15.92 |
| WeMath | `vlmevalkit_cot_qwen32b_judge` | 1740 | 51.09 | 59.94 | 64.25 | 67.36 | 8.85 | 13.16 | 16.26 |
| MathVision | `vlmevalkit_defaults_qwen32b_judge` | 3040 | 22.47 | 26.38 | 26.02 | 27.43 | 3.91 | 3.55 | 4.97 |
| ERQA | `vlmevalkit_defaults` | 400 | 38.00 | 35.50 | 40.25 | 40.50 | -2.50 | 2.25 | 2.50 |
| TreeBench | `vlmevalkit_defaults` | 405 | 39.75 | 41.23 | 41.48 | 44.20 | 1.48 | 1.73 | 4.44 |
| CountBenchQA | `vlmevalkit_defaults` | 487 | 71.25 | 72.48 | 87.06 | 86.24 | 1.23 | 15.81 | 14.99 |
| MathVerse | `vlmevalkit_defaults_qwen32b_judge` | 788 | 17.89 | 21.57 | 22.97 | 25.00 | 3.68 | 5.08 | 7.11 |
| CharXivReason | `vlmevalkit_defaults_qwen32b_judge` | 1000 | 32.70 | 36.70 | 42.60 | 47.20 | 4.00 | 9.90 | 14.50 |
| PhyX mini MC | `vlmevalkit_defaults` | 1000 | 33.20 | 35.60 | 40.80 | 48.60 | 2.40 | 7.60 | 15.40 |
| Physics | `vlmevalkit_reasoning` | 1297 | 21.05 | 20.97 | 20.51 | 26.68 | -0.08 | -0.54 | 5.63 |
| MMMU-ProVis | `vlmevalkit_cot_max2048` | 1730 | 29.02 | 30.29 | 38.03 | 40.46 | 1.27 | 9.02 | 11.45 |
| Blink | `vlmevalkit_defaults` | 1901 | 48.97 | 49.76 | 56.34 | 59.39 | 0.79 | 7.36 | 10.42 |
| VLMBias | `vlmevalkit_defaults` | 2782 | 19.48 | 19.95 | 21.68 | 24.12 | 0.47 | 2.19 | 4.64 |
| VisionGraph-Q3 | `vlmevalkit_q3` | 1000 | 12.50 | 13.78 | 14.23 | 14.50 | 1.28 | 1.73 | 2.00 |
| Average |  |  | 38.29 | 39.71 | 44.29 | 47.22 | 1.42 | 6.00 | 8.93 |
| Average excl. ScreenSpot |  |  | 37.56 | 39.98 | 44.24 | 47.36 | 2.43 | 6.68 | 9.80 |

Normalization notes:
- `MM-HELIX`: weighted mean over category `items * average_score` from the generated results TSV.
- `TableVQABench`: macro mean over the reported split `average_scores` values.
- `SEEPhys`: nested `Overall / Accuracy (%)` value.
- Judge-backed datasets use the local Qwen3-32B judge configured by the queue.

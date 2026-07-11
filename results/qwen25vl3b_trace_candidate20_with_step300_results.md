# Qwen2.5-VL-3B Selected 20 Benchmark Results With All1000 Step 200

Subset manifest root: `benchmark/subsets/trace_candidate37_200`

Each benchmark has exactly one normalized score. Scores are percentages when the evaluator reports accuracy-like metrics.

| Benchmark | Prompt / Dataset | Rows | Base | Step 300 | Step 400 | Step 500 | Step 600 | Step 700 | All1000 Step 200 | Step 300 - Base | Step 400 - Base | Step 500 - Base | Step 600 - Base | Step 700 - Base | All1000 Step 200 - Base |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ChartMuseum | `vlmevalkit_defaults_qwen32b_judge_test` | 200 | 22.50 | 26.00 | 23.50 | 26.50 | 25.50 | 25.00 | 22.50 | 3.50 | 1.00 | 4.00 | 3.00 | 2.50 | 0.00 |
| Game-QA-Lite | `vlmevalkit_cot_boxed` | 200 | 20.50 | 22.00 | 27.00 | 27.50 | 27.00 | 31.00 | 24.00 | 1.50 | 6.50 | 7.00 | 6.50 | 10.50 | 3.50 |
| ScreenSpot | `vlmevalkit_defaults_sample200` | 200 | 43.66 | 40.09 | 41.67 | 43.42 | 40.18 | 42.65 | 44.18 | -3.57 | -1.99 | -0.24 | -3.48 | -1.01 | 0.52 |
| ScreenSpot-Pro | `vlmevalkit_defaults_sample200` | 158/200/200/200/200/200/200 | 22.88 | 15.31 | 17.03 | 15.21 | 16.37 | 15.55 | 16.88 | -7.57 | -5.85 | -7.66 | -6.50 | -7.33 | -5.99 |
| ChartQAPro | `vlmevalkit_faithful_cot` | 200 | 30.38 | 27.76 | 25.44 | 26.28 | 24.91 | 27.82 | 25.10 | -2.62 | -4.94 | -4.10 | -5.47 | -2.55 | -5.28 |
| PuzzleVQA | `vlmevalkit_reasoning` | 200 | 31.00 | 33.50 | 33.50 | 41.00 | 34.50 | 28.50 | 35.00 | 2.50 | 2.50 | 10.00 | 3.50 | -2.50 | 4.00 |
| LogicVista | `vlmevalkit_defaults_qwen32b_judge` | 200 | 34.00 | 37.50 | 41.50 | 43.00 | 39.00 | 32.50 | 36.00 | 3.50 | 7.50 | 9.00 | 5.00 | -1.50 | 2.00 |
| MathVista | `vlmevalkit_defaults_qwen32b_judge` | 200 | 68.50 | 66.00 | 67.50 | 69.00 | 68.50 | 69.50 | 65.00 | -2.50 | -1.00 | 0.50 | 0.00 | 1.00 | -3.50 |
| CV-Bench 3D | `vlmevalkit_defaults` | 200 | 49.50 | 48.50 | 56.00 | 57.50 | 49.50 | 57.00 | 51.50 | -1.00 | 6.50 | 8.00 | 0.00 | 7.50 | 2.00 |
| WeMath | `vlmevalkit_cot_qwen32b_judge` | 200 | 48.50 | 59.50 | 58.00 | 59.00 | 60.50 | 60.50 | 51.50 | 11.00 | 9.50 | 10.50 | 12.00 | 12.00 | 3.00 |
| MathVision | `vlmevalkit_defaults_qwen32b_judge` | 200 | 17.50 | 20.50 | 17.50 | 24.50 | 22.50 | 18.50 | 21.50 | 3.00 | 0.00 | 7.00 | 5.00 | 1.00 | 4.00 |
| ERQA | `vlmevalkit_defaults` | 200 | 30.50 | 35.50 | 31.50 | 32.00 | 31.50 | 33.50 | 34.50 | 5.00 | 1.00 | 1.50 | 1.00 | 3.00 | 4.00 |
| TreeBench | `vlmevalkit_defaults` | 200 | 40.00 | 38.50 | 34.50 | 42.00 | 36.00 | 36.00 | 42.00 | -1.50 | -5.50 | 2.00 | -4.00 | -4.00 | 2.00 |
| CountBenchQA | `vlmevalkit_defaults` | 200 | 71.00 | 75.00 | 73.00 | 73.50 | 74.00 | 74.50 | 72.00 | 4.00 | 2.00 | 2.50 | 3.00 | 3.50 | 1.00 |
| MathVerse | `vlmevalkit_defaults_qwen32b_judge` | 200 | 15.50 | 22.00 | 20.00 | 19.00 | 17.50 | 22.00 | 21.50 | 6.50 | 4.50 | 3.50 | 2.00 | 6.50 | 6.00 |
| CharXivReason | `vlmevalkit_defaults_qwen32b_judge` | 200 | 30.50 | 34.50 | 31.50 | 31.00 | 32.00 | 34.00 | 30.00 | 4.00 | 1.00 | 0.50 | 1.50 | 3.50 | -0.50 |
| PhyX mini MC | `vlmevalkit_defaults` | 200 | 34.00 | 30.50 | 37.00 | 46.00 | 36.00 | 33.00 | 38.50 | -3.50 | 3.00 | 12.00 | 2.00 | -1.00 | 4.50 |
| Physics | `vlmevalkit_reasoning` | 200 | 11.00 | 13.00 | 15.00 | 14.50 | 16.00 | 16.00 | 13.00 | 2.00 | 4.00 | 3.50 | 5.00 | 5.00 | 2.00 |
| MMMU-ProVis | `vlmevalkit_cot_max2048` | 200 | 24.00 | 32.50 | 32.50 | 33.50 | 30.50 | 28.50 | 26.00 | 8.50 | 8.50 | 9.50 | 6.50 | 4.50 | 2.00 |
| Blink | `vlmevalkit_defaults` | 200 | 40.00 | 43.00 | 46.00 | 47.50 | 44.50 | 46.50 | 51.50 | 3.00 | 6.00 | 7.50 | 4.50 | 6.50 | 11.50 |
| Average |  |  | 34.27 | 36.06 | 36.48 | 38.60 | 36.32 | 36.63 | 36.11 | 1.79 | 2.21 | 4.33 | 2.05 | 2.36 | 1.84 |
| Average excl. ScreenSpot |  |  | 34.38 | 36.94 | 37.23 | 39.57 | 37.17 | 37.42 | 36.69 | 2.56 | 2.86 | 5.20 | 2.79 | 3.04 | 2.32 |

Normalization notes:
- `MM-HELIX`: weighted mean over category `items * average_score` from the generated results TSV.
- `TableVQABench`: macro mean over the reported split `average_scores` values.
- `SEEPhys`: nested `Overall / Accuracy (%)` value.
- Judge-backed datasets use the local Qwen3-32B judge configured by the queue.

# Qwen2.5-VL Selected25 Full Temp0.6 Seed 43 Answer-GRPO Benchmark Results

Subset manifest root: `selected25 full; candidate benchmarks use trace_candidate24_full subset manifests; extra benchmarks use full VLMEvalKit datasets`

Each benchmark has exactly one normalized score. Scores are percentages when the evaluator reports accuracy-like metrics.

| Benchmark | Prompt / Dataset | Rows | Base | Answer GRPO 500 | 7B Base | 7B Answer GRPO 500 | Answer GRPO 500 - Base | 7B Base - Base | 7B Answer GRPO 500 - Base |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ChartMuseum | `vlmevalkit_defaults_qwen32b_judge_test` | 1000 | 19.20 | 22.70 | 24.50 | 32.60 | 3.50 | 5.30 | 13.40 |
| Game-QA-Lite | `vlmevalkit_cot_boxed` | 2633 | 19.07 | 21.72 | 24.84 | 29.02 | 2.66 | 5.77 | 9.95 |
| ScreenSpot | `vlmevalkit_defaults_sample200` | 1272 | 64.15 | 55.03 | 68.16 | 77.99 | -9.12 | 4.01 | 13.84 |
| ChartQAPro | `vlmevalkit_faithful_cot` | 1948 | 32.48 | 33.56 | 46.97 | 48.53 | 1.08 | 14.49 | 16.05 |
| PuzzleVQA | `vlmevalkit_reasoning` | 2000 | 33.45 | 38.75 | 46.80 | 53.50 | 5.30 | 13.35 | 20.05 |
| VStarBench | `vlmevalkit_defaults` | 191 | 72.25 | 75.92 | 75.92 | 75.92 | 3.66 | 3.66 | 3.66 |
| LogicVista | `vlmevalkit_defaults_qwen32b_judge` | 447 | 36.91 | 41.39 | 44.30 | 47.20 | 4.47 | 7.38 | 10.29 |
| MathVista | `vlmevalkit_defaults_qwen32b_judge` | 1000 | 54.00 | 63.20 | 69.80 | 73.90 | 9.20 | 15.80 | 19.90 |
| VisualPuzzles | `vlmevalkit_reasoning` | 1168 | 17.98 | 19.01 | 21.23 | 24.57 | 1.03 | 3.25 | 6.59 |
| CV-Bench 3D | `vlmevalkit_defaults` | 1200 | 67.67 | 72.08 | 73.92 | 80.67 | 4.42 | 6.25 | 13.00 |
| WeMath | `vlmevalkit_cot_qwen32b_judge` | 1740 | 45.75 | 57.41 | 65.34 | 68.79 | 11.67 | 19.60 | 23.05 |
| MathVision | `vlmevalkit_defaults_qwen32b_judge` | 3040 | 19.08 | 24.34 | 27.40 | 27.24 | 5.26 | 8.32 | 8.16 |
| ERQA | `vlmevalkit_defaults` | 400 | 35.50 | 35.50 | 38.00 | 39.50 | 0.00 | 2.50 | 4.00 |
| TreeBench | `vlmevalkit_defaults` | 405 | 37.53 | 40.74 | 40.99 | 41.98 | 3.21 | 3.46 | 4.44 |
| CountBenchQA | `vlmevalkit_defaults` | 487 | 62.42 | 67.15 | 82.96 | 84.60 | 4.72 | 20.53 | 22.18 |
| MathVerse | `vlmevalkit_defaults_qwen32b_judge` | 788 | 34.14 | 40.74 | 43.65 | 46.70 | 6.60 | 9.52 | 12.56 |
| CharXivReason | `vlmevalkit_defaults_qwen32b_judge` | 1000 | 28.60 | 33.50 | 40.30 | 46.90 | 4.90 | 11.70 | 18.30 |
| CountQA | `vlmevalkit_cot_boxed` | 1528 | 14.66 | 15.97 | 21.53 | 22.12 | 1.31 | 6.87 | 7.46 |
| PhyX mini MC | `vlmevalkit_defaults` | 1000 | 43.40 | 43.20 | 43.40 | 49.40 | -0.20 | 0.00 | 6.00 |
| SpatialVizBench COT | `vlmevalkit_cot` | 1180 | 25.76 | 26.44 | 26.78 | 32.46 | 0.68 | 1.02 | 6.69 |
| MM-HELIX | `vlmevalkit_boxed_defaults` | 1290 | 3.80 | 3.80 | 5.43 | 6.20 | 0.00 | 1.63 | 2.40 |
| Physics | `vlmevalkit_reasoning` | 1297 | 16.11 | 20.43 | 21.59 | 26.06 | 4.32 | 5.47 | 9.95 |
| TableVQABench | `vlmevalkit_defaults` | 1500 | 69.81 | 72.37 | 75.39 | 77.44 | 2.56 | 5.57 | 7.63 |
| MMMU-ProVis | `vlmevalkit_cot_max2048` | 1730 | 26.01 | 29.71 | 35.32 | 39.88 | 3.70 | 9.31 | 13.87 |
| Blink | `vlmevalkit_defaults` | 1901 | 46.66 | 46.98 | 54.02 | 59.13 | 0.32 | 7.36 | 12.47 |
| Average |  |  | 37.06 | 40.07 | 44.74 | 48.49 | 3.01 | 7.69 | 11.44 |
| Average excl. ScreenSpot |  |  | 35.93 | 39.44 | 43.77 | 47.26 | 3.52 | 7.84 | 11.34 |

Normalization notes:
- `MM-HELIX`: weighted mean over category `items * average_score` from the generated results TSV.
- `TableVQABench`: macro mean over the reported split `average_scores` values.
- `SEEPhys`: nested `Overall / Accuracy (%)` value.
- Judge-backed datasets use the local Qwen3-32B judge configured by the queue.
- `MathVerse`: local Qwen3-32B binary judge outputs such as `Judgement: 1` are counted as correct.

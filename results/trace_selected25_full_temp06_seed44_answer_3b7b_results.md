# Qwen2.5-VL Selected25 Full Temp0.6 Seed 44 Answer-GRPO Benchmark Results

Subset manifest root: `selected25 full; candidate benchmarks use trace_candidate24_full subset manifests; extra benchmarks use full VLMEvalKit datasets`

Each benchmark has exactly one normalized score. Scores are percentages when the evaluator reports accuracy-like metrics.

| Benchmark | Prompt / Dataset | Rows | Base | Answer GRPO 500 | 7B Base | 7B Answer GRPO 500 | Answer GRPO 500 - Base | 7B Base - Base | 7B Answer GRPO 500 - Base |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ChartMuseum | `vlmevalkit_defaults_qwen32b_judge_test` | 1000 | 18.10 | 20.80 | 24.30 | 32.60 | 2.70 | 6.20 | 14.50 |
| Game-QA-Lite | `vlmevalkit_cot_boxed` | 2633 | 17.74 | 20.39 | 24.88 | 29.13 | 2.66 | 7.14 | 11.39 |
| ScreenSpot | `vlmevalkit_defaults_sample200` | 1272 | 67.37 | 66.90 | 73.11 | 77.36 | -0.47 | 5.74 | 9.98 |
| ChartQAPro | `vlmevalkit_faithful_cot` | 1948 | 31.25 | 32.98 | 46.28 | 48.95 | 1.73 | 15.03 | 17.70 |
| PuzzleVQA | `vlmevalkit_reasoning` | 2000 | 32.10 | 39.75 | 47.05 | 52.65 | 7.65 | 14.95 | 20.55 |
| VStarBench | `vlmevalkit_defaults` | 191 | 67.54 | 68.59 | 77.49 | 74.35 | 1.05 | 9.95 | 6.81 |
| LogicVista | `vlmevalkit_defaults_qwen32b_judge` | 447 | 38.03 | 44.30 | 41.61 | 47.43 | 6.26 | 3.58 | 9.40 |
| MathVista | `vlmevalkit_defaults_qwen32b_judge` | 1000 | 59.40 | 64.00 | 68.30 | 73.10 | 4.60 | 8.90 | 13.70 |
| VisualPuzzles | `vlmevalkit_reasoning` | 1168 | 17.89 | 19.01 | 18.58 | 21.83 | 1.11 | 0.68 | 3.94 |
| CV-Bench 3D | `vlmevalkit_defaults` | 1200 | 53.67 | 65.67 | 80.00 | 81.58 | 12.00 | 26.33 | 27.92 |
| WeMath | `vlmevalkit_cot_qwen32b_judge` | 1740 | 47.36 | 57.01 | 61.95 | 67.36 | 9.66 | 14.60 | 20.00 |
| MathVision | `vlmevalkit_defaults_qwen32b_judge` | 3040 | 20.86 | 24.21 | 25.16 | 28.09 | 3.36 | 4.31 | 7.24 |
| ERQA | `vlmevalkit_defaults` | 400 | 34.75 | 36.50 | 38.75 | 40.00 | 1.75 | 4.00 | 5.25 |
| TreeBench | `vlmevalkit_defaults` | 405 | 41.73 | 41.73 | 42.47 | 44.94 | 0.00 | 0.74 | 3.21 |
| CountBenchQA | `vlmevalkit_defaults` | 487 | 65.50 | 68.79 | 81.93 | 84.80 | 3.29 | 16.43 | 19.30 |
| MathVerse | `vlmevalkit_defaults_qwen32b_judge` | 788 | 20.56 | 20.43 | 22.84 | 25.00 | -0.13 | 2.28 | 4.44 |
| CharXivReason | `vlmevalkit_defaults_qwen32b_judge` | 1000 | 29.10 | 35.60 | 38.70 | 46.90 | 6.50 | 9.60 | 17.80 |
| CountQA | `vlmevalkit_cot_boxed` | 1528 | 13.55 | 15.25 | 20.16 | 23.04 | 1.70 | 6.61 | 9.49 |
| PhyX mini MC | `vlmevalkit_defaults` | 1000 | 22.60 | 32.90 | 38.80 | 47.40 | 10.30 | 16.20 | 24.80 |
| SpatialVizBench COT | `vlmevalkit_cot` | 1180 | 24.75 | 27.37 | 26.61 | 31.36 | 2.63 | 1.86 | 6.61 |
| MM-HELIX | `vlmevalkit_boxed_defaults` | 1290 | 3.65 | 3.02 | 4.21 | 6.35 | -0.63 | 0.56 | 2.70 |
| Physics | `vlmevalkit_reasoning` | 1297 | 23.98 | 19.97 | 18.27 | 26.99 | -4.01 | -5.71 | 3.01 |
| TableVQABench | `vlmevalkit_defaults` | 1500 | 69.09 | 71.97 | 75.73 | 78.40 | 2.88 | 6.64 | 9.31 |
| MMMU-ProVis | `vlmevalkit_cot_max2048` | 1730 | 27.34 | 30.98 | 34.39 | 39.42 | 3.64 | 7.05 | 12.08 |
| Blink | `vlmevalkit_defaults` | 1901 | 42.35 | 46.03 | 52.29 | 58.50 | 3.68 | 9.94 | 16.15 |
| Average |  |  | 35.61 | 38.97 | 43.35 | 47.50 | 3.36 | 7.74 | 11.89 |
| Average excl. ScreenSpot |  |  | 34.29 | 37.80 | 42.11 | 46.26 | 3.52 | 7.83 | 11.97 |

Normalization notes:
- `MM-HELIX`: weighted mean over category `items * average_score` from the generated results TSV; seed44 3B-base had two row-level evaluator exceptions, counted as zero.
- `TableVQABench`: macro mean over the reported split `average_scores` values.
- `SEEPhys`: nested `Overall / Accuracy (%)` value.
- Judge-backed datasets use the local Qwen3-32B judge configured by the queue.

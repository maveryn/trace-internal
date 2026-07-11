# Qwen2.5-VL-3B TRACE Candidate37 200-Row Benchmark Results

Subset manifest root: `benchmark/subsets/trace_candidate37_200`

Each benchmark has exactly one normalized score. Scores are percentages when the evaluator reports accuracy-like metrics.

| Benchmark | Prompt / Dataset | Rows | Base | Step 400 | Step 500 | Step 600 | Step 400 - Base | Step 500 - Base | Step 600 - Base |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ChartMuseum | `vlmevalkit_defaults_qwen32b_judge_test` | 200 | 22.50 | 23.50 | 26.50 | 25.50 | 1.00 | 4.00 | 3.00 |
| Game-QA-Lite | `vlmevalkit_cot_boxed` | 200 | 20.50 | 27.00 | 27.50 | 27.00 | 6.50 | 7.00 | 6.50 |
| MindCubeBench tiny | `vlmevalkit_defaults` | 200 | 35.50 | 32.50 | 31.50 | 36.00 | -3.00 | -4.00 | 0.50 |
| ScreenSpot | `vlmevalkit_defaults_sample200` | 200 | 43.66 | 41.67 | 43.42 | 40.18 | -1.99 | -0.24 | -3.48 |
| ScreenSpot-Pro | `vlmevalkit_defaults_sample200` | 158/200/200/200 | 22.88 | 17.03 | 15.21 | 16.37 | -5.85 | -7.66 | -6.50 |
| ChartQAPro | `vlmevalkit_faithful_cot` | 200 | 29.60 | 15.05 | 13.10 | 10.34 | -14.56 | -16.50 | -19.26 |
| PuzzleVQA | `vlmevalkit_reasoning` | 200 | 31.00 | 33.50 | 41.00 | 34.50 | 2.50 | 10.00 | 3.50 |
| VStarBench | `vlmevalkit_defaults` | 191 | 71.73 | 72.77 | 75.39 | 71.73 | 1.05 | 3.66 | 0.00 |
| LogicVista | `vlmevalkit_defaults_qwen32b_judge` | 200 | 34.00 | 41.50 | 43.00 | 39.00 | 7.50 | 9.00 | 5.00 |
| Omni3DBench | `vlmevalkit_defaults` | 200 | 41.43 | 34.55 | 30.99 | 35.25 | -6.88 | -10.44 | -6.18 |
| MathVista | `vlmevalkit_defaults_qwen32b_judge` | 200 | 68.50 | 67.50 | 69.00 | 68.50 | -1.00 | 0.50 | 0.00 |
| VisualPuzzles | `vlmevalkit_reasoning` | 200 | 24.00 | 25.50 | 25.50 | 21.00 | 1.50 | 1.50 | -3.00 |
| CV-Bench 3D | `vlmevalkit_defaults` | 200 | 49.50 | 56.00 | 57.50 | 49.50 | 6.50 | 8.00 | 0.00 |
| OmniSpatialBench manual CoT | `vlmevalkit_cot` | 200 | 44.00 | 42.00 | 45.50 | 33.00 | -2.00 | 1.50 | -11.00 |
| WeMath | `vlmevalkit_cot_qwen32b_judge` | 200 | 48.50 | 58.00 | 59.00 | 60.50 | 9.50 | 10.50 | 12.00 |
| MathVision | `vlmevalkit_defaults_qwen32b_judge` | 200 | 17.50 | 17.50 | 24.50 | 22.50 | 0.00 | 7.00 | 5.00 |
| RefSpatial-Bench | `vlmevalkit_defaults` | 100 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| QSpatial plus | `vlmevalkit_reasoning` | 101 | 1.01 | 0.00 | 0.00 | 0.00 | -1.01 | -1.01 | -1.01 |
| ERQA | `vlmevalkit_defaults` | 200 | 30.50 | 31.50 | 32.00 | 31.50 | 1.00 | 1.50 | 1.00 |
| TreeBench | `vlmevalkit_defaults` | 200 | 40.00 | 34.50 | 42.00 | 36.00 | -5.50 | 2.00 | -4.00 |
| CountBenchQA | `vlmevalkit_defaults` | 200 | 71.00 | 73.00 | 73.50 | 74.00 | 2.00 | 2.50 | 3.00 |
| MathVerse | `vlmevalkit_defaults_qwen32b_judge` | 200 | 15.50 | 20.00 | 19.00 | 17.50 | 4.50 | 3.50 | 2.00 |
| CharXivReason | `vlmevalkit_defaults_qwen32b_judge` | 200 | 30.50 | 31.50 | 31.00 | 32.00 | 1.00 | 0.50 | 1.50 |
| CountQA | `vlmevalkit_cot_boxed` | 200 | 16.50 | 15.00 | 17.50 | 16.00 | -1.50 | 1.00 | -0.50 |
| PhyX mini MC | `vlmevalkit_defaults` | 200 | 34.00 | 37.00 | 46.00 | 36.00 | 3.00 | 12.00 | 2.00 |
| VisuLogic | `vlmevalkit_reasoning` | 200 | 24.50 | 22.50 | 20.50 | 23.50 | -2.00 | -4.00 | -1.00 |
| SPBench SI COT | `vlmevalkit_cot` | 200 | 39.24 | 43.99 | 42.95 | 43.58 | 4.75 | 3.71 | 4.35 |
| SpatialVizBench COT | `vlmevalkit_cot` | 200 | 28.50 | 26.00 | 29.50 | 29.00 | -2.50 | 1.00 | 0.50 |
| MM-HELIX | `vlmevalkit_boxed_defaults` | 200 | 3.50 | 3.00 | 6.50 | 2.00 | -0.50 | 3.00 | -1.50 |
| Physics | `vlmevalkit_reasoning` | 200 | 11.00 | 15.00 | 14.50 | 16.00 | 4.00 | 3.50 | 5.00 |
| TableVQABench | `vlmevalkit_defaults` | 200 | 73.12 | 75.10 | 72.67 | 75.37 | 1.98 | -0.45 | 2.25 |
| MMMU-ProVis | `vlmevalkit_cot_max2048` | 200 | 24.00 | 32.50 | 33.50 | 30.50 | 8.50 | 9.50 | 6.50 |
| Blink | `vlmevalkit_defaults` | 200 | 40.00 | 46.00 | 47.50 | 44.50 | 6.00 | 7.50 | 4.50 |
| SEEPhys | `vlmevalkit_reasoning` | 200 | 7.50 | 11.00 | 10.50 | 11.00 | 3.50 | 3.00 | 3.50 |
| InfoVQA | `vlmevalkit_defaults_val` | 200 | 75.28 | 75.92 | 74.50 | 75.30 | 0.64 | -0.78 | 0.02 |
| CharXivDesc | `vlmevalkit_defaults_qwen32b_judge` | 200 | 61.50 | 59.00 | 63.50 | 69.50 | -2.50 | 2.00 | 8.00 |
| VLMBias | `vlmevalkit_defaults` | 200 | 20.50 | 18.50 | 17.50 | 20.00 | -2.00 | -3.00 | -0.50 |
| Average |  |  | 33.85 | 34.50 | 35.76 | 34.44 | 0.65 | 1.91 | 0.59 |
| Average excl. ScreenSpot |  |  | 33.88 | 34.79 | 36.12 | 34.78 | 0.91 | 2.24 | 0.90 |

Normalization notes:
- `MM-HELIX`: weighted mean over category `items * average_score` from the generated results TSV.
- `TableVQABench`: macro mean over the reported split `average_scores` values.
- `SEEPhys`: nested `Overall / Accuracy (%)` value.
- Judge-backed datasets use the local Qwen3-32B judge configured by the queue.

# Qwen2.5-VL-3B TRACE Candidate37 200-Row Benchmark Results

Subset manifest root: `benchmark/subsets/trace_candidate37_200`

Each benchmark has exactly one normalized score. Scores are percentages when the evaluator reports accuracy-like metrics.

| Benchmark | Prompt / Dataset | Rows | Base | Step 400 | Step 400 - Base |
| --- | --- | ---: | ---: | ---: | ---: |
| ChartMuseum | `vlmevalkit_defaults_qwen32b_judge_test` | 200 | 22.50 | 23.50 | 1.00 |
| Game-QA-Lite | `vlmevalkit_cot_boxed` | 200 | 20.50 | 27.00 | 6.50 |
| MindCubeBench tiny | `vlmevalkit_defaults` | 200 | 35.50 | 32.50 | -3.00 |
| ScreenSpot | `vlmevalkit_defaults_sample200` | 200 | 43.66 | 41.67 | -1.99 |
| ScreenSpot-Pro | `vlmevalkit_defaults_sample200` | 158/200 | 22.88 | 17.03 | -5.85 |
| ChartQAPro | `vlmevalkit_faithful_cot` | 200 | 29.60 | 15.05 | -14.56 |
| PuzzleVQA | `vlmevalkit_reasoning` | 200 | 31.00 | 33.50 | 2.50 |
| VStarBench | `vlmevalkit_defaults` | 191 | 71.73 | 72.77 | 1.05 |
| LogicVista | `vlmevalkit_defaults_qwen32b_judge` | 200 | 34.00 | 41.50 | 7.50 |
| Omni3DBench | `vlmevalkit_defaults` | 200 | 41.43 | 34.55 | -6.88 |
| MathVista | `vlmevalkit_defaults_qwen32b_judge` | 200 | 68.50 | 67.50 | -1.00 |
| VisualPuzzles | `vlmevalkit_reasoning` | 200 | 24.00 | 25.50 | 1.50 |
| CV-Bench 3D | `vlmevalkit_defaults` | 200 | 49.50 | 56.00 | 6.50 |
| OmniSpatialBench manual CoT | `vlmevalkit_cot` | 200 | 44.00 | 42.00 | -2.00 |
| WeMath | `vlmevalkit_cot_qwen32b_judge` | 200 | 48.50 | 58.00 | 9.50 |
| MathVision | `vlmevalkit_defaults_qwen32b_judge` | 200 | 17.50 | 17.50 | 0.00 |
| RefSpatial-Bench | `vlmevalkit_defaults` | 100 | 0.00 | 0.00 | 0.00 |
| QSpatial plus | `vlmevalkit_reasoning` | 101 | 1.01 | 0.00 | -1.01 |
| ERQA | `vlmevalkit_defaults` | 200 | 30.50 | 31.50 | 1.00 |
| TreeBench | `vlmevalkit_defaults` | 200 | 40.00 | 34.50 | -5.50 |
| CountBenchQA | `vlmevalkit_defaults` | 200 | 71.00 | 73.00 | 2.00 |
| MathVerse | `vlmevalkit_defaults_qwen32b_judge` | 200 | 15.50 | 20.00 | 4.50 |
| CharXivReason | `vlmevalkit_defaults_qwen32b_judge` | 200 | 30.50 | 31.50 | 1.00 |
| CountQA | `vlmevalkit_cot_boxed` | 200 | 16.50 | 15.00 | -1.50 |
| PhyX mini MC | `vlmevalkit_defaults` | 200 | 34.00 | 37.00 | 3.00 |
| VisuLogic | `vlmevalkit_reasoning` | 200 | 24.50 | 22.50 | -2.00 |
| SPBench SI COT | `vlmevalkit_cot` | 200 | 39.24 | 43.99 | 4.75 |
| SpatialVizBench COT | `vlmevalkit_cot` | 200 | 28.50 | 26.00 | -2.50 |
| MM-HELIX | `vlmevalkit_boxed_defaults` | 200 | 3.50 | 3.00 | -0.50 |
| Physics | `vlmevalkit_reasoning` | 200 | 11.00 | 15.00 | 4.00 |
| TableVQABench | `vlmevalkit_defaults` | 200 | 73.12 | 75.10 | 1.98 |
| MMMU-ProVis | `vlmevalkit_cot_max2048` | 200 | 24.00 | 32.50 | 8.50 |
| Blink | `vlmevalkit_defaults` | 200 | 40.00 | 46.00 | 6.00 |
| SEEPhys | `vlmevalkit_reasoning` | 200 | 7.50 | 11.00 | 3.50 |
| InfoVQA | `vlmevalkit_defaults_val` | 200 | 75.28 | 75.92 | 0.64 |
| CharXivDesc | `vlmevalkit_defaults_qwen32b_judge` | 200 | 61.50 | 59.00 | -2.50 |
| VLMBias | `vlmevalkit_defaults` | 200 | 20.50 | 18.50 | -2.00 |
| Average |  |  | 33.85 | 34.50 | 0.65 |
| Average excl. ScreenSpot |  |  | 33.88 | 34.79 | 0.91 |

Normalization notes:
- `MM-HELIX`: weighted mean over category `items * average_score` from the generated results TSV.
- `TableVQABench`: macro mean over the reported split `average_scores` values.
- `SEEPhys`: nested `Overall / Accuracy (%)` value.
- Judge-backed datasets use the local Qwen3-32B judge configured by the queue.

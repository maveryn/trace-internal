# TRACE Final20 Temp0.6 Seed42 Benchmark Results: game-rl-qwen25vl7b

Subset manifest root: `final20 full eval; candidate benchmarks use trace_candidate24_full subset manifests; SpatialVizBench/TableVQABench/VisualPuzzles use full VLMEvalKit datasets`

Each benchmark has exactly one normalized score. Scores are percentages when the evaluator reports accuracy-like metrics.

| Benchmark | Prompt / Dataset | Rows | game-rl-qwen25vl7b |
| --- | --- | ---: | ---: |
| ChartMuseum | `vlmevalkit_defaults_qwen32b_judge_test` | 1000 | 24.50 |
| Game-QA-Lite | `vlmevalkit_cot_boxed` | 2633 | 30.27 |
| ScreenSpot | `vlmevalkit_defaults_sample200` | 1272 | 75.24 |
| ChartQAPro | `vlmevalkit_faithful_cot` | 1948 | 46.85 |
| PuzzleVQA | `vlmevalkit_reasoning` | 2000 | 49.45 |
| LogicVista | `vlmevalkit_defaults_qwen32b_judge` | 447 | 44.07 |
| MathVista | `vlmevalkit_defaults_qwen32b_judge` | 1000 | 68.00 |
| VisualPuzzles | `vlmevalkit_reasoning` | 1168 | 19.18 |
| CV-Bench 3D | `vlmevalkit_defaults` | 1200 | 75.83 |
| WeMath | `vlmevalkit_cot_qwen32b_judge` | 1740 | 65.34 |
| MathVision | `vlmevalkit_defaults_qwen32b_judge` | 3040 | 26.48 |
| TreeBench | `vlmevalkit_defaults` | 405 | 39.26 |
| CountBenchQA | `vlmevalkit_defaults` | 487 | 84.80 |
| CharXivReason | `vlmevalkit_defaults_qwen32b_judge` | 1000 | 39.70 |
| PhyX mini MC | `vlmevalkit_defaults` | 1000 | 40.40 |
| SpatialVizBench COT | `vlmevalkit_cot` | 1180 | 29.41 |
| Physics | `vlmevalkit_reasoning` | 1297 | 21.05 |
| TableVQABench | `vlmevalkit_defaults` | 1500 | 74.13 |
| MMMU-ProVis | `vlmevalkit_cot_max2048` | 1730 | 35.84 |
| Blink | `vlmevalkit_defaults` | 1901 | 54.08 |
| Average |  |  | 47.19 |
| Average excl. ScreenSpot |  |  | 45.79 |

Normalization notes:
- `MM-HELIX`: weighted mean over category `items * average_score` from the generated results TSV.
- `TableVQABench`: macro mean over the reported split `average_scores` values.
- `SEEPhys`: nested `Overall / Accuracy (%)` value.
- Judge-backed datasets use the local Qwen3-32B judge configured by the queue.

# TRACE Final20 Temp0.6 Seed42 Benchmark Results: vero-qwen25-7b

Subset manifest root: `final20 full eval; candidate benchmarks use trace_candidate24_full subset manifests; SpatialVizBench/TableVQABench/VisualPuzzles use full VLMEvalKit datasets`

Each benchmark has exactly one normalized score. Scores are percentages when the evaluator reports accuracy-like metrics.

| Benchmark | Prompt / Dataset | Rows | vero-qwen25-7b |
| --- | --- | ---: | ---: |
| ChartMuseum | `vlmevalkit_defaults_qwen32b_judge_test` | 1000 | 29.00 |
| Game-QA-Lite | `vlmevalkit_cot_boxed` | 2633 | 46.79 |
| ScreenSpot | `vlmevalkit_defaults_sample200` | 1272 | 36.87 |
| ChartQAPro | `vlmevalkit_faithful_cot` | 1948 | 41.65 |
| PuzzleVQA | `vlmevalkit_reasoning` | 2000 | 49.80 |
| LogicVista | `vlmevalkit_defaults_qwen32b_judge` | 447 | 45.86 |
| MathVista | `vlmevalkit_defaults_qwen32b_judge` | 1000 | 76.50 |
| VisualPuzzles | `vlmevalkit_reasoning` | 1168 | 23.54 |
| CV-Bench 3D | `vlmevalkit_defaults` | 1200 | 82.67 |
| WeMath | `vlmevalkit_cot_qwen32b_judge` | 1740 | 72.36 |
| MathVision | `vlmevalkit_defaults_qwen32b_judge` | 3040 | 27.34 |
| TreeBench | `vlmevalkit_defaults` | 405 | 41.73 |
| CountBenchQA | `vlmevalkit_defaults` | 487 | 83.57 |
| CharXivReason | `vlmevalkit_defaults_qwen32b_judge` | 1000 | 46.40 |
| PhyX mini MC | `vlmevalkit_defaults` | 1000 | 46.30 |
| SpatialVizBench COT | `vlmevalkit_cot` | 1180 | 31.19 |
| Physics | `vlmevalkit_reasoning` | 1297 | 17.73 |
| TableVQABench | `vlmevalkit_defaults` | 1500 | 11.44 |
| MMMU-ProVis | `vlmevalkit_cot_max2048` | 1730 | 40.00 |
| Blink | `vlmevalkit_defaults` | 1901 | 57.29 |
| Average |  |  | 45.40 |

Normalization notes:
- `MM-HELIX`: weighted mean over category `items * average_score` from the generated results TSV.
- `TableVQABench`: macro mean over the reported split `average_scores` values.
- `SEEPhys`: nested `Overall / Accuracy (%)` value.
- Judge-backed datasets use the local Qwen3-32B judge configured by the queue.

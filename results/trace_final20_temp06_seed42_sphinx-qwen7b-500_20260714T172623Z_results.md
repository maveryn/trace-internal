# TRACE Final20 Temp0.6 Seed42 Benchmark Results: sphinx-qwen7b-500

Subset manifest root: `final20 full eval; candidate benchmarks use trace_candidate24_full subset manifests; SpatialVizBench/TableVQABench/VisualPuzzles use full VLMEvalKit datasets`

Each benchmark has exactly one normalized score. Scores are percentages when the evaluator reports accuracy-like metrics.

| Benchmark | Prompt / Dataset | Rows | sphinx-qwen7b-500 |
| --- | --- | ---: | ---: |
| ChartMuseum | `vlmevalkit_defaults_qwen32b_judge_test` | 1000 | 24.40 |
| Game-QA-Lite | `vlmevalkit_cot_boxed` | 2633 | 25.07 |
| ScreenSpot | `vlmevalkit_defaults_sample200` | 1272 | 81.05 |
| ChartQAPro | `vlmevalkit_faithful_cot` | 1948 | 44.68 |
| PuzzleVQA | `vlmevalkit_reasoning` | 2000 | 47.15 |
| LogicVista | `vlmevalkit_defaults_qwen32b_judge` | 447 | 43.40 |
| MathVista | `vlmevalkit_defaults_qwen32b_judge` | 1000 | 70.80 |
| VisualPuzzles | `vlmevalkit_reasoning` | 1168 | 18.49 |
| CV-Bench 3D | `vlmevalkit_defaults` | 1200 | 79.92 |
| WeMath | `vlmevalkit_cot_qwen32b_judge` | 1740 | 65.17 |
| MathVision | `vlmevalkit_defaults_qwen32b_judge` | 3040 | 26.28 |
| TreeBench | `vlmevalkit_defaults` | 405 | 40.49 |
| CountBenchQA | `vlmevalkit_defaults` | 487 | 83.16 |
| CharXivReason | `vlmevalkit_defaults_qwen32b_judge` | 1000 | 40.60 |
| PhyX mini MC | `vlmevalkit_defaults` | 1000 | 40.90 |
| SpatialVizBench COT | `vlmevalkit_cot` | 1180 | 27.88 |
| Physics | `vlmevalkit_reasoning` | 1297 | 20.35 |
| TableVQABench | `vlmevalkit_defaults` | 1500 | 73.12 |
| MMMU-ProVis | `vlmevalkit_cot_max2048` | 1730 | 36.99 |
| Blink | `vlmevalkit_defaults` | 1901 | 55.34 |
| Average |  |  | 47.26 |

Normalization notes:
- `MM-HELIX`: weighted mean over category `items * average_score` from the generated results TSV.
- `TableVQABench`: macro mean over the reported split `average_scores` values.
- `SEEPhys`: nested `Overall / Accuracy (%)` value.
- Judge-backed datasets use the local Qwen3-32B judge configured by the queue.

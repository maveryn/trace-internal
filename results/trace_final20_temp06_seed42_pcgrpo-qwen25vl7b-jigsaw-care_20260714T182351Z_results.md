# TRACE Final20 Temp0.6 Seed42 Benchmark Results: pcgrpo-qwen25vl7b-jigsaw-care

Subset manifest root: `final20 full eval; candidate benchmarks use trace_candidate24_full subset manifests; SpatialVizBench/TableVQABench/VisualPuzzles use full VLMEvalKit datasets`

Each benchmark has exactly one normalized score. Scores are percentages when the evaluator reports accuracy-like metrics.

| Benchmark | Prompt / Dataset | Rows | pcgrpo-qwen25vl7b-jigsaw-care |
| --- | --- | ---: | ---: |
| ChartMuseum | `vlmevalkit_defaults_qwen32b_judge_test` | 1000 | 25.10 |
| Game-QA-Lite | `vlmevalkit_cot_boxed` | 2633 | 25.94 |
| ScreenSpot | `vlmevalkit_defaults_sample200` | 1272 | 8.41 |
| ChartQAPro | `vlmevalkit_faithful_cot` | 1948 | 41.27 |
| PuzzleVQA | `vlmevalkit_reasoning` | 2000 | 50.05 |
| LogicVista | `vlmevalkit_defaults_qwen32b_judge` | 447 | 43.18 |
| MathVista | `vlmevalkit_defaults_qwen32b_judge` | 1000 | 71.10 |
| VisualPuzzles | `vlmevalkit_reasoning` | 1168 | 20.21 |
| CV-Bench 3D | `vlmevalkit_defaults` | 1200 | 81.08 |
| WeMath | `vlmevalkit_cot_qwen32b_judge` | 1740 | 65.06 |
| MathVision | `vlmevalkit_defaults_qwen32b_judge` | 3040 | 25.39 |
| TreeBench | `vlmevalkit_defaults` | 405 | 40.74 |
| CountBenchQA | `vlmevalkit_defaults` | 487 | 82.96 |
| CharXivReason | `vlmevalkit_defaults_qwen32b_judge` | 1000 | 40.80 |
| PhyX mini MC | `vlmevalkit_defaults` | 1000 | 42.70 |
| SpatialVizBench COT | `vlmevalkit_cot` | 1180 | 29.49 |
| Physics | `vlmevalkit_reasoning` | 1297 | 16.73 |
| TableVQABench | `vlmevalkit_defaults` | 1500 | 69.68 |
| MMMU-ProVis | `vlmevalkit_cot_max2048` | 1730 | 34.28 |
| Blink | `vlmevalkit_defaults` | 1901 | 56.23 |
| Average |  |  | 43.52 |

Normalization notes:
- `MM-HELIX`: weighted mean over category `items * average_score` from the generated results TSV.
- `TableVQABench`: macro mean over the reported split `average_scores` values.
- `SEEPhys`: nested `Overall / Accuracy (%)` value.
- Judge-backed datasets use the local Qwen3-32B judge configured by the queue.

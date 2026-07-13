# TRACE Annotation Additive 0.50 Step500 Ann29 greedy4096 Benchmark Results

Subset manifest root: `trace_candidate24_full minus chartqa/visiongraph_q3 plus full extra7`

Each benchmark has exactly one normalized score. Scores are percentages when the evaluator reports accuracy-like metrics.

| Benchmark | Prompt / Dataset | Rows | trace-qwen25vl3b-rlvr-ann-additive-0p50-sectioned-step500 |
| --- | --- | ---: | ---: |
| ChartMuseum | `vlmevalkit_defaults_qwen32b_judge_test` | 1000 | 21.10 |
| Game-QA-Lite | `vlmevalkit_cot_boxed` | 2633 | 22.94 |
| ScreenSpot | `vlmevalkit_defaults_sample200` | 1272 | 75.47 |
| ScreenSpot-Pro | `vlmevalkit_defaults_sample200` | 1581 | 22.83 |
| ChartQAPro | `vlmevalkit_faithful_cot` | 1948 | 33.84 |
| PuzzleVQA | `vlmevalkit_reasoning` | 2000 | 36.95 |
| VStarBench | `vlmevalkit_defaults` | 191 | 74.87 |
| LogicVista | `vlmevalkit_defaults_qwen32b_judge` | 447 | 40.72 |
| Omni3DBench | `vlmevalkit_defaults` | 501 | 35.40 |
| MathVista | `vlmevalkit_defaults_qwen32b_judge` | 1000 | 65.90 |
| VisualPuzzles | `vlmevalkit_reasoning` | 1168 | 18.84 |
| CV-Bench 3D | `vlmevalkit_defaults` | 1200 | 68.08 |
| WeMath | `vlmevalkit_cot_qwen32b_judge` | 1740 | 52.82 |
| MathVision | `vlmevalkit_defaults_qwen32b_judge` | 3040 | 21.68 |
| ERQA | `vlmevalkit_defaults` | 400 | 37.25 |
| TreeBench | `vlmevalkit_defaults` | 405 | 39.01 |
| CountBenchQA | `vlmevalkit_defaults` | 487 | 77.82 |
| MathVerse | `vlmevalkit_defaults_qwen32b_judge` | 788 | 19.54 |
| CharXivReason | `vlmevalkit_defaults_qwen32b_judge` | 1000 | 34.90 |
| CountQA | `vlmevalkit_cot_boxed` | 1528 | 16.69 |
| PhyX mini MC | `vlmevalkit_defaults` | 1000 | 36.80 |
| SPBench SI COT | `vlmevalkit_cot` | 1009 | 19.52 |
| SpatialVizBench COT | `vlmevalkit_cot` | 1180 | 27.46 |
| MM-HELIX | `vlmevalkit_boxed_defaults` | 1290 | 4.57 |
| Physics | `vlmevalkit_reasoning` | 1297 | 19.97 |
| TableVQABench | `vlmevalkit_defaults` | 1500 | 73.57 |
| MMMU-ProVis | `vlmevalkit_cot_max2048` | 1730 | 28.21 |
| Blink | `vlmevalkit_defaults` | 1901 | 49.87 |
| VLMBias | `vlmevalkit_defaults` | 2782 | 20.52 |
| Average |  |  | 37.83 |
| Average excl. ScreenSpot |  |  | 37.02 |

Normalization notes:
- `MM-HELIX`: weighted mean over category `items * average_score` from the generated results TSV.
- `TableVQABench`: macro mean over the reported split `average_scores` values.
- `SEEPhys`: nested `Overall / Accuracy (%)` value.
- Judge-backed datasets use the local Qwen3-32B judge configured by the queue.

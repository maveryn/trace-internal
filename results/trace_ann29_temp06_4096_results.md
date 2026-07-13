# TRACE Annotation Additive 0.50 Step500 Ann29 temp06_4096 Benchmark Results

Subset manifest root: `trace_candidate24_full minus chartqa/visiongraph_q3 plus full extra7`

Each benchmark has exactly one normalized score. Scores are percentages when the evaluator reports accuracy-like metrics.

| Benchmark | Prompt / Dataset | Rows | trace-qwen25vl3b-rlvr-ann-additive-0p50-sectioned-step500 |
| --- | --- | ---: | ---: |
| ChartMuseum | `vlmevalkit_defaults_qwen32b_judge_test` | 1000 | 18.00 |
| Game-QA-Lite | `vlmevalkit_cot_boxed` | 2633 | 21.31 |
| ScreenSpot | `vlmevalkit_defaults_sample200` | 1272 | 63.44 |
| ScreenSpot-Pro | `vlmevalkit_defaults_sample200` | 1581 | 20.68 |
| ChartQAPro | `vlmevalkit_faithful_cot` | 1948 | 33.82 |
| PuzzleVQA | `vlmevalkit_reasoning` | 2000 | 37.85 |
| VStarBench | `vlmevalkit_defaults` | 191 | 71.73 |
| LogicVista | `vlmevalkit_defaults_qwen32b_judge` | 447 | 36.47 |
| Omni3DBench | `vlmevalkit_defaults` | 501 | 34.73 |
| MathVista | `vlmevalkit_defaults_qwen32b_judge` | 1000 | 64.00 |
| VisualPuzzles | `vlmevalkit_reasoning` | 1168 | 17.38 |
| CV-Bench 3D | `vlmevalkit_defaults` | 1200 | 62.58 |
| WeMath | `vlmevalkit_cot_qwen32b_judge` | 1740 | 51.67 |
| MathVision | `vlmevalkit_defaults_qwen32b_judge` | 3040 | 21.88 |
| ERQA | `vlmevalkit_defaults` | 400 | 36.75 |
| TreeBench | `vlmevalkit_defaults` | 405 | 38.27 |
| CountBenchQA | `vlmevalkit_defaults` | 487 | 73.31 |
| MathVerse | `vlmevalkit_defaults_qwen32b_judge` | 788 | 22.59 |
| CharXivReason | `vlmevalkit_defaults_qwen32b_judge` | 1000 | 32.70 |
| CountQA | `vlmevalkit_cot_boxed` | 1528 | 17.54 |
| PhyX mini MC | `vlmevalkit_defaults` | 1000 | 33.80 |
| SPBench SI COT | `vlmevalkit_cot` | 1009 | 18.63 |
| SpatialVizBench COT | `vlmevalkit_cot` | 1180 | 28.14 |
| MM-HELIX | `vlmevalkit_boxed_defaults` | 1290 | 3.33 |
| Physics | `vlmevalkit_reasoning` | 1297 | 20.20 |
| TableVQABench | `vlmevalkit_defaults` | 1500 | 72.48 |
| MMMU-ProVis | `vlmevalkit_cot_max2048` | 1730 | 27.69 |
| Blink | `vlmevalkit_defaults` | 1901 | 47.03 |
| VLMBias | `vlmevalkit_defaults` | 2782 | 23.80 |
| Average |  |  | 36.27 |
| Average excl. ScreenSpot |  |  | 35.85 |

Normalization notes:
- `MM-HELIX`: weighted mean over category `items * average_score` from the generated results TSV.
- `TableVQABench`: macro mean over the reported split `average_scores` values.
- `SEEPhys`: nested `Overall / Accuracy (%)` value.
- Judge-backed datasets use the local Qwen3-32B judge configured by the queue.

# Qwen2.5-VL-7B TRACE Annotation Additive 0.50 Step500 Selected8 Temp0.6 Results

Subset manifest root: `trace_candidate24_full selected + full countqa`

Each benchmark has exactly one normalized score. Scores are percentages when the evaluator reports accuracy-like metrics.

| Benchmark | Prompt / Dataset | Rows | trace-qwen25vl7b-rlvr-ann-additive-0p50-sectioned-step500 |
| --- | --- | ---: | ---: |
| Game-QA-Lite | `vlmevalkit_cot_boxed` | 2633 | 25.64 |
| ScreenSpot | `vlmevalkit_defaults_sample200` | 1272 | 66.12 |
| ChartQAPro | `vlmevalkit_faithful_cot` | 1948 | 46.03 |
| VStarBench | `vlmevalkit_defaults` | 191 | 79.06 |
| WeMath | `vlmevalkit_cot_qwen32b_judge` | 1740 | 65.57 |
| MathVerse | `vlmevalkit_defaults_qwen32b_judge` | 788 | 25.13 |
| CountQA | `vlmevalkit_cot_boxed` | 1528 | 21.60 |
| Blink | `vlmevalkit_defaults` | 1901 | 55.23 |
| Average |  |  | 48.05 |
| Average excl. ScreenSpot |  |  | 45.79 |

Normalization notes:
- `MM-HELIX`: weighted mean over category `items * average_score` from the generated results TSV.
- `TableVQABench`: macro mean over the reported split `average_scores` values.
- `SEEPhys`: nested `Overall / Accuracy (%)` value.
- Judge-backed datasets use the local Qwen3-32B judge configured by the queue.

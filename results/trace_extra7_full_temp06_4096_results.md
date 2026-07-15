# Qwen2.5-VL Trace Extra7 Full Temp0.6-4096 Benchmark Results

Subset manifest root: `full VLMEvalKit datasets; no subset manifest`

Each benchmark has exactly one normalized score. Scores are percentages when the evaluator reports accuracy-like metrics.

| Benchmark | Prompt / Dataset | Rows | Base | trace-qwen25vl3b-easyr1-all1000-answer-nokl-step500 | qwen25vl7b-base | trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500 | trace-qwen25vl3b-easyr1-all1000-answer-nokl-step500 - Base | qwen25vl7b-base - Base | trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500 - Base |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Omni3DBench | `vlmevalkit_defaults` | 501 | 32.78 | 33.79 | 38.48 | 38.01 | 1.01 | 5.70 | 5.23 |
| VisualPuzzles | `vlmevalkit_reasoning` | 1168 | 16.10 | 18.58 | 18.24 | 20.55 | 2.48 | 2.14 | 4.45 |
| CountQA | `vlmevalkit_cot_boxed` | 1528 | 15.71 | 16.69 | 20.75 | 21.92 | 0.98 | 5.04 | 6.22 |
| SPBench SI COT | `vlmevalkit_cot` | 1009 | 16.15 | 18.53 | 19.62 | 19.33 | 2.38 | 3.47 | 3.17 |
| SpatialVizBench COT | `vlmevalkit_cot` | 1180 | 25.85 | 26.78 | 26.10 | 31.02 | 0.93 | 0.25 | 5.17 |
| MM-HELIX | `vlmevalkit_boxed_defaults` | 1290 | 4.03 | 4.88 | 5.89 | 6.43 | 0.85 | 1.86 | 2.40 |
| TableVQABench | `vlmevalkit_defaults` | 1500 | 68.45 | 71.31 | 73.63 | 78.13 | 2.85 | 5.17 | 9.68 |
| Average |  |  | 25.58 | 27.22 | 28.96 | 30.77 | 1.64 | 3.38 | 5.19 |
| Average excl. ScreenSpot |  |  | 25.58 | 27.22 | 28.96 | 30.77 | 1.64 | 3.38 | 5.19 |

Normalization notes:
- `MM-HELIX`: weighted mean over category `items * average_score` from the generated results TSV.
- `TableVQABench`: macro mean over the reported split `average_scores` values.
- `SEEPhys`: nested `Overall / Accuracy (%)` value.
- Judge-backed datasets use the local Qwen3-32B judge configured by the queue.

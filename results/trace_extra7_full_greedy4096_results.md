# Qwen2.5-VL TRACE Extra7 Full Greedy-4096 Benchmark Results

Subset manifest root: `full VLMEvalKit datasets; no subset manifest`

Each benchmark has exactly one normalized score. Scores are percentages when the evaluator reports accuracy-like metrics.

| Benchmark | Prompt / Dataset | Rows | Base | trace-qwen25vl3b-easyr1-all1000-answer-nokl-step500 | qwen25vl7b-base | trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500 | trace-qwen25vl3b-easyr1-all1000-answer-nokl-step500 - Base | qwen25vl7b-base - Base | trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500 - Base |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Omni3DBench | `vlmevalkit_defaults` | 501 | 35.11 | 35.25 | 37.36 | 36.35 | 0.14 | 2.25 | 1.24 |
| VisualPuzzles | `vlmevalkit_reasoning` | 1168 | 19.26 | 17.64 | 19.86 | 20.21 | -1.63 | 0.60 | 0.94 |
| CountQA | `vlmevalkit_cot_boxed` | 1528 | 15.90 | 15.31 | 22.77 | 22.19 | -0.59 | 6.87 | 6.28 |
| SPBench SI COT | `vlmevalkit_cot` | 1009 | 17.84 | 17.94 | 18.83 | 20.02 | 0.10 | 0.99 | 2.18 |
| SpatialVizBench COT | `vlmevalkit_cot` | 1180 | 21.53 | 27.71 | 26.36 | 29.41 | 6.19 | 4.83 | 7.88 |
| MM-HELIX | `vlmevalkit_boxed_defaults` | 1290 | 3.33 | 4.11 | 5.97 | 6.05 | 0.78 | 2.64 | 2.71 |
| TableVQABench | `vlmevalkit_defaults` | 1500 | 71.68 | 74.51 | 77.44 | 79.20 | 2.83 | 5.76 | 7.52 |
| Average |  |  | 26.38 | 27.50 | 29.80 | 30.49 | 1.12 | 3.42 | 4.11 |
| Average excl. ScreenSpot |  |  | 26.38 | 27.50 | 29.80 | 30.49 | 1.12 | 3.42 | 4.11 |

Normalization notes:
- `MM-HELIX`: weighted mean over category `items * average_score` from the generated results TSV.
- `TableVQABench`: macro mean over the reported split `average_scores` values.
- `SEEPhys`: nested `Overall / Accuracy (%)` value.
- Judge-backed datasets use the local Qwen3-32B judge configured by the queue.

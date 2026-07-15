# TRACE EvoChart Temp0.6 Seed42: Qwen2.5-VL-7B Base vs Answer GRPO

Subset manifest root: `benchmark/subsets/trace_candidate37_200`

Each benchmark has exactly one normalized score. Scores are percentages when the evaluator reports accuracy-like metrics.

| Benchmark | Prompt / Dataset | Rows | 7B Base | 7B Answer GRPO 500 | 7B Answer GRPO 500 - 7B Base |
| --- | --- | ---: | ---: | ---: | ---: |
| EvoChart | `vlmevalkit_boxed_defaults` | 1250 | 55.28 | 64.00 | 8.72 |
| Average |  |  | 55.28 | 64.00 | 8.72 |

Normalization notes:
- `MM-HELIX`: weighted mean over category `items * average_score` from the generated results TSV.
- `TableVQABench`: macro mean over the reported split `average_scores` values.
- `SEEPhys`: nested `Overall / Accuracy (%)` value.
- `QBench-Video`: row-count-weighted mean of the reported subtask accuracies.
- `VideoMMMU` uses its final accuracy row; `Video-TT` uses its nested `overall.score`.
- Judge-backed datasets use the local Qwen3-32B judge configured by the queue.

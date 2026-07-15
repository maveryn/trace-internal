# TRACE Video4 Temp0.6 Seed42 Benchmark Results: Base vs Answer GRPO 500

Subset manifest root: `full VLMEvalKit video4 eval; frame-based aliases with TRACE temp0.6 seed42 decoding`

Each benchmark has exactly one normalized score. Scores are percentages when the evaluator reports accuracy-like metrics.

| Benchmark | Prompt / Dataset | Rows | 7B Base | 7B Answer GRPO 500 | 7B Answer GRPO 500 - 7B Base |
| --- | --- | ---: | ---: | ---: | ---: |
| QBench-Video | `vlmevalkit_8frame_temp06` | 892 | 41.68 | 44.21 | 2.53 |
| VideoMMMU | `vlmevalkit_8frame_temp06` | 900 | 46.11 | 46.56 | 0.44 |
| Video-TT | `vlmevalkit_16frame_temp06` | 1000 | 38.40 | 37.20 | -1.20 |
| TempCompass | `vlmevalkit_8frame_temp06` | 7540 | 67.77 | 70.13 | 2.36 |
| Average |  |  | 48.49 | 49.52 | 1.03 |

Normalization notes:
- `MM-HELIX`: weighted mean over category `items * average_score` from the generated results TSV.
- `TableVQABench`: macro mean over the reported split `average_scores` values.
- `SEEPhys`: nested `Overall / Accuracy (%)` value.
- `QBench-Video`: row-count-weighted mean of the reported subtask accuracies.
- `VideoMMMU` uses its final accuracy row; `Video-TT` uses its nested `overall.score`.
- Judge-backed datasets use the local Qwen3-32B judge configured by the queue.

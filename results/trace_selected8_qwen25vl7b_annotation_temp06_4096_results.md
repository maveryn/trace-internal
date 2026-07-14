# Qwen2.5-VL-7B TRACE Selected8 Temp0.6 Results

Model comparison for the requested selected8 benchmarks. Scores are normalized percentages.

Decoding: `temperature=0.6`, `top_p=1.0`, `top_k=-1`, `max_tokens=4096`, `seed=42`.

| Benchmark | Prompt / Dataset | Rows | 7B Base | 7B Answer GRPO 500 | 7B Annotation GRPO 500 | Answer - Base | Annotation - Base | Annotation - Answer |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Blink | `vlmevalkit_defaults` | 1901 | 53.29 | 58.65 | 55.23 | 5.37 | 1.95 | -3.42 |
| ChartQAPro | `vlmevalkit_faithful_cot` | 1948 | 46.38 | 49.59 | 46.03 | 3.21 | -0.35 | -3.56 |
| CountQA | `vlmevalkit_cot_boxed` | 1528 | 20.75 | 21.92 | 21.60 | 1.18 | 0.85 | -0.33 |
| Game-QA-Lite | `vlmevalkit_cot_boxed` | 2633 | 25.07 | 29.09 | 25.64 | 4.03 | 0.57 | -3.46 |
| MathVerse | `vlmevalkit_defaults_qwen32b_judge` | 788 | 25.25 | 24.75 | 25.13 | -0.51 | -0.13 | 0.38 |
| WeMath | `vlmevalkit_cot_qwen32b_judge` | 1740 | 64.54 | 67.53 | 65.57 | 2.99 | 1.03 | -1.95 |
| VStarBench | `vlmevalkit_defaults` | 191 | 75.39 | 75.92 | 79.06 | 0.52 | 3.66 | 3.14 |
| ScreenSpot | `vlmevalkit_defaults_sample200` | 1272 | 77.12 | 77.83 | 66.12 | 0.71 | -11.01 | -11.71 |
| Average |  |  | 48.47 | 50.66 | 48.05 | 2.19 | -0.43 | -2.61 |
| Average excl. ScreenSpot |  |  | 44.89 | 47.26 | 45.79 | 2.37 | 0.90 | -1.48 |

Sources:
- Base and answer-GRPO numbers for all benchmarks except `CountQA`: `results/trace_candidate24_full_temp06_4096_results.xlsx`.
- Base and answer-GRPO numbers for `CountQA`: `results/trace_extra7_full_temp06_4096_results.xlsx`.
- Annotation-GRPO numbers: this selected8 run using `trace-qwen25vl7b-rlvr-ann-additive-0p50-sectioned-step500`.

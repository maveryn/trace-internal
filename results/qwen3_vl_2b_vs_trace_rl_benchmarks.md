# Qwen3-VL-2B vs Trace RL Benchmark Results

Models compared:

- Base: `Qwen3-VL-2B-Instruct`
- Latest RL: `trace_qwen3_2b_answer_51k_solve_0125_0750_uniform_4kresp_step500_merged`

Scoring:

- `judge` = batched Qwen3-32B extraction/scoring
- `deterministic` = upstream Vero task metric without LLM judge

## Results

| Benchmark | Prompt | Scoring | N | Base | Latest RL | Delta |
|---|---|---|---:|---:|---:|---:|
| ChartQA-Pro | ZS | judge | 1948 | 29.76 ± 1.03 | 30.04 ± 1.03 | +0.28 |
| ChartQA-Pro | Reasoning | judge | 1948 | 25.29 ± 0.97 | 25.89 ± 0.98 | +0.60 |
| MathVista Mini | ZS | judge | 1000 | 66.20 ± 1.50 | 66.90 ± 1.49 | +0.70 |
| MathVista Mini | Reasoning | judge | 1000 | 67.60 ± 1.48 | 67.30 ± 1.48 | -0.30 |
| MathVision TestMini | ZS | judge | 304 | 28.95 ± 2.61 | 33.55 ± 2.71 | +4.61 |
| MathVision TestMini | Reasoning | judge | 304 | 32.89 ± 2.70 | 30.26 ± 2.64 | -2.63 |
| BLINK | ZS | judge | 1901 | 50.92 ± 1.15 | 52.92 ± 1.15 | +2.00 |
| BLINK | Reasoning | judge | 1901 | 53.76 ± 1.14 | 54.45 ± 1.14 | +0.68 |
| EmbSpatial | ZS | judge | 3640 | 67.66 ± 0.78 | 67.25 ± 0.78 | -0.41 |
| EmbSpatial | Reasoning | judge | 3640 | 68.68 ± 0.77 | 69.62 ± 0.76 | +0.94 |
| CountQA | ZS | deterministic | 1528 | 23.82 ± 1.09 | 24.80 ± 1.11 | +0.98 |
| CountQA | Reasoning | deterministic | 1528 | 23.17 ± 1.08 | 22.58 ± 1.07 | -0.59 |
| GameQALite | ZS | deterministic | 2633 | 12.31 | 12.95 | +0.65 |
| VStarBench | ZS | deterministic | 191 | 70.16 | 76.96 | +6.81 |
| VStarBench | Reasoning | deterministic | 191 | 74.35 | 76.96 | +2.62 |
| MMMU-ProVis | ZS | deterministic | 1730 | 18.61 | 17.34 | -1.27 |
| ERQA | ZS | judge | 400 | 35.25 ± 2.39 | 36.00 ± 2.40 | +0.75 |
| ERQA | Reasoning | judge | 400 | 35.00 ± 2.39 | 38.25 ± 2.43 | +3.25 |
| Average | All | mixed | 18 rows | 43.58 | 44.67 | +1.09 |

## Result Files

| Benchmark | Prompt | Base File | Latest RL File |
|---|---|---|---|
| ChartQA-Pro | ZS | [base](../eval/outputs/qwen3_vl_2b_chartqa_pro_qwen3_thinking_zs/judge_summary.json) | [rl](../eval/outputs/trace_qwen3_2b_answer_51k_solve_0125_0750_uniform_4kresp_step500_chartqa_pro_qwen3_thinking_zs_rawpred/judge_summary.json) |
| ChartQA-Pro | Reasoning | [base](../eval/outputs/qwen3_vl_2b_chartqa_pro_reasoning_samplingq3_rawpred/judge_summary.json) | [rl](../eval/outputs/trace_qwen3_2b_answer_51k_solve_0125_0750_uniform_4kresp_step500_chartqa_pro_reasoning_samplingq3_rawpred/judge_summary.json) |
| MathVista Mini | ZS | [base](../eval/outputs/qwen3_vl_2b_mathvista_testmini_qwen3_thinking_zs_rawpred/judge_summary.json) | [rl](../eval/outputs/trace_qwen3_2b_answer_51k_solve_0125_0750_uniform_4kresp_step500_mathvista_testmini_qwen3_thinking_zs_rawpred/judge_summary.json) |
| MathVista Mini | Reasoning | [base](../eval/outputs/qwen3_vl_2b_mathvista_testmini_reasoning_samplingq3_rawpred/judge_summary.json) | [rl](../eval/outputs/trace_qwen3_2b_answer_51k_solve_0125_0750_uniform_4kresp_step500_mathvista_testmini_reasoning_samplingq3_rawpred/judge_summary.json) |
| MathVision TestMini | ZS | [base](../eval/outputs/qwen3_vl_2b_mathvision_testmini_qwen3_thinking_zs_rawpred/judge_summary.json) | [rl](../eval/outputs/trace_qwen3_2b_answer_51k_solve_0125_0750_uniform_4kresp_step500_mathvision_testmini_qwen3_thinking_zs_rawpred/judge_summary.json) |
| MathVision TestMini | Reasoning | [base](../eval/outputs/qwen3_vl_2b_mathvision_testmini_reasoning_samplingq3_rawpred/judge_summary.json) | [rl](../eval/outputs/trace_qwen3_2b_answer_51k_solve_0125_0750_uniform_4kresp_step500_mathvision_testmini_reasoning_samplingq3_rawpred/judge_summary.json) |
| BLINK | ZS | [base](../eval/outputs/qwen3_vl_2b_blink_qwen3_thinking_zs_rawpred/judge_summary.json) | [rl](../eval/outputs/trace_qwen3_2b_answer_51k_solve_0125_0750_uniform_4kresp_step500_blink_qwen3_thinking_zs_rawpred/judge_summary.json) |
| BLINK | Reasoning | [base](../eval/outputs/qwen3_vl_2b_blink_reasoning_samplingq3_rawpred/judge_summary.json) | [rl](../eval/outputs/trace_qwen3_2b_answer_51k_solve_0125_0750_uniform_4kresp_step500_blink_reasoning_samplingq3_rawpred/judge_summary.json) |
| EmbSpatial | ZS | [base](../eval/outputs/qwen3_vl_2b_embspatial_qwen3_thinking_zs_rawpred/judge_summary.json) | [rl](../eval/outputs/trace_qwen3_2b_answer_51k_solve_0125_0750_uniform_4kresp_step500_embspatial_qwen3_thinking_zs_rawpred/judge_summary.json) |
| EmbSpatial | Reasoning | [base](../eval/outputs/qwen3_vl_2b_embspatial_reasoning_samplingq3_rawpred/judge_summary.json) | [rl](../eval/outputs/trace_qwen3_2b_answer_51k_solve_0125_0750_uniform_4kresp_step500_embspatial_reasoning_samplingq3_rawpred/judge_summary.json) |
| CountQA | ZS | [base](../eval/outputs/qwen3_vl_2b_countqa_qwen3_thinking_zs/20260422_165233_results.json) | [rl](../eval/outputs/trace_qwen3_2b_answer_51k_solve_0125_0750_uniform_4kresp_step500_countqa_qwen3_thinking_zs/20260422_172323_results.json) |
| CountQA | Reasoning | [base](../eval/outputs/qwen3_vl_2b_countqa_reasoning_samplingq3/20260422_170255_results.json) | [rl](../eval/outputs/trace_qwen3_2b_answer_51k_solve_0125_0750_uniform_4kresp_step500_countqa_reasoning_samplingq3/20260422_173337_results.json) |
| GameQALite | ZS | [base](../eval/outputs/qwen3_vl_2b_game_qa_lite_qwen3_thinking_zs/20260422_181213_results.json) | [rl](../eval/outputs/trace_qwen3_2b_answer_51k_solve_0125_0750_uniform_4kresp_step500_game_qa_lite_qwen3_thinking_zs/20260422_184834_results.json) |
| VStarBench | ZS | [base](../eval/outputs/qwen3_vl_2b_vstar_bench_qwen3_thinking_zs/20260422_191818_results.json) | [rl](../eval/outputs/trace_qwen3_2b_answer_51k_solve_0125_0750_uniform_4kresp_step500_vstar_bench_qwen3_thinking_zs/20260422_192303_results.json) |
| VStarBench | Reasoning | [base](../eval/outputs/qwen3_vl_2b_vstar_bench_reasoning_samplingq3/20260422_192041_results.json) | [rl](../eval/outputs/trace_qwen3_2b_answer_51k_solve_0125_0750_uniform_4kresp_step500_vstar_bench_reasoning_samplingq3/20260422_192526_results.json) |
| MMMU-ProVis | ZS | [base](../eval/outputs/qwen3_vl_2b_mmmu_pro_vision_qwen3_thinking_zs/20260422_204238_results.json) | [rl](../eval/outputs/trace_qwen3_2b_answer_51k_solve_0125_0750_uniform_4kresp_step500_mmmu_pro_vision_qwen3_thinking_zs/20260422_212449_results.json) |
| ERQA | ZS | [base](../eval/outputs/qwen3_vl_2b_erqa_qwen3_thinking_zs_rawpred/judge_summary.json) | [rl](../eval/outputs/trace_qwen3_2b_answer_51k_solve_0125_0750_uniform_4kresp_step500_erqa_qwen3_thinking_zs_rawpred/judge_summary.json) |
| ERQA | Reasoning | [base](../eval/outputs/qwen3_vl_2b_erqa_reasoning_samplingq3_rawpred/judge_summary.json) | [rl](../eval/outputs/trace_qwen3_2b_answer_51k_solve_0125_0750_uniform_4kresp_step500_erqa_reasoning_samplingq3_rawpred/judge_summary.json) |

## Notes

- `CountQA` evaluates `1528` QA pairs after task expansion, even though the underlying HF `test` split has `1001` source examples.
- `GameQALite` currently has only the zero-shot result here. The reasoning run was not completed because it is very slow on the single H100 with the upstream long-generation setup.
- `MMMU-ProVis` currently has only the zero-shot result here.
- Judge-backed rows above use the local batched Qwen3-32B extraction/scoring flow already added under `eval/scripts/`.
- The `Average` row is a simple unweighted mean across the `18` listed benchmark/prompt rows.

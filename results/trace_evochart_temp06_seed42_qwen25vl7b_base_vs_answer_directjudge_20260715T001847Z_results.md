# EvoChart Temp0.6 Seed42 Direct-Judge Results

Canonical setup: raw `EvoChart` prompt, temperature 0.6, top_p 1.0, top_k -1, max_tokens 4096, seed 42, Qwen3-32B direct answer judge.

Run root: `/dev/shm/trace_rlvr/trace_evochart_temp06_seed42_qwen25vl7b_base_vs_answer_directjudge_20260715T001847Z/runs`

Benchmark root: `/dev/shm/trace_rlvr/trace_evochart_temp06_seed42_qwen25vl7b_base_vs_answer_directjudge_20260715T001847Z_score/benchmark`

| model                                                                 |   score |   rows |   correct |   mean_response_tokens |   median_response_tokens |   max_response_tokens |   length_cap_fraction |   judge_json_rows |   judge_invalid_json_rows |
|:----------------------------------------------------------------------|--------:|-------:|----------:|-----------------------:|-------------------------:|----------------------:|----------------------:|------------------:|--------------------------:|
| qwen25vl7b-base                                                       |   59.52 |   1250 |       744 |                  38.31 |                    29.00 |                   616 |                  0.00 |              1250 |                         0 |
| trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500                   |   66.00 |   1250 |       825 |                  96.24 |                    37.00 |                  2890 |                  0.00 |              1250 |                         0 |
| trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500 - qwen25vl7b-base |    6.48 |        |        81 |                  57.93 |                     8.00 |                  2274 |                  0.00 |                   |                           |

## Artifacts

- `qwen25vl7b-base` score: `/dev/shm/trace_rlvr/trace_evochart_temp06_seed42_qwen25vl7b_base_vs_answer_directjudge_20260715T001847Z_score/benchmark/evochart/qwen25vl7b-base/vlmevalkit_defaults_qwen32b_judge/scores.json`
- `qwen25vl7b-base` predictions: `/dev/shm/trace_rlvr/trace_evochart_temp06_seed42_qwen25vl7b_base_vs_answer_directjudge_20260715T001847Z/runs/evochart/qwen25vl7b-base/vlmevalkit_defaults_qwen32b_judge/EvoChart_predictions.xlsx`
- `qwen25vl7b-base` judged table: `/dev/shm/trace_rlvr/trace_evochart_temp06_seed42_qwen25vl7b_base_vs_answer_directjudge_20260715T001847Z/runs/evochart/qwen25vl7b-base/vlmevalkit_defaults_qwen32b_judge/EvoChart_judged_qwen3_32b.xlsx`
- `trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500` score: `/dev/shm/trace_rlvr/trace_evochart_temp06_seed42_qwen25vl7b_base_vs_answer_directjudge_20260715T001847Z_score/benchmark/evochart/trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500/vlmevalkit_defaults_qwen32b_judge/scores.json`
- `trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500` predictions: `/dev/shm/trace_rlvr/trace_evochart_temp06_seed42_qwen25vl7b_base_vs_answer_directjudge_20260715T001847Z/runs/evochart/trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500/vlmevalkit_defaults_qwen32b_judge/EvoChart_predictions.xlsx`
- `trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500` judged table: `/dev/shm/trace_rlvr/trace_evochart_temp06_seed42_qwen25vl7b_base_vs_answer_directjudge_20260715T001847Z/runs/evochart/trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500/vlmevalkit_defaults_qwen32b_judge/EvoChart_judged_qwen3_32b.xlsx`

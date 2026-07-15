# MMESCI_EN Temp0.6 Seed42 Results

Models: Qwen2.5-VL-7B base and TRACE answer-GRPO step500.

Generation: temperature=0.6, top_p=1.0, top_k=-1, max_tokens=4096, seed=42.

Scoring: Qwen3-32B judge with VLMEvalKit/MMESCI ShortQA prompt, judge temperature=0.0.

| model                       |   rows |   accuracy |   delta_vs_base_pp |   mean_generated_tokens |
|:----------------------------|-------:|-----------:|-------------------:|------------------------:|
| Qwen2.5-VL-7B-Instruct base |   1019 |      14.33 |               0    |                   422.6 |
| TRACE answer GRPO step500   |   1019 |      14.03 |              -0.29 |                   867.9 |

Run root: `/dev/shm/trace_rlvr/trace_mmesci_en_temp06_seed42_qwen25vl7b_base_vs_answer_20260715T005758Z/runs`

Benchmark root: `/dev/shm/trace_rlvr/trace_mmesci_en_temp06_seed42_qwen25vl7b_base_vs_answer_20260715T005758Z/benchmark`

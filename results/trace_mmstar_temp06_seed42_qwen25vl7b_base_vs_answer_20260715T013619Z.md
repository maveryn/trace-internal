# MMStar Qwen2.5-VL-7B Temp0.6 Seed42

Run tag: `trace_mmstar_temp06_seed42_qwen25vl7b_base_vs_answer_20260715T013619Z`

Generation used temperature 0.6, top_p 1.0, top_k -1, max_tokens 4096, seed 42. Official scoring is VLMEvalKit exact matching. The fallback-corrected score only replaces rows where VLMEvalKit logged `Failed in Prefetch` with the local explicit-MCQ option parser used for ScienceQA-style verbose answers.

| model                          | slug                                                |   rows |   official_exact_accuracy |   official_prefetch_parse_success_pct |   official_prefetch_failures |   fallback_parse_success_all_pct |   fallback_recovered_correct_from_official_failures |   fallback_unparsed_official_failures |   fallback_corrected_accuracy |   fallback_all_rows_accuracy |   mean_output_tokens |   median_output_tokens |   max_output_tokens |
|:-------------------------------|:----------------------------------------------------|-------:|--------------------------:|--------------------------------------:|-----------------------------:|---------------------------------:|----------------------------------------------------:|--------------------------------------:|------------------------------:|-----------------------------:|---------------------:|-----------------------:|--------------------:|
| Qwen2.5-VL-7B base             | qwen25vl7b-base                                     |   1500 |                     58.67 |                                 91.20 |                          132 |                            97.53 |                                                  55 |                                    30 |                         62.33 |                        61.93 |                46.48 |                   5.00 |             4096.00 |
| TRACE answer GRPO step500      | trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500 |   1500 |                     52.20 |                                 75.20 |                          372 |                            95.00 |                                                 171 |                                    44 |                         63.60 |                        62.20 |               140.90 |                   9.50 |             4096.00 |
| TRACE answer GRPO - base delta |                                                     |        |                     -6.47 |                                -16.00 |                          240 |                            -2.53 |                                                 116 |                                    14 |                          1.27 |                         0.27 |                94.43 |                   4.50 |                0.00 |


## Interpretation

- Official exact matching undercounts verbose answers on MMStar, especially for the answer-GRPO model.

- Using fallback extraction only on official prefetch failures changes the result from base better by 6.47 pp to answer-GRPO better by 1.27 pp.

- If we include MMStar in final eval, we should add a benchmark-specific local MCQ fallback scorer instead of relying on raw exact matching.

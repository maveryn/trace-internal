# Qwen2.5-VL-3B Base / Answer / Annotation Consolidated Results

Unique benchmarks: 36

Models: base, answer-GRPO step500, annotation-GRPO additive 0.50 step500.

## Averages

| decoding   |   benchmarks |   base_score |   answer_grpo_step500_score |   annotation_additive_0p50_step500_score |   delta_answer_grpo_minus_base |   delta_annotation_minus_base |   delta_annotation_minus_answer_grpo |
|:-----------|-------------:|-------------:|----------------------------:|-----------------------------------------:|-------------------------------:|------------------------------:|-------------------------------------:|
| greedy     |           36 |      33.8272 |                     34.7982 |                                  34.8717 |                         0.9710 |                        1.0445 |                               0.0735 |
| temp0.6    |           36 |      30.1900 |                     33.1038 |                                  32.9413 |                         2.9139 |                        2.7514 |                              -0.1625 |

## Files

- CSV: `results/qwen25vl3b_base_answer_annotation_all36_greedy_temp06_results.csv`
- Excel: `results/qwen25vl3b_base_answer_annotation_all36_greedy_temp06_results.xlsx`

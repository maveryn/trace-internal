# Qwen2.5-VL-7B High-Risk Benchmark LLM-Extracted Scores

This compares the original 1000-sample 7B benchmark scores against a Qwen3-32B LLM extraction / judge pass for the six direct-scored benchmarks most likely to be affected by answer-format parsing.

## Setup

- Extraction queue: `trace_candidate6_highrisk_1000_7b_base_vs_step500_qwen32b_api_extract_20260713T004000Z`
- Judge/extractor: `Qwen/Qwen3-32B`, served as OpenAI-compatible endpoints on local ports `18100-18107`.
- Evaluated models: `Qwen/Qwen2.5-VL-7B-Instruct` and `/dev/shm/trace_rlvr/merged_hf/trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500`.
- New scoring uses LLM extraction for option/value/short-answer normalization; `Physics` uses binary LLM judging; `VisionGraph-Q3` extracts the short answer and then runs the VisionGraph verifier.

## Summary

| benchmark      | prompt_run             |    N |   Old_Base |   New_Base_LLMExtract |   Old_Step500 |   New_Step500_LLMExtract |   Old_Delta_Step500MinusBase |   New_Delta_Step500MinusBase |   Delta_Shift |   Base_response_mean |   Step500_response_mean |
|:---------------|:-----------------------|-----:|-----------:|----------------------:|--------------:|-------------------------:|-----------------------------:|-----------------------------:|--------------:|---------------------:|------------------------:|
| PuzzleVQA      | vlmevalkit_reasoning   | 1000 |      45.2  |                 46.5  |         43    |                    53.5  |                        -2.2  |                         7    |          9.2  |               244.23 |                  364.14 |
| TreeBench      | vlmevalkit_defaults    |  405 |      38.02 |                 40.49 |         37.28 |                    42.96 |                        -0.74 |                         2.47 |          3.21 |                17.96 |                   34.01 |
| PhyX mini MC   | vlmevalkit_defaults    | 1000 |      40.3  |                 39.5  |         49.8  |                    49    |                         9.5  |                         9.5  |          0    |               163.34 |                  722.79 |
| Physics        | vlmevalkit_reasoning   | 1000 |      14.1  |                 24.7  |         15.4  |                    26.9  |                         1.3  |                         2.2  |          0.9  |               720.43 |                  897.15 |
| MMMU-ProVis    | vlmevalkit_cot_max2048 | 1000 |      38.2  |                 38.1  |         34.2  |                    39.4  |                        -4    |                         1.3  |          5.3  |               440.48 |                  586.52 |
| VisionGraph-Q3 | vlmevalkit_q3          | 1000 |      17.78 |                 14.93 |         17.46 |                    13.69 |                        -0.32 |                        -1.24 |         -0.92 |               395.4  |                  688.68 |
| Average        | simple mean            | 5405 |      32.27 |                 34.04 |         32.86 |                    37.58 |                         0.59 |                         3.54 |          2.95 |               330.3  |                  548.88 |

## Notes

- The simple average over these six benchmarks moves from an old trained-vs-base delta of `+0.59` to a new LLM-extracted delta of `+3.54`.
- The largest trained-vs-base corrections are on `PuzzleVQA`, `MMMU-ProVis`, and `TreeBench`, where direct extraction previously made the step500 model look worse than base.
- `VisionGraph-Q3` remains slightly lower for step500 than base after LLM extraction; its macro score is reported as the headline score, and micro scores are included in the CSV/XLSX.

## Artifacts

- CSV: `results/qwen25vl7b_candidate6_highrisk_1000_llm_extracted_comparison.csv`
- Excel: `results/qwen25vl7b_candidate6_highrisk_1000_llm_extracted_comparison.xlsx`
- Raw score root: `benchmark/llm_extracted/trace_candidate6_highrisk_1000_7b_base_vs_step500_qwen32b_api_extract_20260713T004000Z/scores`

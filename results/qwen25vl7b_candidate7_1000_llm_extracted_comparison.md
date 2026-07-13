# Qwen2.5-VL-7B 1000-Sample LLM-Extracted Score Comparison

This compares the existing benchmark scores against a secondary Qwen3-32B LLM-extraction pass for seven benchmarks where verbose responses can break direct/exact parsers.

- Models: `Qwen/Qwen2.5-VL-7B-Instruct` and `/dev/shm/trace_rlvr/merged_hf/trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500`
- Judge/extractor: `Qwen/Qwen3-32B`, loaded once per GPU across eight worker processes
- Scoring: LLM extraction only, then deterministic benchmark comparison. ChartQAPro uses the existing relaxed ChartQAPro scorer on the extracted short answer.
- Game-QA-Lite is mixed-format; the corrected extractor infers per-row answer type: option, number, or short answer.

## Scores

| benchmark                  | prompt_run              |    N |   Old_Base |   New_Base_LLMExtract |   Base_NewMinusOld |   Old_Step500 |   New_Step500_LLMExtract |   Step500_NewMinusOld |   Old_Delta_Step500MinusBase |   New_Delta_Step500MinusBase |   Delta_Shift |
|:---------------------------|:------------------------|-----:|-----------:|----------------------:|-------------------:|--------------:|-------------------------:|----------------------:|-----------------------------:|-----------------------------:|--------------:|
| Blink                      | vlmevalkit_defaults     | 1000 |      52.4  |                 53.8  |               1.4  |         33.3  |                    57.3  |                 24    |                       -19.1  |                         3.5  |         22.6  |
| ChartQAPro                 | vlmevalkit_faithful_cot | 1000 |      32.5  |                 46.72 |              14.22 |         17.81 |                    50.02 |                 32.21 |                       -14.69 |                         3.3  |         17.99 |
| Game-QA-Lite               | vlmevalkit_cot_boxed    | 1000 |      23.3  |                 24    |               0.7  |         29.6  |                    27.1  |                 -2.5  |                         6.3  |                         3.1  |         -3.2  |
| CountBenchQA               | vlmevalkit_defaults     |  487 |      86.24 |                 86.24 |               0    |         86.65 |                    86.65 |                  0    |                         0.41 |                         0.41 |          0    |
| ERQA                       | vlmevalkit_defaults     |  400 |      40    |                 41    |               1    |         41.25 |                    41.5  |                  0.25 |                         1.25 |                         0.5  |         -0.75 |
| VStarBench                 | vlmevalkit_defaults     |  191 |      76.44 |                 76.44 |               0    |         72.25 |                    73.3  |                  1.05 |                        -4.19 |                        -3.14 |          1.05 |
| CV-Bench 3D                | vlmevalkit_defaults     | 1000 |      71.9  |                 74.5  |               2.6  |         68.6  |                    80    |                 11.4  |                        -3.3  |                         5.5  |          8.8  |
| Average (unweighted)       |                         | 5078 |      54.68 |                 57.53 |               2.85 |         49.92 |                    59.41 |                  9.49 |                        -4.76 |                         1.88 |          6.64 |
| Average (weighted by rows) |                         | 5078 |      49.76 |                 53.57 |               3.8  |         43.68 |                    56.56 |                 12.88 |                        -6.08 |                         2.99 |          9.08 |

## Takeaways

- BLINK changes from a large apparent regression under direct parsing (`-19.10`) to an LLM-extracted gain (`+3.50`).
- ChartQAPro changes from a large apparent regression (`-14.69`) to an LLM-extracted gain (`+3.30`), so the previous number was mostly extraction-sensitive.
- CV-Bench 3D also flips from `-3.30` to `+5.50` after extraction.
- Game-QA-Lite remains positive, but the LLM-extracted delta (`+3.10`) is smaller than the old boxed/direct delta (`+6.30`).
- CountBenchQA and ERQA are nearly unchanged, which is expected because their responses were already short.
- VStarBench remains a small regression under both scoring styles.

## Artifacts

- CSV: `results/qwen25vl7b_candidate7_1000_llm_extracted_comparison.csv`
- Excel: `results/qwen25vl7b_candidate7_1000_llm_extracted_comparison.xlsx`
- Primary extraction queue: `benchmark/llm_extracted/trace_candidate7_1000_7b_base_vs_step500_qwen32b_extract_20260713T001500Z`
- Corrected Game-QA extraction queue: `benchmark/llm_extracted/trace_gameqa_1000_7b_base_vs_step500_qwen32b_extract_mixed_v2_20260713T002500Z`

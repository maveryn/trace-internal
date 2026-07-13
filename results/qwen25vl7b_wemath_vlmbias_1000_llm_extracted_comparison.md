# Qwen2.5-VL-7B WeMath/VLMBias LLM-Extracted Scores

This reruns `WeMath` and `VLMBias` with Qwen3-32B used as an answer extractor only, followed by deterministic exact scoring.

## Setup

- Extraction queue: `trace_wemath_vlmbias_1000_7b_base_vs_step500_qwen32b_api_extract_braced_20260713T010321Z`
- Judge/extractor: `Qwen/Qwen3-32B`, served on local OpenAI-compatible ports `18100-18107`.
- `WeMath`: Qwen3 extracts the final option letter; exact option scoring.
- `VLMBias`: Qwen3 extracts the final braced answer value; exact normalized scoring.

## Summary

| benchmark   | prompt_run                   |    N |   Old_Base |   New_Base_LLMExtract |   Old_Step500 |   New_Step500_LLMExtract |   Old_Delta_Step500MinusBase |   New_Delta_Step500MinusBase |   Delta_Shift |
|:------------|:-----------------------------|-----:|-----------:|----------------------:|--------------:|-------------------------:|-----------------------------:|-----------------------------:|--------------:|
| WeMath      | vlmevalkit_cot_qwen32b_judge | 1000 |      62.3  |                 62.5  |          66.9 |                    68    |                         4.6  |                          5.5 |          0.9  |
| VLMBias     | vlmevalkit_defaults          | 1000 |      21.2  |                 21.2  |          23.7 |                    23.7  |                         2.5  |                          2.5 |          0    |
| Average     | simple mean                  | 2000 |      41.75 |                 41.85 |          45.3 |                    45.85 |                         3.55 |                          4   |          0.45 |

## Notes

- `WeMath` changes from `+4.60` trained-vs-base delta to `+5.50` after Qwen3 extraction.
- `VLMBias` is unchanged overall after correct braced-answer extraction: base `21.20`, step500 `23.70`.
- A first yes/no-only VLMBias pass was discarded because VLMBias also includes numeric counting categories; the committed result uses the corrected braced-answer extractor.

## Artifacts

- CSV: `results/qwen25vl7b_wemath_vlmbias_1000_llm_extracted_comparison.csv`
- Excel: `results/qwen25vl7b_wemath_vlmbias_1000_llm_extracted_comparison.xlsx`
- Raw score root: `benchmark/llm_extracted/trace_wemath_vlmbias_1000_7b_base_vs_step500_qwen32b_api_extract_braced_20260713T010321Z/scores`

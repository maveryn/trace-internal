# TRACE OCRBench-v2 MINI / ScreenSpot-v2 3B Base / Answer / Annotation Results

Subset manifest root: `/home/shadeform/LMUData`

Scores are canonical VLMEvalKit grounding metrics normalized to percentages.

## Greedy, max_tokens=4096

| Benchmark | Rows | Base | Answer GRPO 500 | Annotation GRPO 500 | Answer - Base | Annotation - Base | Annotation - Answer |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| OCRBench v2 MINI | 2500 | 49.26 | 49.19 | 49.37 | -0.07 | 0.11 | 0.17 |
| ScreenSpot v2 | 1272 | 77.12 | 67.14 | 77.67 | -9.98 | 0.55 | 10.53 |
| Average |  | 63.19 | 58.17 | 63.52 | -5.03 | 0.33 | 5.35 |

## Temperature 0.6, max_tokens=4096

| Benchmark | Rows | Base | Answer GRPO 500 | Annotation GRPO 500 | Answer - Base | Annotation - Base | Annotation - Answer |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| OCRBench v2 MINI | 2500 | 45.35 | 47.91 | 47.75 | 2.56 | 2.41 | -0.16 |
| ScreenSpot v2 | 1272 | 51.18 | 56.60 | 65.02 | 5.42 | 13.84 | 8.41 |
| Average |  | 48.26 | 52.26 | 56.38 | 3.99 | 8.12 | 4.13 |

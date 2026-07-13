# TRACE Grounding 3B Base / Answer / Annotation Results

Subset manifest root: `/home/shadeform/trace/benchmark/subsets/trace_grounding`

Scores are canonical VLMEvalKit grounding metrics normalized to percentages.

## Greedy, max_tokens=4096

| Benchmark | Rows | Base | Answer GRPO 500 | Annotation GRPO 500 | Answer - Base | Annotation - Base | Annotation - Answer |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| RefSpatial wo unseen | 200 | 0.00 | 0.50 | 0.50 | 0.50 | 0.50 | 0.00 |
| OSWorld-G | 564 | 3.72 | 3.90 | 1.95 | 0.18 | -1.77 | -1.95 |
| RefCOCO | 1000 | 21.30 | 27.20 | 16.30 | 5.90 | -5.00 | -10.90 |
| GroundingME | 1005 | 11.14 | 11.34 | 11.94 | 0.20 | 0.80 | 0.60 |
| TDBenchGrounding rot0 | 200 | 2.50 | 1.50 | 0.50 | -1.00 | -2.00 | -1.00 |
| Average |  | 7.73 | 8.89 | 6.24 | 1.16 | -1.50 | -2.65 |

## Temperature 0.6, max_tokens=4096

| Benchmark | Rows | Base | Answer GRPO 500 | Annotation GRPO 500 | Answer - Base | Annotation - Base | Annotation - Answer |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| RefSpatial wo unseen | 200 | 0.00 | 0.00 | 0.50 | 0.00 | 0.50 | 0.50 |
| OSWorld-G | 564 | 1.95 | 2.30 | 2.30 | 0.35 | 0.35 | 0.00 |
| RefCOCO | 1000 | 5.20 | 9.90 | 6.50 | 4.70 | 1.30 | -3.40 |
| GroundingME | 1005 | 9.75 | 10.55 | 11.54 | 0.80 | 1.79 | 1.00 |
| TDBenchGrounding rot0 | 200 | 1.50 | 3.00 | 0.50 | 1.50 | -1.00 | -2.50 |
| Average |  | 3.68 | 5.15 | 4.27 | 1.47 | 0.59 | -0.88 |

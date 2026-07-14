# TRACE Final20 Evaluation Setup

This document records the evaluation setup used for the final 20-benchmark comparison workbooks in `results/`, especially:

- `results/trace_final20_temp06_3b7b_model_results.xlsx`
- `results/trace_final20_temp06_seed42_*_results.md`
- `results/trace_final20_temp06_seed42_*_results.xlsx`

The canonical runner for single-model final20 evaluation is:

```bash
scripts/run_trace_final20_temp06_seed42_single_model.sh
```

## Benchmark Families

| Family | Benchmarks |
| --- | --- |
| Charts / Tables / Figures | ChartMuseum, ChartQAPro, CharXivReason, TableVQABench |
| Math / Science | MathVision, MathVista, WeMath, Physics, PhyX mini MC, MMMU-ProVis |
| Spatial / Perception / Grounding | ScreenSpot, SpatialVizBench COT, CV-Bench 3D, TreeBench, CountBenchQA, Blink |
| Puzzle / Abstract Reasoning | Game-QA-Lite, PuzzleVQA, VisualPuzzles, LogicVista |

## Prompt Policy

All compared models use the same prompt path for a given benchmark.

There is not one universal prompt across all 20 benchmarks. Each benchmark uses its configured VLMEvalKit or repo-local prompt builder, recorded as `prompt_run` in the result workbooks. Generation requests are sent as OpenAI-compatible chat completions with a single `user` message containing the benchmark text plus image content. No additional TRACE training system prompt is added during these external benchmark evaluations.

Implementation details:

- `scripts/run_external_benchmark_generation_api_queue.py` builds the chat messages.
- Most benchmarks call the local VLMEvalKit runner through `build_prompt_for_runner`.
- `ChartMuseum` is a local exception that sends the dataset image and question directly.
- The same generated row set, prompt path, decoding config, and scorer path are used across all models being compared.

## Decoding Config

The final20 comparison workbook uses the temperature-0.6 setting:

| Parameter | Value |
| --- | --- |
| `temperature` | `0.6` |
| `top_p` | `1.0` |
| `top_k` | `-1` |
| `presence_penalty` | `0.0` |
| `repetition_penalty` | `1.0` |
| `max_tokens` | `4096` |
| `seed` | `42` |

Generation serving defaults:

| Parameter | Value |
| --- | --- |
| vLLM endpoints | 8 OpenAI-compatible servers |
| GPU mapping | one endpoint per GPU, `0..7` |
| generation ports | `18000..18007` |
| `gpu_memory_utilization` | `0.90` |
| `max_model_len` | `32768` |
| `max_num_seqs` | `256` |
| `max_num_batched_tokens` | `32768` |
| client parallelism | `32` requests per endpoint |

## Judge / Extraction Config

The judge/extractor model is:

```text
Qwen/Qwen3-32B
```

It is served as `qwen3-32b-judge` through local OpenAI-compatible vLLM endpoints.

| Parameter | Value |
| --- | --- |
| judge ports | `18100..18107` |
| `gpu_memory_utilization` | `0.90` |
| `max_model_len` | `8192` |
| `max_num_seqs` | `128` |
| `max_num_batched_tokens` | `32768` |
| `judge_max_tokens` | `64` |
| API parallelism | `16` |
| API batch size | `128` |
| batches per endpoint | `2` |

The judge is used in two ways:

- For some benchmarks, the benchmark scorer directly uses the judge-backed evaluator path.
- For other benchmarks, Qwen3-32B extracts a normalized final answer first, and the repo then applies the benchmark-specific deterministic scorer in the finalization step.

## Benchmark Table

| Family | Benchmark | Key | Dataset alias | Prompt / run | Rows | Score path |
| --- | --- | --- | --- | --- | ---: | --- |
| Charts / Tables / Figures | ChartMuseum | `chartmuseum` | `ChartMuseum_test` | `vlmevalkit_defaults_qwen32b_judge_test` | 1000 | official/direct judge-backed |
| Charts / Tables / Figures | ChartQAPro | `chartqapro` | `ChartQAPro_CoT` | `vlmevalkit_faithful_cot` | 1948 | Qwen3 extraction + benchmark scorer |
| Charts / Tables / Figures | CharXivReason | `charxivreason` | `CharXiv_reasoning_val` | `vlmevalkit_defaults_qwen32b_judge` | 1000 | official/direct judge-backed |
| Charts / Tables / Figures | TableVQABench | `tablevqabench` | `TableVQABench` | `vlmevalkit_defaults` | 1500 | official/direct scorer |
| Math / Science | MathVision | `mathvision` | `MathVision` | `vlmevalkit_defaults_qwen32b_judge` | 3040 | official/direct judge-backed |
| Math / Science | MathVista | `mathvista` | `MathVista_MINI` | `vlmevalkit_defaults_qwen32b_judge` | 1000 | official/direct judge-backed |
| Math / Science | WeMath | `wemath` | `WeMath_COT` | `vlmevalkit_cot_qwen32b_judge` | 1740 | Qwen3 extraction + benchmark scorer |
| Math / Science | Physics | `physics` | `Physics` | `vlmevalkit_reasoning` | 1297 | Qwen3 extraction + benchmark scorer |
| Math / Science | PhyX mini MC | `phyx_mini_mc` | `PhyX_mini_MC` | `vlmevalkit_defaults` | 1000 | Qwen3 extraction + benchmark scorer |
| Math / Science | MMMU-ProVis | `mmmu_pro_vision` | `MMMU_Pro_V_COT` | `vlmevalkit_cot_max2048` | 1730 | Qwen3 extraction + benchmark scorer |
| Spatial / Perception / Grounding | ScreenSpot | `screenspot` | `ScreenSpot` | `vlmevalkit_defaults_sample200` | 1272 | official/direct grounding scorer |
| Spatial / Perception / Grounding | SpatialVizBench COT | `spatialvizbench_cot` | `SpatialVizBench_CoT` | `vlmevalkit_cot` | 1180 | Qwen3 extraction + benchmark scorer |
| Spatial / Perception / Grounding | CV-Bench 3D | `cvbench_3d` | `CV-Bench-3D` | `vlmevalkit_defaults` | 1200 | Qwen3 extraction + benchmark scorer |
| Spatial / Perception / Grounding | TreeBench | `treebench` | `TreeBench` | `vlmevalkit_defaults` | 405 | Qwen3 extraction + benchmark scorer |
| Spatial / Perception / Grounding | CountBenchQA | `countbenchqa` | `CountBenchQA` | `vlmevalkit_defaults` | 487 | Qwen3 extraction + benchmark scorer |
| Spatial / Perception / Grounding | Blink | `blink` | `BLINK` | `vlmevalkit_defaults` | 1901 | Qwen3 extraction + benchmark scorer |
| Puzzle / Abstract Reasoning | Game-QA-Lite | `game_qa_lite` | `Game-QA-Lite` | `vlmevalkit_cot_boxed` | 2633 | Qwen3 extraction + benchmark scorer |
| Puzzle / Abstract Reasoning | PuzzleVQA | `puzzlevqa` | `PuzzleVQA` | `vlmevalkit_reasoning` | 2000 | Qwen3 extraction + benchmark scorer |
| Puzzle / Abstract Reasoning | VisualPuzzles | `visualpuzzles` | `VisualPuzzles` | `vlmevalkit_reasoning` | 1168 | Qwen3 extraction + benchmark scorer |
| Puzzle / Abstract Reasoning | LogicVista | `logicvista` | `LogicVista` | `vlmevalkit_defaults_qwen32b_judge` | 447 | official/direct judge-backed |

## Subsets / Dataset Sources

The final20 runner combines two sources:

- `CANDIDATE_BENCHMARKS`: run with `--run-set full` and `--subset-root benchmark/subsets/trace_candidate24_full`.
- `EXTRA_BENCHMARKS`: `SpatialVizBench COT`, `TableVQABench`, and `VisualPuzzles`, run as full VLMEvalKit datasets through `--run-set trace_candidate37_200`.

The result summaries label this as:

```text
final20 full eval; candidate benchmarks use trace_candidate24_full subset manifests; SpatialVizBench/TableVQABench/VisualPuzzles use full VLMEvalKit datasets
```

## Result Normalization

Scores are normalized to percentage-style accuracy where the evaluator reports an accuracy-like metric. The summarizer emits one score per benchmark and one unweighted `Average` row across the 20 benchmark scores. It does not emit an `Average excl. ScreenSpot` row for final20 results.

Special cases are handled by the summarizer/eval scripts:

- `ScreenSpot`: official grounding-style accuracy from the benchmark scorer.
- `TableVQABench`: macro mean over reported split `average_scores`.
- Qwen3-extracted benchmarks: answer extraction is batched through Qwen3-32B, then finalized with benchmark-specific scoring.

## Reproduction Template

Example:

```bash
MODEL_PATH=/path/or/hf/repo \
MODEL_SLUG=my-model-slug \
bash scripts/run_trace_final20_temp06_seed42_single_model.sh
```

The runner writes:

- generation outputs under `/dev/shm/trace_rlvr/<RUN_TAG>/runs`
- score outputs under `/dev/shm/trace_rlvr/<RUN_TAG>_score`
- logs under `logs/benchmark/<RUN_TAG>`
- markdown and Excel summaries under `results/<RUN_TAG>_results.{md,xlsx}`


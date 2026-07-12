# TRACE External Benchmark Evaluation Plan

This document tracks the paper-facing evaluation protocol for Qwen3-VL-4B-Instruct and follow-up trained checkpoints.

## Execution Policy

- Primary harness: VLMEvalKit.
- Generation backend: vLLM only, with FlashAttention. Do not use Hugging Face generation.
- Queue execution: run generation and scoring in separate phases. Generation workers keep one VLM loaded per GPU and claim one dataset at a time; local-judge scoring workers keep one `Qwen/Qwen3-32B` judge loaded per GPU and run only after generation artifacts exist.
- GPU assignment:
  - base `Qwen/Qwen3-VL-4B-Instruct`: GPUs `6,7`
  - TRACE alpha0 ablation: GPUs `0,1`
  - TRACE alpha0.5 ablation: GPUs `2,3`
  - TRACE alpha1 ablation: GPUs `4,5`
- Default model setup: VLMEvalKit's `Qwen3-VL-4B-Instruct` generation defaults:
  - `temperature=0.7`
  - `top_p=0.8`
  - `top_k=20`
  - `presence_penalty=1.5`
  - `repetition_penalty=1.0`
  - `max_new_tokens=16384`
- Judge policy: use direct/exact official evaluators when available. If a dataset requires an LLM judge, use local `Qwen/Qwen3-32B` with thinking disabled.
- Artifact policy:
  - Score summaries live under `benchmark/<dataset>/<model>/<run_name>/`.
  - Full predictions and run artifacts live under `runs/<dataset>/<model>/<run_name>/`.
- Sanity policy: if a score is more than 5 absolute points away from the expected rough value in `/home/jovyan/work/benchmarks.txt`, verify dataset alias, split, sample count, prompt, evaluator, generation config, output cap rate, parser, and judge behavior before accepting the result.

## Queue Commands

```bash
bash scripts/export_trace_ablation_hf_checkpoints.sh
CUDA_VISIBLE_DEVICES="" python scripts/materialize_vlmeval_datasets.py \
  --aliases ScreenSpot_Pro_Development ScreenSpot_Pro_Creative ScreenSpot_Pro_CAD \
  ScreenSpot_Pro_Scientific ScreenSpot_Pro_Office ScreenSpot_Pro_OS
bash scripts/run_external_benchmark_generation_pool.sh all
bash scripts/run_external_benchmark_score_pool.sh all
```

For base-only or ablation-only execution, pass `base` or `ablations` to the generation/scoring pool scripts.
The scoring pool refreshes `benchmark/results.md` after workers finish. The manual equivalent is `python scripts/summarize_external_benchmark_results.py`.
The generation pool defaults to one global vLLM memory/concurrency policy: `gpu_memory_utilization=0.90`, `max_num_batched_tokens=262144`, `max_num_seqs=512`, `MAX_TOKENS_OVERRIDE=4096`, and 2-second staggered worker startup on the 8-GPU schedule. The requested batch size defaults to 2048. For capped image-only runs, the runner queues the full requested chunk into vLLM so vLLM can refill completed sequences from the chunk backlog while respecting `max_num_seqs`. CPU prompt/image request construction is prefetched with `PREFETCH_WORKERS=4` and `PREFETCH_BATCHES=2`, overlapping the next chunks with current generation.
ScreenSpotPro must be materialized before VLM generation. Its TSV/image cache is large enough that lazy VLMEvalKit download inside a GPU worker leaves a loaded vLLM model idle while the CPU/network path downloads dataset files.

`VSI-Bench` is removed from the benchmark plan because video decoding/frame extraction dominated wall time and made the GPU look idle. Video benchmarks should be handled in a separate pipeline with predecoded frames if they are reintroduced.

Queue jobs are reclaimed after 15 minutes if a worker dies before marking completion, and each job is attempted at most twice by default.

## Benchmark Queue

| Benchmark | VLMEvalKit / Port Mapping | Notes |
|---|---|---|
| ChartQAPro | `ChartQAPro_CoT` | Completed. |
| ChartMuseum | local VLMEvalKit-compatible ChartMuseum test runner | Completed with local Qwen3-32B judge. |
| CharXivDesc | `CharXiv_descriptive_val` | Native VLMEvalKit. |
| CharXivReason | `CharXiv_reasoning_val` | Native VLMEvalKit. |
| EvoChart | `EvoChart_Qwen3_ZS` | Completed with Vero's Qwen3 zero-shot prompt. |
| InfoVQA | `InfoVQA_VAL` | Completed on labeled validation split; `InfoVQA_TEST` lacks answers for local scoring. |
| MMMU-ProVis | `MMMU_Pro_V_COT` | Completed with official COT prompt and `max_tokens=2048` after uncapped-COT sanity run was too slow. |
| MathVision | `MathVision` | Completed with local Qwen3-32B answer-extraction judge. |
| MathVista | `MathVista_MINI` | Completed with local Qwen3-32B answer-extraction judge. |
| MathVerse | `MathVerse_MINI_Vision_Only_cot` | Native VLMEvalKit COT variant. |
| LogicVista | `LogicVista` | Native VLMEvalKit. |
| Blink | `BLINK` | Native VLMEvalKit. |
| ERQA | `ERQA` | Native VLMEvalKit. |
| EmbSpatial | `EmbSpatialBench` | Native VLMEvalKit. |
| RoboSpatialHome | `RoboSpatialHome` | Native VLMEvalKit. |
| Game-QA-Lite | port from Vero `game_qa_lite_reasoning` behavior | Add support in VLMEvalKit-side code. |
| CountQA | port from Vero non-reasoning `countqa` behavior | Do not use reasoning prompt. |
| VStarBench | `VStarBench` | Native VLMEvalKit direct variant. |
| ScreenSpotPro | six `ScreenSpot_Pro_*` subsets | Report pooled sample-wise aggregate over 1,581 samples, with subset scores as secondary metrics. |
| MMStar | `MMStar` | Native VLMEvalKit. |
| MME-RealWorld-Lite | `MME-RealWorld-Lite` | Native VLMEvalKit. |
| TreeBench | `TreeBench` | Native VLMEvalKit. |
| VLMBlind | `VLMBlind` | Native VLMEvalKit. |
| VisionGraph-Q3 | `VisionGraph_Q3` | Local VLMEvalKit adapter using only the third graph-reasoning question per image; deterministic task-specific scoring. Included in the fixed `trace_candidate37_200` suite as a 200-question manifest sampled from 1,000 released Q3 test examples. |

## ScreenSpotPro Aggregation

ScreenSpotPro is treated as one benchmark family. Its headline score is pooled sample-wise:

```text
total_correct_across_subsets / total_samples_across_subsets
```

Subset sizes:

| Subset | Samples |
|---|---:|
| Development | 299 |
| Creative | 341 |
| CAD | 261 |
| Scientific | 254 |
| Office | 230 |
| OS | 196 |
| Total | 1581 |

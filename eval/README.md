# TRACE Evaluation Setup

This directory is the local home for benchmark evaluation that mirrors the Vero evaluation stack as closely as possible while keeping only the pieces we need in this repository.

## Scope

- Evaluation harness runtime: installed from the local clone at `/home/jovyan/work/vero/vero-eval`
- Local copied assets: only the Vero files needed for the first benchmark and runner entrypoint
- First benchmark: `ChartQA-Pro`
- Additional locally vendored benchmarks: `MathVista Mini`, `MathVision`
- Additional locally vendored grouped benchmark: `BLINK`
- Additional locally vendored benchmark: `EmbSpatial`
- Additional locally vendored benchmark: `CountQA`
- Additional locally vendored benchmark: `GameQALite`
- Additional locally vendored benchmark: `VStarBench`
- Additional locally vendored benchmark: `MMMU-ProVis`
- Additional locally vendored benchmark: `ERQA`
- Model under test: `zlab-princeton/Vero-Qwen3I-8B`
- Judge model for judge-backed benchmarks: `Qwen/Qwen3-32B`

`ChartQA-Pro` zero-shot evaluation does not require an LLM judge. It uses the Vero task prompt templates plus deterministic answer extraction and relaxed matching.
The default local reasoning task is also deterministic unless you explicitly use the local `chartqa_pro_reasoning_samplingq3_judge` query branch added in this repo.

## Local Layout

- [examples/eval.sh](/home/jovyan/work/trace/eval/examples/eval.sh): copied from `vero-eval/examples/eval.sh`
- [vendor/vero_eval/lmms_eval/tasks/chartqa_pro](/home/jovyan/work/trace/eval/vendor/vero_eval/lmms_eval/tasks/chartqa_pro): copied ChartQA-Pro task configs, prompts, and utilities
- [vendor/vero_eval/lmms_eval/tasks/mathvista](/home/jovyan/work/trace/eval/vendor/vero_eval/lmms_eval/tasks/mathvista): copied MathVista task configs, prompts, and utilities
- [vendor/vero_eval/lmms_eval/tasks/mathvision](/home/jovyan/work/trace/eval/vendor/vero_eval/lmms_eval/tasks/mathvision): copied MathVision task configs, prompts, and utilities
- [vendor/vero_eval/lmms_eval/tasks/blink](/home/jovyan/work/trace/eval/vendor/vero_eval/lmms_eval/tasks/blink): copied BLINK task configs, prompts, and utilities
- [vendor/vero_eval/lmms_eval/tasks/embspatial](/home/jovyan/work/trace/eval/vendor/vero_eval/lmms_eval/tasks/embspatial): copied EmbSpatial task configs, prompts, and utilities
- [vendor/vero_eval/lmms_eval/tasks/countqa](/home/jovyan/work/trace/eval/vendor/vero_eval/lmms_eval/tasks/countqa): copied CountQA task configs and utilities
- [vendor/vero_eval/lmms_eval/tasks/game_qa](/home/jovyan/work/trace/eval/vendor/vero_eval/lmms_eval/tasks/game_qa): copied GameQALite task configs and utilities
- [vendor/vero_eval/lmms_eval/tasks/vstar_bench](/home/jovyan/work/trace/eval/vendor/vero_eval/lmms_eval/tasks/vstar_bench): copied VStarBench task configs and utilities
- [vendor/vero_eval/lmms_eval/tasks/mmmu_pro](/home/jovyan/work/trace/eval/vendor/vero_eval/lmms_eval/tasks/mmmu_pro): copied MMMU-Pro task configs and utilities
- [vendor/vero_eval/lmms_eval/tasks/erqa](/home/jovyan/work/trace/eval/vendor/vero_eval/lmms_eval/tasks/erqa): copied ERQA task configs and utilities
- [vendor/vero_eval/lmms_eval/tasks/_task_utils/answer_extraction.py](/home/jovyan/work/trace/eval/vendor/vero_eval/lmms_eval/tasks/_task_utils/answer_extraction.py): copied deterministic answer extraction helper
- [vendor/vero_eval/lmms_eval/tasks/_task_utils/answer_parsing.py](/home/jovyan/work/trace/eval/vendor/vero_eval/lmms_eval/tasks/_task_utils/answer_parsing.py): copied judge-based extraction helper for future reasoning tasks
- [vendor/vero_eval/lmms_eval/tasks/chartqa_pro/chartqa_pro_reasoning_samplingq3_judge.yaml](/home/jovyan/work/trace/eval/vendor/vero_eval/lmms_eval/tasks/chartqa_pro/chartqa_pro_reasoning_samplingq3_judge.yaml): local judge-backed ChartQA-Pro reasoning variant
- [scripts/chartqa_reasoning_judge_score.py](/home/jovyan/work/trace/eval/scripts/chartqa_reasoning_judge_score.py): faster batched Qwen3-32B extractor/scorer for ChartQA-Pro reasoning outputs saved with `--predict_only`
- [scripts/mathvista_judge_score.py](/home/jovyan/work/trace/eval/scripts/mathvista_judge_score.py): batched Qwen3-32B extractor/scorer for MathVista Mini outputs saved with `--predict_only`
- [scripts/mathvision_judge_score.py](/home/jovyan/work/trace/eval/scripts/mathvision_judge_score.py): batched Qwen3-32B judge scorer for MathVision outputs saved with `--predict_only`
- [scripts/blink_judge_score.py](/home/jovyan/work/trace/eval/scripts/blink_judge_score.py): batched Qwen3-32B extraction/scorer for grouped BLINK outputs saved with `--predict_only`
- [scripts/embspatial_judge_score.py](/home/jovyan/work/trace/eval/scripts/embspatial_judge_score.py): batched Qwen3-32B extraction/scorer for EmbSpatial outputs saved with `--predict_only`
- [scripts/erqa_judge_score.py](/home/jovyan/work/trace/eval/scripts/erqa_judge_score.py): batched Qwen3-32B extraction/scorer for ERQA outputs saved with `--predict_only`
- [vendor/vero_eval/lmms_eval/api/metrics.py](/home/jovyan/work/trace/eval/vendor/vero_eval/lmms_eval/api/metrics.py): copied metrics module used by ChartQA-Pro scoring

The copied files are a local snapshot of the benchmark/task logic we are matching against. The executable evaluation runtime is installed into the local env from the Vero clone so behavior stays aligned with upstream.

For MathVista Mini, the default upstream Qwen3 prompt tasks are deterministic. Local judge-backed variants can be created by swapping `process_results` to `utils.mathvista_process_results_judge`, or by using `--predict_only` plus `scripts/mathvista_judge_score.py` for batched judge extraction.

For MathVision, upstream includes Qwen3 zero-shot and reasoning prompt tasks on the full `test` split. This repo also adds local `testmini` query branches for faster comparison runs:

- [mathvision_testmini_qwen3_thinking_zs.yaml](/home/jovyan/work/trace/eval/vendor/vero_eval/lmms_eval/tasks/mathvision/mathvision_testmini_qwen3_thinking_zs.yaml)
- [mathvision_testmini_reasoning_samplingq3.yaml](/home/jovyan/work/trace/eval/vendor/vero_eval/lmms_eval/tasks/mathvision/mathvision_testmini_reasoning_samplingq3.yaml)

The local fast path is `--predict_only` plus `scripts/mathvision_judge_score.py`, which mirrors upstream `mathvision_gpt_eval_process_results` but batches the Qwen3-32B judge calls.

For BLINK, upstream includes grouped `blink_qwen3_thinking_zs` and `blink_reasoning_samplingq3` tasks. Upstream default scoring is deterministic MCQ parsing, but BLINK also provides an LLM-extraction path via `blink_process_results_extract`. In this repo, the fast path is `--predict_only` plus `scripts/blink_judge_score.py`, which batches Qwen3-32B answer extraction across all BLINK subtasks and then applies BLINK's own option-letter parsing and aggregation.

For EmbSpatial, upstream includes `embspatial_qwen3_thinking_zs` and `embspatial_reasoning_samplingq3`. Upstream default scoring is deterministic MCQ parsing, but the task also provides an LLM-extraction path via `embspatial_process_results_extract`. In this repo, the fast path is `--predict_only` plus `scripts/embspatial_judge_score.py`, which batches Qwen3-32B answer extraction and then applies EmbSpatial's own option-letter parsing and per-relation aggregation.

For CountQA, upstream includes `countqa_qwen3_thinking_zs` and `countqa_reasoning_samplingq3` on the `test` split of `Jayant-Sravan/CountQA`. Upstream scoring is deterministic integer extraction through `extract_final_answer(...)` plus final-number matching, so no separate LLM-judge path is needed for the local eval flow.

For GameQALite, upstream includes `game_qa_lite_qwen3_thinking_zs` and `game_qa_lite_reasoning_samplingq3` on the `train` split of `gsarch/Game-QA-Lite`. Upstream scoring defaults to deterministic option parsing via `game_qa_process_results`, and also provides a judge-backed extraction path via `game_qa_process_results_extract` if we need that later.

For VStarBench, upstream includes `vstar_bench_qwen3_thinking_zs` and `vstar_bench_reasoning_samplingq3` on the `test` split of `lmms-lab/vstar-bench`. Upstream scoring is deterministic option-letter extraction and category-aware aggregation through `vstar_process_results` and `vstar_aggregate_results`.

For MMMU-ProVis, upstream uses the `vision` config of `MMMU/MMMU_Pro` on the `test` split, exposed through `mmmu_pro_vision_qwen3_thinking_zs` and `mmmu_pro_vision_reasoning_samplingq3`. Scoring is deterministic multiple-choice parsing through `mmmu_pro_process_results` and `mmmu_pro_aggregate_results`.

For ERQA, upstream includes `erqa_qwen3_thinking_zs` and `erqa_reasoning_samplingq3` on the `test` split of `FlagEval/ERQA`. Upstream defaults to deterministic option extraction, but also provides an LLM-extraction path via `erqa_process_results_extract`. In this repo, the fast path is `--predict_only` plus `scripts/erqa_judge_score.py`, which batches Qwen3-32B answer extraction and then applies ERQA's option-letter parsing and per-question-type aggregation.

## Environment

The isolated evaluation env lives at:

- `/home/jovyan/work/trace/eval/.venv`

This env is created as a path-based Python 3.10 conda environment so we can stay close to Vero's pinned runtime.

## Benchmark Settings

For `chartqa_pro_qwen3_zs`, Vero uses:

- dataset: `ahmed-masry/ChartQAPro`
- split: `test`
- generation:
  - `max_new_tokens=1024`
  - `temperature=1.0`
  - `top_p=1.0`
  - `top_k=40`
  - `presence_penalty=2.0`
  - `do_sample=True`
- task prompt postamble:
  - `Answer the question using a single word or phrase.`

Source file:

- [chartqa_pro_qwen3_zs.yaml](/home/jovyan/work/trace/eval/vendor/vero_eval/lmms_eval/tasks/chartqa_pro/chartqa_pro_qwen3_zs.yaml)

## Model Placement

Planned local model layout:

- `eval/models/Vero-Qwen3I-8B/`
- `eval/models/Qwen3-32B/`

Recommended GPU split for judge-backed benchmarks on this machine (`8 x A100 40GB`):

- evaluated model via vLLM: `6` GPUs
- LLM judge via vLLM: `2` GPUs

For `ChartQA-Pro` zero-shot and the default local reasoning task, the judge is not used, so the evaluated model can use all available GPUs if needed.
For the local `chartqa_pro_reasoning_samplingq3_judge` variant, the evaluator frees the model before postprocessing and then instantiates the Qwen3-32B judge locally.

## Expected Commands

Activate the env:

```bash
conda activate /home/jovyan/work/trace/eval/.venv
```

If your Hugging Face token is not already configured in the shell, export it before downloading models or datasets:

```bash
export HF_TOKEN=...
```

Run a single task in the same style as Vero:

```bash
cd /home/jovyan/work/trace/eval
bash examples/eval.sh \
  --model-path zlab-princeton/Vero-Qwen3I-8B \
  --tasks chartqa_pro_qwen3_zs \
  --output-path ./outputs/chartqa_pro
```

Run a judge-backed task later:

```bash
cd /home/jovyan/work/trace/eval
JUDGE_MODEL_PATH=/home/jovyan/work/trace/eval/models/Qwen3-32B \
VLLM_TENSOR_PARALLEL_SIZE=2 \
CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 bash examples/eval.sh \
  --model-path zlab-princeton/Vero-Qwen3I-8B \
  --tasks <judge_task> \
  --num-gpus 8 \
  --output-path ./outputs/<judge_task>
```

The local wrapper now forwards `--judge-model` by exporting `JUDGE_MODEL_PATH`; the installed Vero runtime does not accept older `--judge_model_*` CLI flags directly.

## Downloads

Background download logs and pid files are written to:

- `/home/jovyan/work/trace/eval/cache/download_logs/`

Current model targets:

- judge: `/home/jovyan/work/trace/eval/models/Qwen3-32B/`
- evaluated model: `/home/jovyan/work/trace/eval/models/Vero-Qwen3I-8B/`

## Notes

- `ChartQA-Pro` is the first benchmark because its default Vero flow avoids the LLM judge path while still matching the Vero chart evaluation flow.
- The `chartqa_pro_reasoning_samplingq3_judge` task is a local extension for judge-based answer extraction; it is not the default upstream Vero ChartQA-Pro task.
- For throughput, prefer `--predict_only` plus `scripts/chartqa_reasoning_judge_score.py` over the per-example in-evaluator judge path.
- A separate results document should be added later under this directory once runs start producing outputs.

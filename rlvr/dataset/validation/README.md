# Qwen3-VL-2B Selected512 External Validation

This folder contains feasible validation subsets, up to 512 questions each, selected from 2048-token Qwen/Qwen3-VL-2B-Instruct source-pool evaluations. Some subsets were rebuilt from the exact RLVR trainer validation path.

| dataset | file | rows | selected acc | reported acc | extraction | cap | avg tokens | max tokens |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| mathverse_mini | mathverse_mini.parquet | 512 | 52.15% | 52.10% | 100.00% | 0.00% | 213.22 | 347 |
| mathvista_mini | mathvista_mini.parquet | 512 | 61.33% | 61.30% | 100.00% | 0.00% | 175.41 | 564 |
| mmstar | mmstar.parquet | 512 | 58.20% | 58.30% | 100.00% | 0.00% | 80.90 | 173 |
| charxiv_dq | charxiv_dq.parquet | 512 | 62.30% | 62.30% | 100.00% | 0.00% | 28.68 | 84 |
| charxiv_rq | charxiv_rq.parquet | 512 | 26.76% | 26.80% | 100.00% | 0.00% | 155.62 | 419 |
| embspatialbench | embspatialbench.parquet | 512 | 69.14% | 69.20% | 100.00% | 0.00% | 3.67 | 5 |
| blink | blink.parquet | 512 | 53.91% | 53.80% | 100.00% | 0.00% | 5.12 | 52 |
| countqa | countqa.parquet | 512 | 25.59% | 25.54%* | 100.00% | 0.00% | 98.67 | 138 |

Parquet schema: `uid`, `instance_id`, `benchmark_id`, `source_id`, `prompt`, `prompt_mode`, `images`, `ground_truth`, `parser_family`, `metadata`.
Selection diagnostics and exact source-pool runs remain under `runs/benchmark_exact_rlvr/`.

## Reproducing the metrics

The table above reports the selected-set metrics recorded in:
1. `manifest.json` in this folder
2. the per-dataset selection manifests referenced by `manifest.json`, for example:
   - `runs/benchmark_exact_rlvr/mathverse_mini_pool_qwen3_vl_2b/selected512/mathverse_mini_selected512.json`
   - `runs/benchmark_exact_rlvr/mathvista_mini_pool_qwen3_vl_2b/selected512/mathvista_mini_selected512.json`
   - `runs/benchmark_exact_rlvr/mmstar_pool_qwen3_vl_2b/selected512/mmstar_selected512.json`

Those numbers were built from the exact RLVR trainer validation path with:
1. model: `Qwen/Qwen3-VL-2B-Instruct`
2. `data.val_batch_size=512`
3. `worker.rollout.val_override_config.temperature=0.0`
4. `worker.rollout.val_override_config.top_p=1.0`
5. `worker.rollout.val_override_config.n=1`
6. `worker.rollout.val_override_config.max_tokens=2048`

To rerun the exact RLVR validation path on the current 8-dataset pack:

```bash
cd rlvr
python -m verl.trainer.main config=examples/config.yaml \
  data.train_files=dataset/validation/mathverse_mini.parquet \
  "data.val_files=[dataset/validation/mathverse_mini.parquet,dataset/validation/mathvista_mini.parquet,dataset/validation/mmstar.parquet,dataset/validation/charxiv_dq.parquet,dataset/validation/charxiv_rq.parquet,dataset/validation/embspatialbench.parquet,dataset/validation/blink.parquet,dataset/validation/countqa.parquet]" \
  data.prompt_key=prompt \
  data.answer_key=ground_truth \
  data.dataset_mode=trace \
  data.max_prompt_length=1024 \
  data.max_response_length=2048 \
  data.rollout_batch_size=128 \
  data.val_batch_size=512 \
  data.filter_overlong_prompts=false \
  data.train_dataloader_num_workers=0 \
  data.val_dataloader_num_workers=0 \
  worker.actor.model.model_path=Qwen/Qwen3-VL-2B-Instruct \
  worker.rollout.tensor_parallel_size=1 \
  worker.rollout.gpu_memory_utilization=0.8 \
  worker.rollout.limit_images=4 \
  worker.rollout.max_model_len=16384 \
  worker.rollout.max_num_batched_tokens=16384 \
  worker.rollout.val_override_config.temperature=0.0 \
  worker.rollout.val_override_config.top_p=1.0 \
  worker.rollout.val_override_config.n=1 \
  worker.rollout.val_override_config.max_tokens=2048 \
  trainer.project_name=benchmark_exact_rlvr \
  trainer.experiment_name=selected512_verify_qwen3_vl_2b \
  "trainer.logger=[console]" \
  trainer.val_only=true \
  trainer.val_predictions_dump_dir=../runs/benchmark_selected512_exact_verify/qwen3_vl_2b \
  trainer.find_last_checkpoint=false \
  trainer.save_freq=-1 \
  trainer.val_freq=-1
```

That rerun writes per-dataset metrics under:
1. `runs/benchmark_selected512_exact_verify/qwen3_vl_2b/global_step_0/<dataset>/metrics.json`
2. `runs/benchmark_selected512_exact_verify/qwen3_vl_2b/global_step_0/<dataset>/predictions.jsonl`

Important caveat: a fresh rerun can drift slightly from the table because a small number of rows near the response-length boundary may flip between `stop` and `length` at `2048` tokens. The README table is the selected-set source metric, not a guarantee that every fresh rerun will land on exactly the same extraction rate.

`*` CountQA does not use a published Qwen3-VL-2B reference score here. The `25.54%` reference is the full extracted-answer accuracy from the exact RLVR trainer validation run.

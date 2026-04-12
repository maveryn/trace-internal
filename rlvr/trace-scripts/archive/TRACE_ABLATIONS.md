# TRACE Ablations

This directory contains the 4 TRACE RLVR ablation launchers for the `Qwen/Qwen2.5-VL-3B-Instruct` 4-GPU setup.

## Training Parquet

All 4 launchers are expected to train from the same built TRACE 128k dataset, exported into one self-contained RLVR parquet:

1. `rlvr/dataset/train/trace_rlvr_train_128k_all_tasks.parquet`
2. fallback HF repo: `xashru/trace-rlvr-train-128k@train`

This parquet keeps:

1. `answer_gt`
2. `evidence_gt`
3. `reward_contract`
4. `bucket_id_str`
5. `prompt_answer_only`
6. `prompt_answer_and_evidence`
7. embedded image bytes under `images`

If the local parquet is missing, the shared launcher automatically falls back to the HF dataset repo above. For a private HF repo, `HF_TOKEN` or `HUGGINGFACE_TOKEN` must be set in the environment.

## Validation Pack

All 4 launchers use the shared external validation pack defined in:

1. `rlvr/trace-scripts/validation_pack_qwen3_vl_2b_selected512.sh`

That pack points at:

1. `rlvr/dataset/validation/mathverse_mini.parquet`
2. `rlvr/dataset/validation/mathvista_mini.parquet`
3. `rlvr/dataset/validation/mmstar.parquet`
4. `rlvr/dataset/validation/charxiv_dq.parquet`
5. `rlvr/dataset/validation/charxiv_rq.parquet`
6. `rlvr/dataset/validation/embspatialbench.parquet`
7. `rlvr/dataset/validation/blink.parquet`
8. `rlvr/dataset/validation/countqa.parquet`

Validation frequency is fixed to every `20` training steps in the ablation wrappers.

## Launchers

1. `trace_answer_only.sh`
   Training prompt column: `prompt_answer_only`.
   Training reward: answer-only (`overall = answer_reward`).
   Curriculum: `none`.

2. `trace_answer_only_curriculum.sh`
   Training prompt column: `prompt_answer_only`.
   Training reward: answer-only (`overall = answer_reward`).
   Curriculum: `self_paced_ema`.

3. `trace_answer_evidence.sh`
   Training prompt column: `prompt_answer_and_evidence`.
   Training reward: gated answer+evidence TRACE reward.
   Curriculum: `none`.

4. `trace_answer_evidence_curriculum.sh`
   Training prompt column: `prompt_answer_and_evidence`.
   Training reward: gated answer+evidence TRACE reward.
   Curriculum: `self_paced_ema`.

## Shared Fixed Knobs

The ablation wrappers keep these fixed by default:

1. model: `Qwen/Qwen2.5-VL-3B-Instruct`
2. GPUs: `4`
3. `max_steps=250`
4. `val_freq=20`
5. `save_freq=20`
6. same rollout/data/optimizer settings via `trace-scripts/config_trace.yaml`

Only these vary across the 4 scripts:

1. training prompt column
2. TRACE reward mode
3. curriculum mode

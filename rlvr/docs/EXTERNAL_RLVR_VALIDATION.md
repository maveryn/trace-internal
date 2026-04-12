# External RLVR Validation

Reference for the fixed external validation pack used by RLVR training.

## 1) Scope
This path is for answer-only external validation during RLVR.

It is intentionally separate from TRACE training export:
- TRACE training data keeps TRACE-native prompts, answers, evidence, and reward contracts.
- External validation keeps benchmark-faithful prompts and answer-only targets.
- The frozen RLVR-ready validation pack lives under `rlvr/dataset/validation/`.

## 2) Current validation pack
The current recurring RLVR validation pack lives in:
- `rlvr/dataset/validation/`

It contains the current `8 x 512` shortlist:
1. `mathverse_mini`
2. `mathvista_mini`
3. `mmstar`
4. `charxiv_dq`
5. `charxiv_rq`
6. `embspatialbench`
7. `blink`
8. `countqa`

Files in that folder:
1. one RLVR-ready parquet per benchmark,
2. `combined.parquet` with all `4096` selected rows as an offline convenience artifact,
2. `manifest.json` with selected-set metrics and references,
3. `README.md` summarizing the pack.

## 3) Row contract
Each validation row includes:
1. `uid`
2. `instance_id`
3. `benchmark_id`
4. `source_id`
5. `prompt`
6. `prompt_mode`
7. `images`
8. `ground_truth`
9. `parser_family`
10. `metadata`

Notes:
1. These rows are answer-only on purpose.
2. They use the RLVR validation path in `rlvr/verl/utils/val_reward.py`.
3. The pack does not bake boxed-answer text into the parquet; RLVR applies shared validation formatting at runtime.
4. Images are embedded directly into the parquet rows.
5. `combined.parquet` normalizes `ground_truth` and `metadata` to strings so all 8 benchmarks can share one physical parquet; the TRACE loader decodes JSON metadata back to Python objects at runtime.

## 4) Training-script default
The RLVR trace launchers share the default validation list from:
- `rlvr/trace-scripts/validation_pack_qwen3_vl_2b_selected512.sh`

That shell fragment now defines `DEFAULT_VAL_FILES_JSON` as the 8 individual
benchmark parquets under `rlvr/dataset/validation/`.

This matches the `symrl` validation flow:
1. one validation dataloader per benchmark,
2. `val_batch_size=512`,
3. rollout engine prepare/generate/release inside the per-benchmark loop.

Per-dataset metrics are therefore logged directly from the benchmark-specific
validation loop. `combined.parquet` is not the default training path.

## 5) Maintenance policy
This repo no longer keeps the old benchmark export builder pipeline.

If the validation pack needs to be rebuilt or resampled:
1. generate or screen the benchmark data outside the training critical path,
2. write the finalized selected parquets into `rlvr/dataset/validation/`,
3. update `manifest.json` and `README.md`,
4. keep the RLVR validation path unchanged.

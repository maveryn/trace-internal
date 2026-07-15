# Trace External Validation Pack

This folder is the active Trace-style benchmark validation pack for the new `rlvr/` stack.

Current scope:

- `mathvista_mini.parquet`
- `mmstar.parquet`
- `charxiv_rq.parquet`
- `embspatialbench.parquet`
- `mmmu_pro_vision.parquet`
- `countqa.parquet`

Excluded for now:

- `mathverse_mini`

These parquet files are symlinked to the archived source assets under `rlvr_legacy/dataset/validation/`.
The new PPO trainer can run Trace-style validation by setting:

- `data.validation_style=trace_benchmark`
- `data.val_files=[...]`
- `data.val_prompt_key=prompt_answer`
- `data.val_answer_key=answer_gt`
- `data.val_disable_system_prompt=false`
- `data.val_format_prompt=null`
- `data.max_prompt_length=1536`
- `data.max_response_length=1536`

Legacy external benchmark rows still carry `prompt`/`ground_truth` columns, and the Trace dataset loader
falls back to those when `prompt_answer`/`answer_gt` are absent. Prepared rows such as MMMU-Pro Vision
and CountQA carry both column pairs and are evaluated with the same answer-mode JSON system prompt used
during Trace RLVR training.

When this mode is enabled, validation runs one dataloader per benchmark and reports metrics under:

- `val-core/<benchmark>/...`
- `val-aux/<benchmark>/...`

See `manifest.json` in this directory for the exact retained benchmark list and source paths.

MMMU-Pro Vision can be regenerated with:

```bash
python rlvr/scripts/prepare_mmmu_pro_vision_validation.py --sample-size 512 --seed 20260504 --max-image-pixels 1048576
```

CountQA can be regenerated with:

```bash
python rlvr/scripts/prepare_countqa_validation.py --sample-size 512 --seed 20260504 --max-image-pixels 1048576
```

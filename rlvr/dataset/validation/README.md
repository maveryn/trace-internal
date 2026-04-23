# TRACE External Validation Pack

This folder is the active TRACE-style benchmark validation pack for the new `rlvr/` stack.

Current scope:

- `mathvista_mini.parquet`
- `mmstar.parquet`
- `charxiv_dq.parquet`
- `charxiv_rq.parquet`
- `embspatialbench.parquet`
- `blink.parquet`

Excluded for now:

- `mathverse_mini`
- `countqa`

These parquet files are symlinked to the archived source assets under `rlvr_legacy/dataset/validation/`.
The new PPO trainer can run TRACE-style validation by setting:

- `data.validation_style=trace_benchmark`
- `data.val_files=[...]`
- `data.val_prompt_key=prompt`
- `data.val_answer_key=ground_truth`
- `data.val_disable_system_prompt=true`
- `data.val_format_prompt=./examples/format_prompt/math.jinja`

When this mode is enabled, validation runs one dataloader per benchmark and reports metrics under:

- `val-core/<benchmark>/...`
- `val-aux/<benchmark>/...`

See `manifest.json` in this directory for the exact retained benchmark list and source paths.

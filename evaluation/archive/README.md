# Legacy Evaluation Archive

`evaluation/final25` is the only active final-comparison contract. Evaluation
scripts, repair utilities, and result artifacts elsewhere in this repository
predate that frozen campaign and are retained only for provenance or historical
reanalysis.

They remain at their existing paths so old reports and committed provenance do
not break. They must not be used as completion markers, caches, score inputs, or
result sources for a Final25 run. The Final25 launcher uses a fresh tmpfs
campaign root, content-addressed request/judge caches, campaign-specific queue
names, and exact archive coverage checks, which enforce this separation without
rewriting historical paths.

No new runtime result belongs under this archive directory. Completed Final25
responses, extractions, and scores are stored as immutable Parquet slices in the
private HF archive; local runtime files remain under the configured tmpfs
campaign root.

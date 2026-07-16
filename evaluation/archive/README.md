# Legacy Evaluation Archive

`evaluation/final24` is the active final-comparison reporting selection. It
inherits benchmark-level contracts from the immutable `evaluation/final25`
All31 source campaign. Other evaluation scripts, repair utilities, and result
artifacts are retained for provenance or historical reanalysis.

They remain at their existing paths so old reports and committed provenance do
not break. They must not be used as completion markers, caches, score inputs, or
result sources for a new campaign. The historical launcher uses a fresh tmpfs
campaign root, content-addressed request/judge caches, campaign-specific queue
names, and exact archive coverage checks, which enforce this separation without
rewriting historical paths.

No new runtime result belongs under this archive directory. Completed
responses, extractions, and scores are stored as immutable Parquet slices in the
private HF archive; local runtime files remain under the configured tmpfs
campaign root.

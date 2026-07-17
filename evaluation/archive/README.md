# Legacy Evaluation Archive

`evaluation/trace_eval` is the active external-comparison suite. The content in
this archive, along with the older numbered evaluation directories, is retained
only for provenance and historical reanalysis.

They remain at their existing paths so old reports and committed provenance do
not break. They must not be used as completion markers, caches, score inputs, or
result sources for a new campaign. The historical launcher uses a fresh tmpfs
campaign root, content-addressed request/judge caches, campaign-specific queue
names, and exact archive coverage checks, which enforce this separation without
rewriting historical paths.

No new runtime result belongs under this archive directory. Raw prompts,
responses, extractions, scores, and source identities remain in the local or
internal archive. Only the separately validated, allowlisted neutral Parquet
export may be uploaded to the paper repository; local runtime files remain
under the configured tmpfs campaign root.

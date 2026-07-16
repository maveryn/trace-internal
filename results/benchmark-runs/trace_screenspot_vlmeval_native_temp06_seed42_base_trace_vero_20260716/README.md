# ScreenSpot - VLMEvalKit prompt with native media

Status: complete. All three models generated and scored all 1,272 ScreenSpot
examples with zero API errors and zero length-cap finishes.

| Model | Correct | Overall Acc (%) | Delta vs base (pp) | Mobile (%) | Desktop (%) | Web (%) | Parser misses |
|---|---:|---:|---:|---:|---:|---:|---:|
| Qwen2.5-VL-7B base | 972 / 1,272 | 76.4151 | 0.0000 | 83.2669 | 64.9701 | 77.2936 | 22 |
| TRACE step 500 rerun | 994 / 1,272 | 78.1447 | +1.7296 | 84.2629 | 65.5689 | 80.7339 | 13 |
| VERO Qwen2.5-VL-7B | 878 / 1,272 | 69.0252 | -7.3899 | 68.5259 | 63.4731 | 73.8532 | 238 |

This is the controlled media-bound comparison. It restores the exact
historical pinned VLMEvalKit ScreenSpot prompt payload and named x/y scoring
path while changing Qwen's minimum processor area from 1,003,520 to 3,136
pixels. The concatenated prompt corpus SHA-256 is
`c82e949bc7b3175f2f8959f002e2e5e077ac814ac550a315332b1d082a404d66`
in both the old and this run. Dataset rows, source media, maximum image area,
models, sampling, and seed are unchanged.

| Model | VLMEvalKit + 1MP floor (%) | VLMEvalKit + native (%) | Native delta (pp) | VERO protocol + native (%) |
|---|---:|---:|---:|---:|
| Qwen2.5-VL-7B base | 68.7893 | 76.4151 | +7.6258 | 83.4906 |
| TRACE step 500 rerun | 72.0912 | 78.1447 | +6.0535 | 81.7610 |
| VERO Qwen2.5-VL-7B | 62.1855 | 69.0252 | +6.8396 | 89.7013 |

Native resolution therefore accounts for a reproducible 6.05 to 7.63 point
improvement under the same VLMEvalKit protocol. It does not account for the
full VERO-protocol result, especially for the VERO checkpoint. The final
column changes prompt and coordinate response/parser protocol together and is
included for context, not as a media-only comparison.

Generation used seed 42, temperature 0.6, top-p 1.0, top-k -1, presence
penalty 0, repetition penalty 1, and 16,384 maximum output tokens. Images were
sent as verified source files and Qwen used the 3,136 to 12,845,056 pixel
bounds. Scoring retained the pinned VLMEvalKit parser and point-in-box
geometry, plus the existing narrow adapter for one unambiguous explicit action
inside a single `<answer>` block. The adapter changed 0 Base rows, 0 TRACE
rows, and 481 VERO rows.

The live artifacts are under
`/dev/shm/trace_rlvr/trace_screenspot_vlmeval_native_temp06_seed42_3models_20260716T151214Z`.
Compact generation and score receipts are preserved beside this README.

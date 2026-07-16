# ScreenSpot - native media, base vs TRACE vs VERO

Status: complete. All three models generated and scored all 1,272 ScreenSpot
examples with zero API errors and zero length-cap finishes.

| Model | Correct | Overall Acc (%) | Delta vs base (pp) | Mobile (%) | Desktop (%) | Web (%) | Parser misses |
|---|---:|---:|---:|---:|---:|---:|---:|
| Qwen2.5-VL-7B base | 1,062 / 1,272 | 83.4906 | 0.0000 | 88.6454 | 77.8443 | 81.8807 | 2 |
| TRACE step 500 rerun | 1,040 / 1,272 | 81.7610 | -1.7296 | 86.6534 | 75.1497 | 81.1927 | 3 |
| VERO Qwen2.5-VL-7B | 1,141 / 1,272 | 89.7013 | +6.2107 | 91.4343 | 87.7246 | 89.2202 | 0 |

Generation used the same VERO ScreenSpot protocol for every model: the common
helpful-assistant system message and an absolute-pixel `point_2d` JSON response.
Sampling used seed 42, temperature 0.6, top-p 1.0, top-k -1, presence penalty
0, repetition penalty 1, and 16,384 maximum output tokens. All responses ended
normally, so the larger cap did not affect truncation.

Images were sent as their verified source files. Qwen processing used the
checkpoint-native 3,136 to 12,845,056 pixel bounds with normal 28-pixel grid
alignment. Scoring parsed the VERO absolute point, normalized it using the
original image dimensions, and used pinned VLMEvalKit ScreenSpot point-in-box
geometry. The pinned VLMEvalKit commit was
`a8b12bf1c3737a33fc1de967c202f9c592b22e86`.

The previous comparison reported Base 68.79%, TRACE 72.09%, and VERO 62.19%.
Those values should be superseded by this run. The changes of +14.70, +9.67,
and +27.51 percentage points respectively are protocol-level changes: prompt,
coordinate parsing, and media bounds changed together, so they are not an
isolated estimate of the media-bound effect.

The live full artifacts are under
`/dev/shm/trace_rlvr/trace_screenspot_vero_native_temp06_seed42_3models_20260716T144252Z`.
Compact generation and score receipts are preserved beside this README.

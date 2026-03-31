# RLVR Status (2026-02-02)

## Current status
- Qwen2.5-VL 7B runs successfully with vLLM after lowering `worker.rollout.gpu_memory_utilization` to 0.8.
- Qwen3-VL 4B is unstable in this environment: slow steps and multiple library incompatibilities.

## Qwen3-VL 4B issues observed
- **Processor missing**: `AutoProcessor.from_pretrained("Qwen/Qwen3-VL-4B-Instruct")` returns a tokenizer class (no `Qwen3VLProcessor` in current Transformers), which caused `None.apply_chat_template(...)` in dataset filtering.
- **vLLM fallback path**: vLLM logs indicate multimodal execution falls back to Transformers kernels, which is slower than native vLLM.
- **vLLM API drift**: needed updates for `mm_processor_cache_gb` and `get_tp_group()`.
- **Slow log-prob recompute**: long sequences and multi-modal preprocessing dominate runtime (even after disabling param offload).
- **Torch Inductor cache warnings**: corrupted cache entries in `/tmp/torchinductor_*` add overhead.

## Possible fixes
- **Version pinning**: roll back to the exact library versions where Qwen3-VL was fast (vLLM, Transformers, PyTorch, flash-attn, flashinfer).
- **Upgrade support**: move to Transformers/vLLM versions that include a native Qwen3-VL processor and vLLM multimodal implementation.
- **Disable compile**: set `worker.actor.use_torch_compile=false` to avoid inductor cache issues.
- **Speed knobs**: reduce `rollout.n` and `max_response_length`, increase micro-batch sizes (within divisibility constraints), and lower `min_pixels` to reduce image preprocessing cost.

## Notes
- CountQA accuracy is sensitive to exact boxed integer output (e.g., `\boxed{2}`), due to strict grading.

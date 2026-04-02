from __future__ import annotations

import types


def _ensure_vllm_torch_compat() -> None:
    """Patch torch 2.8 so current vLLM nightlies can import cleanly.

    Some recent vLLM nightlies assume
    `torch._dynamo.convert_frame.GraphCaptureOutput` exists for torch < 2.12.
    Torch 2.8 does not expose that symbol, so `import vllm` fails before the
    actual runtime is initialized.

    RLVR launchers prepend this directory to `PYTHONPATH`, so `sitecustomize`
    is imported automatically by Python. When the symbol is missing we provide a
    minimal placeholder that satisfies vLLM's import-time monkeypatch. The
    placeholder is only used to unblock the import path; torch 2.8 does not
    instantiate this class itself.
    """

    try:
        import torch._dynamo.convert_frame as convert_frame
    except Exception:
        return

    if hasattr(convert_frame, "GraphCaptureOutput"):
        return

    class _GraphCaptureOutputCompat:
        def get_runtime_env(self):
            return types.SimpleNamespace(external_refs=[], used_globals={})

    convert_frame.GraphCaptureOutput = _GraphCaptureOutputCompat


_ensure_vllm_torch_compat()

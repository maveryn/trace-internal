from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any


def _bootstrap_repo_sitecustomize() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)
    try:
        import sitecustomize  # noqa: F401
    except Exception:
        pass


def _safe_version(module: Any) -> str:
    return str(getattr(module, "__version__", "unknown"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-check the local RLVR runtime for Qwen3.5 support.")
    parser.add_argument("--model", default="Qwen/Qwen3.5-0.8B-Base", help="Model id to validate.")
    args = parser.parse_args()

    _bootstrap_repo_sitecustomize()

    import transformers
    import vllm
    from transformers import AutoConfig, AutoProcessor

    print(f"transformers={_safe_version(transformers)}")
    print(f"vllm={_safe_version(vllm)}")

    config = AutoConfig.from_pretrained(args.model, trust_remote_code=False)
    print(f"model_type={getattr(config, 'model_type', None)}")
    print(f"architectures={getattr(config, 'architectures', None)}")

    processor = AutoProcessor.from_pretrained(args.model, trust_remote_code=False, use_fast=True)
    print(f"processor={processor.__class__.__name__}")
    image_processor = getattr(processor, "image_processor", None)
    print(f"image_processor={image_processor.__class__.__name__ if image_processor is not None else None}")
    print(f"model_input_names={list(getattr(processor, 'model_input_names', []))}")

    if str(getattr(config, "model_type", "")).strip() != "qwen3_5":
        raise SystemExit("Qwen3.5 runtime check failed: expected model_type=qwen3_5.")
    if "Qwen3VLProcessor" not in processor.__class__.__name__:
        raise SystemExit("Qwen3.5 runtime check failed: expected a Qwen3VLProcessor-compatible processor.")

    print("Qwen3.5 runtime check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

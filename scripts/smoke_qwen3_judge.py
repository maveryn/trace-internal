#!/usr/bin/env python3
"""Smoke-test the local VERO Qwen3 text judge."""

from lmms_eval.tasks._task_utils.vllm_judge import get_judge_engine


def main() -> None:
    engine = get_judge_engine("Qwen/Qwen3-32B")
    print("engine", type(engine).__name__, "multimodal", getattr(engine, "supports_multimodal", None))
    print(engine.generate_json('Return exactly this JSON: {"ok": true}', max_tokens=32))


if __name__ == "__main__":
    main()

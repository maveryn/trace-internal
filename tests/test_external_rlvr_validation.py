from __future__ import annotations

from benchmark.external_rlvr_validation import _build_prompt


def test_build_prompt_keeps_benchmark_prompt_intact_without_suffix() -> None:
    prompt = _build_prompt(
        "What is 2 + 2?",
        choices=[("A", "3"), ("B", "4")],
        prompt_suffix_style=None,
    )
    assert prompt == "What is 2 + 2?\n\nA. 3\nB. 4"


def test_build_prompt_can_still_append_optional_suffix_style() -> None:
    prompt = _build_prompt(
        "What is 2 + 2?",
        choices=None,
        prompt_suffix_style="boxed_final_answer",
    )
    assert prompt.endswith("Provide only the final answer, wrapped in \\boxed{}.")

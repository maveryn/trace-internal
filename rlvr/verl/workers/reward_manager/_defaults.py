from __future__ import annotations

from functools import lru_cache
from typing import Any, Callable


@lru_cache(maxsize=1)
def resolve_default_compute_score() -> Callable[..., Any]:
    try:
        from verl.utils.reward_score import default_compute_score

        return default_compute_score
    except ImportError:
        from vero_reward import default_compute_score

        return default_compute_score


@lru_cache(maxsize=1)
def resolve_extract_answer() -> Callable[..., Any]:
    try:
        from verl.utils.reward_score.math_verify_reward_type_boxed import _extract_answer

        return _extract_answer
    except ImportError:
        from vero_reward.math_verify_reward_type_boxed import _extract_answer

        return _extract_answer

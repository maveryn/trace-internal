import json
import re
from typing import Any


REWARD_NAME = "trace_answer_json"
REWARD_TYPE = "batch"


def _extract_answer(response: str) -> Any:
    match = re.search(r"\{.*?\}", response, flags=re.DOTALL)
    if not match:
        return None

    try:
        payload = json.loads(match.group(0))
    except Exception:
        return None

    return payload.get("answer")


def _gold_value(ground_truth: Any) -> Any:
    if isinstance(ground_truth, str):
        try:
            ground_truth = json.loads(ground_truth)
        except Exception:
            return ground_truth.strip()

    if isinstance(ground_truth, dict) and "value" in ground_truth:
        return ground_truth["value"]

    return ground_truth


def compute_score(
    reward_inputs: list[dict[str, Any]],
    format_weight: float = 0.05,
    **_: Any,
) -> list[dict[str, float]]:
    scores = []
    for reward_input in reward_inputs:
        pred = _extract_answer(reward_input["response"])
        gold = _gold_value(reward_input["ground_truth"])

        format_score = 1.0 if pred is not None else 0.0
        accuracy_score = 1.0 if pred == gold else 0.0
        scores.append(
            {
                "overall": (1.0 - format_weight) * accuracy_score + format_weight * format_score,
                "format": format_score,
                "accuracy": accuracy_score,
            }
        )

    return scores

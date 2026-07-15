# Copyright 2024 Bytedance Ltd. and/or its affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import ast
import json
import re
from collections import defaultdict
from numbers import Integral
from typing import Any, Optional

import numpy as np
import torch
from mathruler.grader import extract_boxed_content, grade_answer
from transformers import PreTrainedTokenizer

from ..protocol import DataProto
from .local_strict_eval import strict_score_response
from .trace_reward import extract_trace_answer_for_scoring, is_trace_reward_input, score_trace_response


_CHOICE_LETTERS = "ABCDEFGHIJKL"
_CHOICE_SINGLE_RE = re.compile(
    rf"\(([{_CHOICE_LETTERS}a-l])\)|(?<![A-Za-z0-9])([{_CHOICE_LETTERS}a-l])(?=[^A-Za-z0-9]|$)"
)
_CHOICE_SEQ_RE = re.compile(rf"(?<![A-Za-z0-9])([{_CHOICE_LETTERS}]{{2,12}})(?=[^A-Za-z0-9]|$)")
_CHOICE_PREFIX_RE = re.compile(r"^\s*\(?([A-La-l])[\)\.\:]\s*(.*)$")
_NUMBER_RE = re.compile(r"[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?")
_NUMBER_OR_FRAC_RE = re.compile(
    r"[-+]?\d+\s*/\s*\d+|[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
)
_YES_NO_RE = re.compile(r"(?<![A-Za-z])(yes|no|true|false)(?![A-Za-z])", re.IGNORECASE)
_INT_RE = re.compile(r"[-+]?\d+")


def score_external_response(
    *,
    response: str,
    ground_truth: Any,
    prompt_text: str | None = None,
    parser_family: str | None = None,
    metadata: Any | None = None,
) -> tuple[float, bool, str | None, str]:
    """Score an external validation response, accepting Trace JSON answer payloads."""
    extracted_trace_answer = extract_trace_answer_for_scoring(response)
    if extracted_trace_answer is not None:
        accuracy, extracted, extracted_answer, method = strict_score_response(
            response=extracted_trace_answer,
            ground_truth=ground_truth,
            prompt_text=prompt_text,
            parser_family=parser_family,
            metadata=metadata,
        )
        return (
            accuracy,
            True,
            extracted_answer if extracted_answer is not None else extracted_trace_answer,
            f"trace_json:{method}",
        )

    return strict_score_response(
        response=response,
        ground_truth=ground_truth,
        prompt_text=prompt_text,
        parser_family=parser_family,
        metadata=metadata,
    )


def _is_non_string_sequence(value: Any) -> bool:
    return isinstance(value, (list, tuple)) and not isinstance(value, (str, bytes))


def _normalize_binary_grid(sequence_value: Any) -> list[list[int]] | None:
    if not _is_non_string_sequence(sequence_value):
        return None

    rows = list(sequence_value)
    if not rows:
        return None

    normalized: list[list[int]] = []
    row_length: int | None = None

    for row in rows:
        if not _is_non_string_sequence(row):
            return None
        row_list = list(row)
        if row_length is None:
            row_length = len(row_list)
            if row_length == 0:
                return None
        elif len(row_list) != row_length:
            return None

        normalized_row: list[int] = []
        for cell in row_list:
            if isinstance(cell, Integral):
                normalized_value = int(cell)
            else:
                return None

            if normalized_value not in (0, 1):
                return None

            normalized_row.append(normalized_value)

        normalized.append(normalized_row)

    return normalized


def _to_numpy_grid(value: Any) -> np.ndarray | None:
    if isinstance(value, str):
        try:
            value = ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return None

    if isinstance(value, np.ndarray):
        if value.ndim != 2:
            return None
        if not np.isin(value, (0, 1)).all():
            return None
        return value.astype(np.int8)

    normalized = _normalize_binary_grid(value)
    if normalized is None:
        return None
    return np.array(normalized, dtype=np.int8)


def _parse_response_grid(answer: str | None) -> np.ndarray | None:
    if not answer:
        return None

    try:
        parsed = ast.literal_eval(answer)
    except (SyntaxError, ValueError, TypeError):
        normalized = answer.replace("{", "[").replace("}", "]")
        try:
            parsed = ast.literal_eval(normalized)
        except (SyntaxError, ValueError, TypeError):
            return None

    return _to_numpy_grid(parsed)


def _extract_choice_letters(text: str) -> list[str]:
    if not text:
        return []

    matches = []
    for match in _CHOICE_SINGLE_RE.finditer(text):
        letter = match.group(1) or match.group(2)
        if letter:
            matches.append(letter.upper())

    if matches:
        return matches

    seq_match = _CHOICE_SEQ_RE.search(text.upper())
    if seq_match:
        return list(seq_match.group(1))

    return []


def _normalize_yes_no(value: str) -> Optional[str]:
    if value is None:
        return None
    s = value.strip().lower()
    if s in {"yes", "true", "y", "1"}:
        return "yes"
    if s in {"no", "false", "n", "0"}:
        return "no"
    return None


def _extract_yes_no(text: str) -> Optional[str]:
    if not text:
        return None
    matches = _YES_NO_RE.findall(text)
    if not matches:
        return None
    return _normalize_yes_no(matches[-1])


def _contains_latex(value: str) -> bool:
    if not value:
        return False
    return "\\" in value or "$" in value or "frac" in value or "sqrt" in value


def _split_prefixed_choice_answer(gt: str) -> Optional[tuple[str, str]]:
    if not gt:
        return None
    match = _CHOICE_PREFIX_RE.match(gt.strip())
    if not match:
        return None
    return match.group(1).upper(), match.group(2).strip()


def _parse_numeric_value(value: str) -> Optional[float]:
    if value is None:
        return None
    s = value.strip()
    if not s:
        return None
    frac_match = re.fullmatch(r"[-+]?\d+\s*/\s*\d+", s)
    if frac_match:
        num, denom = s.split("/")
        try:
            denom_val = float(denom)
            if denom_val == 0:
                return None
            return float(num) / denom_val
        except ValueError:
            return None
    if "," in s and not re.fullmatch(r"[-+]?\d{1,3}(?:,\d{3})+(?:\.\d+)?", s):
        return None
    s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def _extract_numeric_values(text: str) -> list[float]:
    if not text:
        return []
    matches = _NUMBER_OR_FRAC_RE.findall(text)
    values: list[float] = []
    for match in matches:
        parsed = _parse_numeric_value(match)
        if parsed is not None:
            values.append(parsed)
    return values


def _parse_choice_ground_truth(gt: str) -> Optional[list[str]]:
    if not gt:
        return None
    s = gt.strip().upper()
    if not s:
        return None

    prefixed = _split_prefixed_choice_answer(s)
    if prefixed is not None:
        return [prefixed[0]]

    if re.search(r"\d", s):
        return None
    # remove common conjunctions
    s_norm = re.sub(r"\b(AND|OR)\b", "", s)
    # letters outside choice range => not MCQ
    if re.search(rf"[M-Z]", s_norm):
        return None
    letters = re.findall(rf"[{_CHOICE_LETTERS}]", s_norm)
    if not letters:
        return None
    cleaned = re.sub(rf"[{_CHOICE_LETTERS}\s,;/\\()\[\]-]", "", s_norm)
    if cleaned:
        return None
    if re.fullmatch(rf"[{_CHOICE_LETTERS}]{{2,12}}", s_norm):
        if len(set(letters)) != len(letters):
            return None
    return letters


def _numbers_equal(pred: str, gt: str) -> bool:
    pred_val = _parse_numeric_value(pred)
    if pred_val is None:
        return False
    gt_val = _parse_numeric_value(gt)
    if gt_val is None:
        return False
    return abs(pred_val - gt_val) < 1e-6


def _is_simple_numeric_or_unit(gt: str) -> bool:
    if not gt:
        return False
    if _contains_latex(gt):
        return False
    numbers = _extract_numeric_values(gt)
    return len(numbers) == 1


def _parse_numeric_sequence_gt(gt: str) -> Optional[list[float]]:
    if not gt:
        return None
    if re.search(r"[A-Za-z]", gt):
        return None
    try:
        parsed = ast.literal_eval(gt)
        if isinstance(parsed, (list, tuple)) and parsed:
            values: list[float] = []
            for item in parsed:
                val = _parse_numeric_value(str(item))
                if val is None:
                    return None
                values.append(val)
            return values
    except Exception:
        pass
    values = _extract_numeric_values(gt)
    if len(values) >= 2:
        return values
    return None


def _parse_json_list(gt: str) -> Optional[list[Any]]:
    if not gt:
        return None
    s = gt.strip()
    if not (s.startswith("[") and s.endswith("]")):
        return None
    try:
        parsed = json.loads(s)
    except Exception:
        return None
    if isinstance(parsed, list):
        return parsed
    return None


def _normalize_index_list(items: Any) -> Optional[list[int]]:
    if not _is_non_string_sequence(items):
        return None
    out: list[int] = []
    for item in list(items):
        if isinstance(item, bool):
            out.append(int(item))
        elif isinstance(item, Integral):
            out.append(int(item))
        elif isinstance(item, float) and item.is_integer():
            out.append(int(item))
        else:
            return None
    return out


def _parse_index_list_text(text: str) -> Optional[list[int]]:
    if not text:
        return None
    parsed: Any = None
    try:
        parsed = json.loads(text)
    except Exception:
        parsed = None
    if parsed is None:
        try:
            parsed = ast.literal_eval(text)
        except Exception:
            parsed = None
    if isinstance(parsed, (list, tuple, set)):
        return _normalize_index_list(parsed)

    matches = _INT_RE.findall(text)
    if not matches:
        return None
    try:
        return [int(m) for m in matches]
    except ValueError:
        return None


def _index_list_similarity(pred_list: list[int], gt_list: list[int], mode: str = "exact") -> float:
    pred_set = set(int(v) for v in pred_list)
    gt_set = set(int(v) for v in gt_list)

    if mode == "exact":
        return 1.0 if [int(v) for v in pred_list] == [int(v) for v in gt_list] else 0.0

    if not pred_set and not gt_set:
        return 1.0

    if mode == "f1":
        denom = len(pred_set) + len(gt_set)
        if denom == 0:
            return 1.0
        return 2 * len(pred_set & gt_set) / denom

    union = pred_set | gt_set
    if not union:
        return 1.0
    return len(pred_set & gt_set) / len(union)


def _score_index_list(candidates: list[str], gt_list: list[int], mode: str = "exact") -> Optional[float]:
    best: Optional[float] = None
    for text in candidates:
        pred_list = _parse_index_list_text(text)
        if pred_list is None:
            continue
        score = _index_list_similarity(pred_list, gt_list, mode=mode)
        if best is None or score > best:
            best = score
    return best


def _parse_choice_list(items: list[Any]) -> Optional[list[str]]:
    letters: list[str] = []
    for item in items:
        s = str(item).strip().upper()
        if len(s) != 1 or s not in _CHOICE_LETTERS:
            return None
        letters.append(s)
    return letters if letters else None


def _parse_numeric_list(items: list[Any]) -> Optional[list[float]]:
    values: list[float] = []
    for item in items:
        val = _parse_numeric_value(str(item))
        if val is None:
            return None
        values.append(val)
    return values if values else None


def _match_choice(candidates: list[str], expected_letters: list[str]) -> bool:
    expected_set = sorted(set(expected_letters))
    for text in candidates:
        letters = _extract_choice_letters(text)
        if not letters:
            continue
        if len(expected_set) == 1:
            if letters[-1] == expected_set[0]:
                return True
        else:
            if sorted(set(letters)) == expected_set:
                return True
    return False


def _match_yes_no(candidates: list[str], expected: str) -> bool:
    for text in candidates:
        value = _extract_yes_no(text)
        if value == expected:
            return True
    return False


def _match_numeric(candidates: list[str], gt: str) -> bool:
    gt_values = _extract_numeric_values(gt)
    if not gt_values:
        return False
    gt_val = gt_values[0]
    for text in candidates:
        for value in _extract_numeric_values(text):
            if abs(value - gt_val) < 1e-6:
                return True
    return False


def _match_numeric_sequence(candidates: list[str], gt_values: list[float]) -> bool:
    if not gt_values:
        return False
    for text in candidates:
        values = _extract_numeric_values(text)
        if len(values) < len(gt_values):
            continue
        tail = values[-len(gt_values) :]
        if len(tail) == len(gt_values) and all(abs(a - b) < 1e-6 for a, b in zip(tail, gt_values)):
            return True
    return False


def _format_reward(response: str) -> float:
    pattern = re.compile(r".*\\boxed\\{.*\\}.*", re.DOTALL)
    return 1.0 if re.fullmatch(pattern, response) else 0.0


def _grid_accuracy(response: str, ground_truth_grid: np.ndarray) -> float:
    answer = extract_boxed_content(response)
    response_grid = _parse_response_grid(answer)

    if response_grid is None:
        return -1.0

    if response_grid.shape != ground_truth_grid.shape:
        return -1.0

    matches = int(np.count_nonzero(response_grid == ground_truth_grid))
    total = ground_truth_grid.size
    return 2 * ((matches / total) - 0.5)


def _score_non_grid(response: str, ground_truth: Any) -> float:
    answer = extract_boxed_content(response)
    gt_str = str(ground_truth).strip() if ground_truth is not None else ""

    candidates: list[str] = []
    if answer:
        candidates.append(answer)
    if answer != response:
        candidates.append(response)
    if not candidates:
        candidates = [response]

    def _match_single_gt(gt_value: Any) -> bool:
        gt_text = str(gt_value).strip() if gt_value is not None else ""
        if not gt_text:
            return False

        # Some datasets store answers as "(A) text". Accept either the option
        # letter or the text payload as correct.
        prefixed_choice = _split_prefixed_choice_answer(gt_text)
        if prefixed_choice is not None:
            expected_letter, remainder = prefixed_choice
            if _match_choice(candidates, [expected_letter]):
                return True
            if remainder and _match_single_gt(remainder):
                return True

        choice_letters = _parse_choice_ground_truth(gt_text)
        if choice_letters and _match_choice(candidates, choice_letters):
            return True
        seq = _parse_numeric_sequence_gt(gt_text)
        if seq is not None:
            return _match_numeric_sequence(candidates, seq)
        # Prefer numeric matching for scalar numeric ground truths (e.g., "0"/"1")
        # before falling back to yes/no normalization. This keeps count tasks
        # (like prism_dev) from being mis-scored as boolean QA.
        if _is_simple_numeric_or_unit(gt_text):
            if _match_numeric(candidates, gt_text):
                return True
        yes_no = _normalize_yes_no(gt_text)
        if yes_no:
            return _match_yes_no(candidates, yes_no)
        if _contains_latex(gt_text):
            return any(grade_answer(cand, gt_text) for cand in candidates)
        return any(grade_answer(cand, gt_text) for cand in candidates)

    if not gt_str:
        return 0.0

    gt_list: Optional[list[Any]] = None
    if isinstance(ground_truth, (list, tuple)):
        gt_list = list(ground_truth)
    else:
        gt_list = _parse_json_list(gt_str)

    if gt_list is not None:
        index_list = _normalize_index_list(gt_list)
        if index_list is not None:
            score = _score_index_list(candidates, index_list, mode="exact")
            if score is not None:
                return score
        choice_letters = _parse_choice_list(gt_list)
        if choice_letters:
            return 1.0 if _match_choice(candidates, choice_letters) else 0.0
        numeric_list = _parse_numeric_list(gt_list)
        if numeric_list is not None and len(numeric_list) > 1:
            return 1.0 if _match_numeric_sequence(candidates, numeric_list) else 0.0
        for item in gt_list:
            if _match_single_gt(item):
                return 1.0
        return 0.0

    return 1.0 if _match_single_gt(ground_truth) else 0.0


def compute_val_reward(
    data: DataProto,
    tokenizer: PreTrainedTokenizer,
    dataset_name: str,
    skip_special_tokens: bool = True,
    return_details: bool = False,
) -> (
    tuple[torch.Tensor, dict[str, list[float]]]
    | tuple[torch.Tensor, dict[str, list[float]], list[dict[str, Any]]]
):
    reward_tensor = torch.zeros_like(data.batch["responses"], dtype=torch.float32)
    reward_metrics: dict[str, list[float]] = defaultdict(list)
    reward_details: list[dict[str, Any]] = []

    response_ids = data.batch["responses"]
    if "response_mask" in data.batch.keys():
        response_mask = data.batch["response_mask"]
    elif "attention_mask" in data.batch.keys():
        response_mask = data.batch["attention_mask"][:, -response_ids.size(1) :]
    else:
        response_mask = torch.ones_like(response_ids, dtype=torch.long)
    response_length = torch.sum(response_mask, dim=-1)

    for i in range(len(data)):
        cur_length = int(response_length[i].item())
        valid_response_ids = response_ids[i][:cur_length]
        response_str = tokenizer.decode(valid_response_ids, skip_special_tokens=skip_special_tokens)
        prompt_str = tokenizer.decode(data.batch["prompts"][i], skip_special_tokens=skip_special_tokens)

        ground_truth = data.non_tensor_batch["ground_truth"][i]
        parser_family = data.non_tensor_batch["parser_family"][i] if "parser_family" in data.non_tensor_batch else None
        metadata = data.non_tensor_batch["metadata"][i] if "metadata" in data.non_tensor_batch else None
        extra_info = data.non_tensor_batch["extra_info"][i] if "extra_info" in data.non_tensor_batch else None
        image_sizes = data.non_tensor_batch["image_sizes"][i] if "image_sizes" in data.non_tensor_batch else None
        if image_sizes is None and isinstance(extra_info, dict):
            image_sizes = extra_info.get("image_sizes") or extra_info.get("image_size")
        reward_input = {
            "ground_truth": ground_truth,
            **{
                key: data.non_tensor_batch[key][i]
                for key in ("answer_gt", "annotation_gt", "reward_contract")
                if key in data.non_tensor_batch
            },
        }
        answer_reward: float | None = None
        annotation_reward: float | None = None
        if is_trace_reward_input(reward_input):
            trace_score = score_trace_response(
                response=response_str,
                answer_gt=reward_input["answer_gt"],
                annotation_gt=reward_input["annotation_gt"],
                reward_contract=reward_input["reward_contract"],
                image_sizes=image_sizes,
                metadata=metadata,
                extra_info=extra_info,
                trace_reward_mode="answer",
            )
            overall = float(trace_score["overall"])
            format_score = float(trace_score.get("format", 0.0))
            answer_reward = float(trace_score.get("answer_reward", 0.0))
            annotation_reward = float(trace_score.get("annotation_reward", 0.0))
            hit = 1.0 if answer_reward >= 0.999999 else 0.0
            extracted = bool(trace_score.get("answer_parse_ok", 0.0) or trace_score.get("annotation_parse_ok", 0.0))
            extracted_answer = trace_score.get("answer")
            parser_output = trace_score
        else:
            accuracy, extracted, extracted_answer, parser_output = score_external_response(
                response=response_str,
                ground_truth=ground_truth,
                prompt_text=prompt_str,
                parser_family=parser_family,
                metadata=metadata,
            )
            hit = 1.0 if accuracy > 0.5 else 0.0
            format_score = _format_reward(response_str)
            overall = accuracy

        reward_tensor[i, cur_length - 1] = overall
        reward_metrics["answer_reward"].append(answer_reward)
        reward_metrics["annotation_reward"].append(annotation_reward)
        reward_metrics["overall"].append(overall)
        reward_metrics["format"].append(format_score)
        reward_metrics["accuracy_on_total"].append(hit)
        reward_metrics["extracted"].append(1.0 if extracted else 0.0)
        reward_metrics["hit"].append(hit)
        if extracted:
            # extracted-only accuracy (hit / extracted)
            reward_metrics["accuracy"].append(hit)
        else:
            # Keep validation metric vectors sample-aligned; the aggregation code
            # ignores None values for extracted-only metrics.
            reward_metrics["accuracy"].append(None)

        if return_details:
            reward_details.append(
                {
                    "dataset_name": dataset_name,
                    "overall": float(overall),
                    "format": float(format_score),
                    "hit": float(hit),
                    "extracted": bool(extracted),
                    "extracted_answer": extracted_answer,
                    "parser_output": parser_output,
                    "parser_family": parser_family,
                    "metadata": metadata,
                    "generated_tokens": cur_length,
                }
            )

    if return_details:
        return reward_tensor, reward_metrics, reward_details
    return reward_tensor, reward_metrics

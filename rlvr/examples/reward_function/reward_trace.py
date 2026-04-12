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

import ast
import json
import os
import re
import socket
from datetime import datetime, timezone
from collections.abc import Sequence
from numbers import Integral, Real
from typing import Any

import numpy as np
from mathruler.grader import extract_boxed_content, grade_answer
from verl.utils.local_strict_eval import strict_score_response
from verl.utils.trace_reward import is_trace_reward_input, score_trace_response

try:
    from scipy.optimize import linear_sum_assignment
except Exception:  # pragma: no cover - scipy is expected, keep a fallback.
    linear_sum_assignment = None


REWARD_NAME = "reward_trace"
REWARD_TYPE = "batch"

_INT_RE = re.compile(r"[-+]?\d+")
_CODE_BLOCK_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)
_ANSWER_TAG_RE = re.compile(r"<answer>(.*?)</answer>", re.DOTALL | re.IGNORECASE)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _truncate_text(value: str, max_chars: int = 1200) -> str:
    if len(value) <= max_chars:
        return value
    return value[:max_chars] + "...<truncated>"


def _append_jsonl_records(path: str, records: list[dict[str, Any]]) -> None:
    if not records:
        return
    output_path = os.path.abspath(path)
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    payload = "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records).encode("utf-8")
    fd = os.open(output_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(fd, payload)
    finally:
        os.close(fd)


def _is_non_string_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))


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


def _coerce_int_list(sequence_value: Any) -> list[int] | None:
    if not _is_non_string_sequence(sequence_value):
        return None
    items = list(sequence_value)
    out: list[int] = []
    for item in items:
        if isinstance(item, bool):
            out.append(int(item))
        elif isinstance(item, Integral):
            out.append(int(item))
        elif isinstance(item, float) and item.is_integer():
            out.append(int(item))
        else:
            return None
    return out


def _to_scalar_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, Integral):
        return int(value)
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _parse_index_list_text(text: str) -> list[int] | None:
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
        except (SyntaxError, ValueError, TypeError):
            parsed = None

    if isinstance(parsed, (list, tuple, set)):
        return _coerce_int_list(parsed)

    matches = _INT_RE.findall(text)
    if not matches:
        return None

    try:
        return [int(m) for m in matches]
    except ValueError:
        return None


def _parse_scalar_int_text(text: str) -> int | None:
    if not text:
        return None

    parsed = _parse_json_like(text)
    scalar = _to_scalar_int(parsed)
    if scalar is not None:
        return scalar

    matches = _INT_RE.findall(text)
    if not matches:
        return None
    try:
        return int(matches[0])
    except ValueError:
        return None


def _to_numpy_grid(value: Any) -> np.ndarray | None:
    if isinstance(value, str):
        try:
            # Try to turn string representations (e.g. "[[1,0],[0,1]]") into Python objects.
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


def _to_index_list(value: Any) -> list[int] | None:
    if isinstance(value, str):
        return _parse_index_list_text(value)

    if isinstance(value, np.ndarray):
        if value.ndim != 1:
            return None
        if not np.isfinite(value).all():
            return None
        if not np.all(np.equal(value, np.round(value))):
            return None
        return [int(v) for v in value.tolist()]

    return _coerce_int_list(value)


def _parse_response_grid(answer: str | None) -> np.ndarray | None:
    if not answer:
        return None

    try:
        parsed = ast.literal_eval(answer)
    except (SyntaxError, ValueError, TypeError):
        # Common failure: a set-like outer brace containing lists (unhashable).
        # Try a softer parse by normalizing braces to brackets.
        normalized = answer.replace("{", "[").replace("}", "]")
        try:
            parsed = ast.literal_eval(normalized)
        except (SyntaxError, ValueError, TypeError):
            return None

    return _to_numpy_grid(parsed)


def format_reward(response: str) -> float:
    pattern = re.compile(r".*\\boxed\{.*\}.*", re.DOTALL)
    has_boxed_answer = re.fullmatch(pattern, response)
    return 1.0 if has_boxed_answer else 0.0


def _grid_accuracy_reward(response: str, ground_truth_grid: np.ndarray) -> float:
    answer = extract_boxed_content(response)
    response_grid = _parse_response_grid(answer)

    if response_grid is None:
        return 0.0

    if response_grid.shape != ground_truth_grid.shape:
        return 0.0

    matches = int(np.count_nonzero(response_grid == ground_truth_grid))
    total = ground_truth_grid.size

    return matches / total


def _index_list_similarity(pred_list: list[int], gt_list: list[int], mode: str) -> float:
    pred_set = set(int(v) for v in pred_list)
    gt_set = set(int(v) for v in gt_list)

    if mode == "exact":
        return 1.0 if pred_set == gt_set else 0.0

    if not pred_set and not gt_set:
        return 1.0

    if mode == "jaccard":
        union = pred_set | gt_set
        if not union:
            return 1.0
        return len(pred_set & gt_set) / len(union)

    if mode == "f1":
        denom = len(pred_set) + len(gt_set)
        if denom == 0:
            return 1.0
        return 2 * len(pred_set & gt_set) / denom

    raise ValueError(f"Unsupported list_reward_mode: {mode}")


def _index_list_accuracy_reward(response: str, ground_truth_list: list[int], list_reward_mode: str) -> float:
    answer = extract_boxed_content(response)
    pred_list = _parse_index_list_text(answer)
    if pred_list is None:
        return 0.0
    return _index_list_similarity(pred_list, ground_truth_list, list_reward_mode)


def accuracy_reward(response: str, ground_truth: Any, list_reward_mode: str = "exact") -> float:
    score, _, _, _ = strict_score_response(
        response=response,
        ground_truth=ground_truth,
        list_reward_mode=list_reward_mode,
    )
    return float(score)


def _parse_json_like(value: Any) -> Any | None:
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except Exception:
            try:
                return ast.literal_eval(text)
            except (SyntaxError, ValueError, TypeError):
                return None
    return value


def _to_non_negative_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, Integral):
        parsed = int(value)
    elif isinstance(value, float) and value.is_integer():
        parsed = int(value)
    else:
        return None
    if parsed < 0:
        return None
    return parsed


def _to_bbox(box: Any) -> list[float] | None:
    if not _is_non_string_sequence(box):
        return None

    values = list(box)
    if len(values) != 4:
        return None

    coords: list[float] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, Real):
            return None
        coord = float(value)
        if not np.isfinite(coord):
            return None
        coords.append(coord)

    x1, y1, x2, y2 = coords
    left, right = sorted((x1, x2))
    top, bottom = sorted((y1, y2))
    return [left, top, right, bottom]


def _to_bbox_list(value: Any) -> list[list[float]] | None:
    if not _is_non_string_sequence(value):
        return None

    out: list[list[float]] = []
    for raw_box in list(value):
        box = _to_bbox(raw_box)
        if box is None:
            return None
        out.append(box)
    return out


def _parse_bbox_payload(value: Any, require_count: bool) -> dict[str, Any] | None:
    parsed = _parse_json_like(value)
    if not isinstance(parsed, dict):
        return None

    if "bboxes" not in parsed:
        return None
    boxes = _to_bbox_list(parsed.get("bboxes"))
    if boxes is None:
        return None

    count: int | None = None
    if "count" in parsed:
        count = _to_non_negative_int(parsed.get("count"))
        if count is None:
            return None
    elif require_count:
        return None

    if count is None:
        count = len(boxes)

    return {"count": count, "bboxes": boxes}


def _extract_brace_objects(text: str) -> list[str]:
    objects: list[str] = []
    depth = 0
    start_index: int | None = None
    in_string = False
    escaped = False

    for i, char in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
            continue

        if char == "{":
            if depth == 0:
                start_index = i
            depth += 1
            continue

        if char == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start_index is not None:
                objects.append(text[start_index : i + 1])
                start_index = None

    return objects


def _collect_bbox_candidates(response: str) -> list[str]:
    candidates: list[str] = []

    boxed = extract_boxed_content(response)
    if boxed:
        candidates.append(boxed.strip())

    for match in _ANSWER_TAG_RE.findall(response):
        if match.strip():
            candidates.append(match.strip())

    for match in _CODE_BLOCK_RE.findall(response):
        if match.strip():
            candidates.append(match.strip())

    for match in _extract_brace_objects(response):
        if match.strip():
            candidates.append(match.strip())

    if response.strip():
        candidates.append(response.strip())

    deduped: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        deduped.append(candidate)

    return deduped


def _parse_bbox_response(response: str) -> dict[str, Any] | None:
    for candidate in reversed(_collect_bbox_candidates(response)):
        payload = _parse_bbox_payload(candidate, require_count=True)
        if payload is not None:
            return payload
    return None


def _bbox_iou(box_a: list[float], box_b: list[float]) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b

    inter_w = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    inter_h = max(0.0, min(ay2, by2) - max(ay1, by1))
    inter_area = inter_w * inter_h

    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter_area
    if union <= 0.0:
        return 0.0

    return inter_area / union


def _greedy_assignment(iou_matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if iou_matrix.size == 0:
        return np.array([], dtype=np.int64), np.array([], dtype=np.int64)

    remaining_rows = set(range(iou_matrix.shape[0]))
    remaining_cols = set(range(iou_matrix.shape[1]))
    selected_rows: list[int] = []
    selected_cols: list[int] = []

    while remaining_rows and remaining_cols:
        best_pair: tuple[int, int] | None = None
        best_iou = -1.0
        for row in remaining_rows:
            for col in remaining_cols:
                iou = float(iou_matrix[row, col])
                if iou > best_iou:
                    best_iou = iou
                    best_pair = (row, col)

        if best_pair is None:
            break

        row, col = best_pair
        selected_rows.append(row)
        selected_cols.append(col)
        remaining_rows.remove(row)
        remaining_cols.remove(col)

    return np.array(selected_rows, dtype=np.int64), np.array(selected_cols, dtype=np.int64)


def _assigned_match_ious(pred_boxes: list[list[float]], gt_boxes: list[list[float]]) -> list[float]:
    if not pred_boxes or not gt_boxes:
        return []

    iou_matrix = np.zeros((len(pred_boxes), len(gt_boxes)), dtype=np.float32)
    for row, pred_box in enumerate(pred_boxes):
        for col, gt_box in enumerate(gt_boxes):
            iou_matrix[row, col] = _bbox_iou(pred_box, gt_box)

    if linear_sum_assignment is None:
        row_ind, col_ind = _greedy_assignment(iou_matrix)
    else:
        row_ind, col_ind = linear_sum_assignment(-iou_matrix)

    return [float(iou_matrix[row, col]) for row, col in zip(row_ind, col_ind)]


def _bbox_match_stats(
    pred_boxes: list[list[float]],
    gt_boxes: list[list[float]],
    iou_threshold: float,
    bbox_set_mode: str,
) -> tuple[float, float, int, float]:
    bbox_set_mode = (bbox_set_mode or "thresholded").lower()
    if not pred_boxes and not gt_boxes:
        return 1.0, 0.0, 0, 0.0

    assigned_ious = _assigned_match_ious(pred_boxes, gt_boxes)
    if bbox_set_mode == "soft_iou_mass":
        # Dense location signal: sum assigned IoUs normalized by max(|P|, |G|).
        # This rewards both matching more objects and improving localization quality.
        normalizer = max(len(pred_boxes), len(gt_boxes), 1)
        iou_mass = float(sum(assigned_ious))
        r_set = iou_mass / normalizer
        positive_ious = [iou for iou in assigned_ious if iou > 0.0]
        matched_count = len(positive_ious)
        matched_iou_mean = float(sum(positive_ious) / matched_count) if matched_count > 0 else 0.0
        r_iou = matched_iou_mean
        return r_set, r_iou, matched_count, matched_iou_mean

    if bbox_set_mode != "thresholded":
        raise ValueError(
            f"Unsupported bbox_set_mode: {bbox_set_mode}. "
            "Expected one of {'thresholded', 'soft_iou_mass'}."
        )

    matched_ious = [iou for iou in assigned_ious if iou >= iou_threshold]
    matched_count = len(matched_ious)

    union_size = len(pred_boxes) + len(gt_boxes) - matched_count
    r_set = 1.0 if union_size <= 0 else (matched_count / union_size)

    if matched_count == 0:
        return r_set, 0.0, 0, 0.0

    matched_iou_mean = float(sum(matched_ious) / matched_count)
    denom = max(1e-8, 1.0 - iou_threshold)
    normalized_ious = [max(0.0, min(1.0, (iou - iou_threshold) / denom)) for iou in matched_ious]
    r_iou = float(sum(normalized_ious) / matched_count)
    return r_set, r_iou, matched_count, matched_iou_mean


def _bbox_count_signal(pred_count: int, gt_count: int, mode: str) -> float:
    mode = (mode or "soft").lower()
    if mode == "hard":
        return 1.0 if pred_count == gt_count else 0.0
    if mode == "soft":
        return float(np.exp(-abs(pred_count - gt_count) / 2.0))
    raise ValueError(f"Unsupported bbox_r_cnt_mode: {mode}")


def _bbox_count_exact_reward(pred_count: int, gt_count: int) -> float:
    return 1.0 if pred_count == gt_count else 0.0


def _bbox_consistency_factor(pred_count_field: int, pred_boxes: list[list[float]], factor: float) -> tuple[float, float]:
    consistency_ok = 1.0 if pred_count_field == len(pred_boxes) else 0.0
    cons_factor = 1.0 if consistency_ok == 1.0 else factor
    return consistency_ok, cons_factor


def _bbox_base_reward(
    pred_boxes: list[list[float]],
    gt_boxes: list[list[float]],
    iou_threshold: float,
    r_cnt_mode: str,
    bbox_set_mode: str,
    gate_set_lambda: float,
) -> tuple[float, float, float, float, int, float]:
    r_set, r_iou, matched_count, matched_iou_mean = _bbox_match_stats(
        pred_boxes=pred_boxes,
        gt_boxes=gt_boxes,
        iou_threshold=iou_threshold,
        bbox_set_mode=bbox_set_mode,
    )
    r_cnt = _bbox_count_signal(pred_count=len(pred_boxes), gt_count=len(gt_boxes), mode=r_cnt_mode)
    # Blend a count/consistency gate baseline with set overlap quality.
    # gate_set_lambda=0 -> pure gate reward; gate_set_lambda=1 -> pure gate*r_set.
    base_reward = r_cnt * ((1.0 - gate_set_lambda) + gate_set_lambda * r_set)
    return base_reward, r_cnt, r_set, r_iou, matched_count, matched_iou_mean


def _bbox_accuracy_reward(
    response: str,
    ground_truth_payload: dict[str, Any],
    iou_threshold: float,
    consistency_factor: float,
    r_cnt_mode: str,
    bbox_set_mode: str,
    gate_set_lambda: float,
) -> dict[str, float]:
    pred_payload = _parse_bbox_response(response)
    if pred_payload is None:
        return {
            "overall": 0.0,
            "format": 0.0,
            "accuracy": 0.0,
            "r_cnt": 0.0,
            "r_set": 0.0,
            "r_iou": 0.0,
            "r_ans": 0.0,
            "cons_factor": 0.0,
            "consistency_ok": 0.0,
            "count_err": float(len(ground_truth_payload["bboxes"])),
            "matched_count": 0.0,
            "matched_iou_mean": 0.0,
            "parse_ok": 0.0,
            "zero_reward": 1.0,
        }

    pred_boxes = pred_payload["bboxes"]
    gt_boxes = ground_truth_payload["bboxes"]
    pred_count_field = int(pred_payload["count"])
    pred_count = len(pred_boxes)
    gt_count = len(gt_boxes)

    base_reward, r_cnt, r_set, r_iou, matched_count, matched_iou_mean = _bbox_base_reward(
        pred_boxes=pred_boxes,
        gt_boxes=gt_boxes,
        iou_threshold=iou_threshold,
        r_cnt_mode=r_cnt_mode,
        bbox_set_mode=bbox_set_mode,
        gate_set_lambda=gate_set_lambda,
    )
    consistency_ok, cons_factor = _bbox_consistency_factor(pred_count_field, pred_boxes, consistency_factor)
    accuracy = max(0.0, base_reward * cons_factor)
    r_ans = _bbox_count_exact_reward(pred_count_field, gt_count)

    return {
        "overall": accuracy,
        "format": 1.0,
        "accuracy": accuracy,
        "r_cnt": float(r_cnt),
        "r_set": float(r_set),
        "r_iou": float(r_iou),
        "r_ans": float(r_ans),
        "cons_factor": float(cons_factor),
        "consistency_ok": float(consistency_ok),
        "count_err": float(abs(pred_count - gt_count)),
        "matched_count": float(matched_count),
        "matched_iou_mean": float(matched_iou_mean),
        "parse_ok": 1.0,
        "zero_reward": 1.0 if accuracy <= 0.0 else 0.0,
    }


def _resolve_dataset_mode(dataset_mode: str, ground_truth: Any) -> str:
    mode = (dataset_mode or "auto").lower()
    if mode not in {"auto", "integer", "bbox"}:
        raise ValueError(f"Unsupported dataset_mode: {dataset_mode}")

    if mode != "auto":
        return mode

    gt_bbox_payload = _parse_bbox_payload(ground_truth, require_count=True)
    return "bbox" if gt_bbox_payload is not None else "integer"


def compute_score(
    reward_inputs: list[dict[str, Any]],
    format_weight: float = 0.0,
    list_reward_mode: str = "exact",
    dataset_mode: str = "auto",
    trace_reward_mode: str = "answer_and_evidence",
    bbox_iou_threshold: float = 0.5,
    bbox_r_cnt_mode: str = "soft",
    bbox_set_mode: str = "thresholded",
    bbox_gate_set_lambda: float = 0.2,
    bbox_consistency_factor: float = 0.0,
    bbox_debug_log_enabled: bool = True,
    bbox_debug_log_path: str = "logs/bbox_debug.jsonl",
    bbox_debug_log_max_examples: int = 3,
    bbox_set_weight: float = 0.9,  # kept only for backward-compatible kwargs
    bbox_consistency_penalty_weight: float | None = None,  # legacy alias
) -> list[dict[str, float]]:
    bbox_r_cnt_mode = (bbox_r_cnt_mode or "soft").lower()
    if bbox_r_cnt_mode not in {"hard", "soft"}:
        raise ValueError(f"bbox_r_cnt_mode must be one of {{'hard', 'soft'}}, got {bbox_r_cnt_mode}")
    bbox_set_mode = (bbox_set_mode or "thresholded").lower()
    if bbox_set_mode not in {"thresholded", "soft_iou_mass"}:
        raise ValueError(
            f"bbox_set_mode must be one of {{'thresholded', 'soft_iou_mass'}}, got {bbox_set_mode}"
        )
    if bbox_gate_set_lambda < 0.0 or bbox_gate_set_lambda > 1.0:
        raise ValueError(f"bbox_gate_set_lambda must be in [0, 1], got {bbox_gate_set_lambda}")
    if bbox_iou_threshold < 0.0 or bbox_iou_threshold >= 1.0:
        raise ValueError(f"bbox_iou_threshold must be in [0, 1), got {bbox_iou_threshold}")
    if bbox_consistency_penalty_weight is not None:
        if bbox_consistency_penalty_weight < 0.0 or bbox_consistency_penalty_weight > 1.0:
            raise ValueError(
                "bbox_consistency_penalty_weight (legacy alias) must be in [0, 1], "
                f"got {bbox_consistency_penalty_weight}"
            )
        if bbox_consistency_factor == 0.0:
            # Legacy mapping: old subtractive 0.1 approximately maps to 0.9 multiplicative factor.
            bbox_consistency_factor = 1.0 - float(bbox_consistency_penalty_weight)
    if bbox_consistency_factor < 0.0 or bbox_consistency_factor > 1.0:
        raise ValueError(
            "bbox_consistency_factor must be in [0, 1], "
            f"got {bbox_consistency_factor}"
        )

    if bbox_set_weight < 0.0:
        raise ValueError(f"bbox_set_weight must be non-negative, got {bbox_set_weight}")

    scores = []
    bbox_total = 0
    bbox_parse_ok_sum = 0.0
    bbox_r_ans_sum = 0.0
    bbox_consistency_ok_sum = 0.0
    bbox_overall_sum = 0.0
    bbox_r_set_sum = 0.0
    bbox_r_iou_sum = 0.0
    bbox_matched_count_sum = 0.0
    bbox_zero_reward_sum = 0.0
    qualified_ans_consistent_count = 0.0
    qualified_ans_consistent_iou_sum = 0.0
    debug_iou_pos_samples: list[dict[str, Any]] = []
    debug_iou_zero_samples: list[dict[str, Any]] = []
    iou_pos_count = 0.0
    iou_zero_count = 0.0

    for reward_input in reward_inputs:
        prompt_text = str(reward_input.get("prompt", "") or "")
        response = re.sub(r"\s*(<|>|/)\s*", r"\1", reward_input["response"])
        ground_truth = reward_input["ground_truth"]

        if is_trace_reward_input(reward_input):
            trace_score = score_trace_response(
                response=response,
                answer_gt=reward_input["answer_gt"],
                evidence_gt=reward_input["evidence_gt"],
                reward_contract=reward_input["reward_contract"],
                bbox_iou_threshold=bbox_iou_threshold,
                trace_reward_mode=trace_reward_mode,
            )
            scores.append(trace_score)
            continue

        sample_mode = _resolve_dataset_mode(dataset_mode, ground_truth)

        if sample_mode == "bbox":
            ground_truth_payload = _parse_bbox_payload(ground_truth, require_count=True)
            if ground_truth_payload is None:
                scores.append(
                    {
                        "overall": 0.0,
                        "format": 0.0,
                        "accuracy": 0.0,
                        "r_cnt": 0.0,
                        "r_set": 0.0,
                        "r_iou": 0.0,
                        "r_ans": 0.0,
                        "cons_factor": 0.0,
                        "consistency_ok": 0.0,
                        "count_err": 0.0,
                        "matched_count": 0.0,
                        "matched_iou_mean": 0.0,
                        "parse_ok": 0.0,
                        "zero_reward": 1.0,
                        "gt_parse_fail": 1.0,
                    }
                )
            else:
                score = _bbox_accuracy_reward(
                    response=response,
                    ground_truth_payload=ground_truth_payload,
                    iou_threshold=bbox_iou_threshold,
                    consistency_factor=bbox_consistency_factor,
                    r_cnt_mode=bbox_r_cnt_mode,
                    bbox_set_mode=bbox_set_mode,
                    gate_set_lambda=bbox_gate_set_lambda,
                )
                score["gt_parse_fail"] = 0.0
                scores.append(score)

            bbox_score = scores[-1]
            bbox_total += 1
            bbox_parse_ok_sum += float(bbox_score.get("parse_ok", 0.0))
            bbox_r_ans_sum += float(bbox_score.get("r_ans", 0.0))
            bbox_consistency_ok_sum += float(bbox_score.get("consistency_ok", 0.0))
            bbox_overall_sum += float(bbox_score.get("overall", 0.0))
            bbox_r_set_sum += float(bbox_score.get("r_set", 0.0))
            bbox_r_iou_sum += float(bbox_score.get("r_iou", 0.0))
            bbox_matched_count_sum += float(bbox_score.get("matched_count", 0.0))
            bbox_zero_reward_sum += float(bbox_score.get("zero_reward", 0.0))

            matched_iou_mean = float(bbox_score.get("matched_iou_mean", 0.0))
            if float(bbox_score.get("r_ans", 0.0)) >= 0.5 and float(bbox_score.get("consistency_ok", 0.0)) >= 0.5:
                qualified_ans_consistent_count += 1.0
                qualified_ans_consistent_iou_sum += matched_iou_mean

            if ground_truth_payload is not None:
                gt_boxes = ground_truth_payload.get("bboxes", [])
                gt_count = len(gt_boxes)
                pred_payload = _parse_bbox_response(response)

                ans_ok = float(bbox_score.get("r_ans", 0.0)) >= 0.5
                cons_ok = float(bbox_score.get("consistency_ok", 0.0)) >= 0.5
                r_iou_value = float(bbox_score.get("r_iou", 0.0))
                if gt_count > 0 and ans_ok and cons_ok:
                    if r_iou_value > 0.01:
                        iou_pos_count += 1.0
                        if len(debug_iou_pos_samples) < max(0, int(bbox_debug_log_max_examples)):
                            debug_iou_pos_samples.append(
                                {
                                    "event_type": "ans_consistent_iou_gt_0p01",
                                    "prompt": _truncate_text(prompt_text),
                                    "response": _truncate_text(response),
                                    "ground_truth": ground_truth_payload,
                                    "prediction": pred_payload,
                                    "metrics": {
                                        "overall": float(bbox_score.get("overall", 0.0)),
                                        "r_set": float(bbox_score.get("r_set", 0.0)),
                                        "r_iou": r_iou_value,
                                        "matched_count": float(bbox_score.get("matched_count", 0.0)),
                                        "count_err": float(bbox_score.get("count_err", 0.0)),
                                    },
                                }
                            )
                    elif r_iou_value <= 1e-8:
                        iou_zero_count += 1.0
                        if len(debug_iou_zero_samples) < max(0, int(bbox_debug_log_max_examples)):
                            debug_iou_zero_samples.append(
                                {
                                    "event_type": "ans_consistent_iou_eq_0",
                                    "prompt": _truncate_text(prompt_text),
                                    "response": _truncate_text(response),
                                    "ground_truth": ground_truth_payload,
                                    "prediction": pred_payload,
                                    "metrics": {
                                        "overall": float(bbox_score.get("overall", 0.0)),
                                        "r_set": float(bbox_score.get("r_set", 0.0)),
                                        "r_iou": r_iou_value,
                                        "matched_count": float(bbox_score.get("matched_count", 0.0)),
                                        "count_err": float(bbox_score.get("count_err", 0.0)),
                                    },
                                }
                            )

            continue

        format_score = format_reward(response)
        accuracy_score, extracted, _, _ = strict_score_response(
            response=response,
            ground_truth=ground_truth,
            list_reward_mode=list_reward_mode,
        )
        scores.append(
            {
                "overall": (1 - format_weight) * accuracy_score + format_weight * format_score,
                "format": format_score,
                "accuracy": accuracy_score,
                "extracted": float(extracted),
                "hit": 1.0 if accuracy_score > 0.5 else 0.0,
            }
        )

    # Log a directly interpretable conditional IoU metric:
    # mean matched IoU among samples where the declared count is correct and consistent
    # with the predicted box list length.
    bbox_indices = [idx for idx, score in enumerate(scores) if "matched_iou_mean" in score]
    if bbox_indices:
        bbox_count = float(len(bbox_indices))
        conditional_mean = (
            float(qualified_ans_consistent_iou_sum / qualified_ans_consistent_count)
            if qualified_ans_consistent_count > 0
            else 0.0
        )
        conditional_rate = qualified_ans_consistent_count / bbox_count if bbox_count > 0 else 0.0
        for idx in bbox_indices:
            scores[idx]["matched_iou_mean_when_ans_consistent"] = conditional_mean
            scores[idx]["matched_iou_mean_when_ans_consistent_count"] = float(qualified_ans_consistent_count)
            scores[idx]["matched_iou_mean_when_ans_consistent_rate"] = float(conditional_rate)
            # Keep the log surface compact: expose only conditional IoU aggregates.
            scores[idx].pop("matched_iou_mean", None)

    if bbox_debug_log_enabled and bbox_total > 0:
        summary_record = {
            "event_type": "batch_summary",
            "ts_utc": _utc_now_iso(),
            "host": socket.gethostname(),
            "pid": os.getpid(),
            "total_bbox_samples": int(bbox_total),
            "parse_ok_rate": bbox_parse_ok_sum / bbox_total,
            "r_ans_rate": bbox_r_ans_sum / bbox_total,
            "consistency_ok_rate": bbox_consistency_ok_sum / bbox_total,
            "overall_mean": bbox_overall_sum / bbox_total,
            "r_set_mean": bbox_r_set_sum / bbox_total,
            "r_iou_mean": bbox_r_iou_sum / bbox_total,
            "matched_count_mean": bbox_matched_count_sum / bbox_total,
            "zero_reward_rate": bbox_zero_reward_sum / bbox_total,
            "matched_iou_mean_when_ans_consistent": (
                qualified_ans_consistent_iou_sum / qualified_ans_consistent_count
                if qualified_ans_consistent_count > 0
                else 0.0
            ),
            "matched_iou_mean_when_ans_consistent_count": float(qualified_ans_consistent_count),
            "matched_iou_mean_when_ans_consistent_rate": (
                qualified_ans_consistent_count / bbox_total if bbox_total > 0 else 0.0
            ),
            "ans_consistent_iou_gt_0p01_count": float(iou_pos_count),
            "ans_consistent_iou_gt_0p01_rate": (
                iou_pos_count / qualified_ans_consistent_count if qualified_ans_consistent_count > 0 else 0.0
            ),
            "ans_consistent_iou_eq_0_count": float(iou_zero_count),
            "ans_consistent_iou_eq_0_rate": (
                iou_zero_count / qualified_ans_consistent_count if qualified_ans_consistent_count > 0 else 0.0
            ),
            "cfg": {
                "bbox_iou_threshold": float(bbox_iou_threshold),
                "bbox_r_cnt_mode": bbox_r_cnt_mode,
                "bbox_set_mode": bbox_set_mode,
                "bbox_gate_set_lambda": float(bbox_gate_set_lambda),
                "bbox_consistency_factor": float(bbox_consistency_factor),
            },
        }
        debug_records = [summary_record]
        debug_records.extend(debug_iou_pos_samples)
        debug_records.extend(debug_iou_zero_samples)
        _append_jsonl_records(bbox_debug_log_path, debug_records)

    return scores

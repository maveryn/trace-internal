from __future__ import annotations

import ast
import json
import re
from collections.abc import Sequence
from numbers import Integral, Real
from typing import Any

import numpy as np

try:
    from scipy.optimize import linear_sum_assignment
except Exception:  # pragma: no cover
    linear_sum_assignment = None

from .local_strict_eval import strict_score_response
from .trace_mode import resolve_trace_reward_mode


_CODE_BLOCK_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)
_ANSWER_TAG_RE = re.compile(r"<answer>(.*?)</answer>", re.DOTALL | re.IGNORECASE)

_TRACE_ANSWER_SCORING_MODES = {"exact_json", "legacy_strict"}


def _is_non_string_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))


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
            except Exception:
                return None
    return value


def _extract_brace_objects(text: str) -> list[str]:
    objects: list[str] = []
    depth = 0
    start_index: int | None = None
    in_string = False
    escaped = False

    for index, char in enumerate(text):
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
                start_index = index
            depth += 1
            continue
        if char == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start_index is not None:
                objects.append(text[start_index : index + 1])
                start_index = None

    return objects


def _collect_json_candidates(response: str) -> list[str]:
    candidates: list[str] = []
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


def _normalize_trace_reward_mode(trace_reward_mode: str | None, *, trace_output_mode: str | None = None) -> str:
    return resolve_trace_reward_mode(trace_reward_mode, trace_output_mode=trace_output_mode)


def _normalize_trace_answer_scoring(trace_answer_scoring: str | None) -> str:
    normalized = str(trace_answer_scoring or "exact_json").strip().lower()
    aliases = {
        "exact": "exact_json",
        "exact_json": "exact_json",
        "legacy": "legacy_strict",
        "legacy_strict": "legacy_strict",
        "strict": "legacy_strict",
    }
    resolved = aliases.get(normalized)
    if resolved is None:
        raise ValueError(
            f"TRACE answer scoring must be one of {sorted(_TRACE_ANSWER_SCORING_MODES)!r}; "
            f"aliases {sorted(aliases)!r} are accepted. got {trace_answer_scoring!r}"
        )
    return resolved


def _required_trace_answer_keys(trace_reward_mode: str) -> set[str]:
    if trace_reward_mode == "answer":
        return {"answer"}
    return {"answer", "evidence"}


def _extract_trace_sections(response: str) -> tuple[str | None, str | None, bool]:
    if len(_ANSWER_TAG_RE.findall(response)) != 1:
        return None, None, False

    answer_block = _ANSWER_TAG_RE.search(response)
    if answer_block is None:
        return None, None, False
    answer_text = answer_block.group(1).strip()
    if not answer_text:
        return None, None, False
    return None, answer_text, True


def _parse_trace_answer_payload(answer_block: str) -> dict[str, Any] | None:
    parsed = _parse_json_like(answer_block)
    if isinstance(parsed, dict):
        return parsed
    for candidate in _collect_json_candidates(answer_block):
        parsed = _parse_json_like(candidate)
        if isinstance(parsed, dict):
            return parsed
    return None


def evaluate_trace_response_format(
    response: str,
    *,
    trace_reward_mode: str = "answer_and_evidence",
) -> dict[str, Any]:
    normalized_mode = _normalize_trace_reward_mode(trace_reward_mode)
    think_text, answer_block, structure_ok = _extract_trace_sections(response)
    if not structure_ok:
        return {
            "format": 0.0,
            "structure_ok": False,
            "json_ok": False,
            "schema_ok": False,
            "think_text": None,
            "answer_block": None,
            "payload": None,
        }

    payload = _parse_json_like(answer_block or "")
    if not isinstance(payload, dict):
        return {
            "format": 0.0,
            "structure_ok": True,
            "json_ok": False,
            "schema_ok": False,
            "think_text": think_text,
            "answer_block": answer_block,
            "payload": None,
        }

    schema_ok = set(payload.keys()) == _required_trace_answer_keys(normalized_mode)
    return {
        "format": 1.0 if schema_ok else 0.5,
        "structure_ok": True,
        "json_ok": True,
        "schema_ok": schema_ok,
        "think_text": think_text,
        "answer_block": answer_block,
        "payload": payload,
    }


def _normalize_scalar_number(value: Any) -> float | int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, Integral):
        return int(value)
    if isinstance(value, Real):
        as_float = float(value)
        if not np.isfinite(as_float):
            return None
        if as_float.is_integer():
            return int(as_float)
        return as_float
    return None


def _normalize_numeric_evidence(value: Any) -> list[float | int] | None:
    parsed = _parse_json_like(value)
    scalar = _normalize_scalar_number(parsed)
    if scalar is not None:
        return [scalar]
    if not _is_non_string_sequence(parsed):
        return None
    out: list[float | int] = []
    for item in list(parsed):
        normalized = _normalize_scalar_number(item)
        if normalized is None:
            return None
        out.append(normalized)
    return out


def _canonical_scalar_symbol(value: Any) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (Integral, Real)) and not isinstance(value, bool):
        normalized = _normalize_scalar_number(value)
        return str(normalized)
    if isinstance(value, str):
        return value.strip().lower()
    if value is Ellipsis:
        return "..."
    try:
        return json.dumps(_canonical_jsonable(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError):
        return str(value)


def _canonical_jsonable(value: Any) -> Any:
    if value is Ellipsis:
        return "..."
    if isinstance(value, bool):
        return value
    if isinstance(value, np.generic):
        return _canonical_jsonable(value.item())
    if isinstance(value, np.ndarray):
        return _canonical_jsonable(value.tolist())
    if isinstance(value, (Integral, Real)) and not isinstance(value, bool):
        return _normalize_scalar_number(value)
    if isinstance(value, str):
        return value.strip().lower()
    if isinstance(value, dict):
        items: list[tuple[str, Any]] = []
        for key, item_value in value.items():
            items.append((_canonical_scalar_symbol(key), _canonical_jsonable(item_value)))
        return {key: item_value for key, item_value in sorted(items, key=lambda kv: kv[0])}
    if isinstance(value, (set, frozenset)):
        normalized_items = [_canonical_jsonable(item) for item in value]
        return sorted(
            normalized_items,
            key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        )
    if _is_non_string_sequence(value):
        return [_canonical_jsonable(item) for item in list(value)]
    return value


def _serialize_candidate(value: Any) -> str:
    if isinstance(value, str):
        return value
    if value is Ellipsis:
        return "..."
    try:
        return json.dumps(
            _canonical_jsonable(value),
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )
    except (TypeError, ValueError):
        return str(value)


def _normalize_symbolic_set(value: Any, *, evidence_type: str) -> set[Any] | None:
    parsed = _parse_json_like(value)
    if parsed is None:
        return None
    if isinstance(parsed, (set, frozenset)):
        parsed = list(parsed)
    elif not _is_non_string_sequence(parsed):
        parsed = [parsed]

    normalized: set[Any] = set()
    if evidence_type == "edge_set":
        for item in list(parsed):
            if not _is_non_string_sequence(item):
                return None
            endpoints = list(item)
            if len(endpoints) != 2:
                return None
            normalized.add(tuple(sorted((_canonical_scalar_symbol(endpoints[0]), _canonical_scalar_symbol(endpoints[1])))))
        return normalized

    for item in list(parsed):
        normalized.add(_canonical_scalar_symbol(item))
    return normalized


def _normalize_coord_pair(value: Any) -> tuple[float | int, float | int] | None:
    if not _is_non_string_sequence(value):
        return None
    items = list(value)
    if len(items) != 2:
        return None
    x = _normalize_scalar_number(items[0])
    y = _normalize_scalar_number(items[1])
    if x is None or y is None:
        return None
    return (x, y)


def _normalize_sequence(value: Any, *, evidence_type: str) -> list[Any] | None:
    parsed = _parse_json_like(value)
    if not _is_non_string_sequence(parsed):
        return None
    items = list(parsed)
    normalized: list[Any] = []
    is_coord_sequence = evidence_type in {"grid_point_path", "point_path"}
    for item in items:
        if is_coord_sequence:
            coord = _normalize_coord_pair(item)
            if coord is None:
                return None
            normalized.append(coord)
        else:
            normalized.append(_canonical_scalar_symbol(item))
    return normalized


def _normalize_point_set(value: Any) -> set[tuple[float | int, float | int]] | None:
    parsed = _parse_json_like(value)
    single = _normalize_coord_pair(parsed)
    if single is not None:
        return {single}
    if not _is_non_string_sequence(parsed):
        return None
    normalized: set[tuple[float | int, float | int]] = set()
    for item in list(parsed):
        coord = _normalize_coord_pair(item)
        if coord is None:
            return None
        normalized.add(coord)
    return normalized


def _normalize_bbox(value: Any) -> list[float] | None:
    if not _is_non_string_sequence(value):
        return None
    items = list(value)
    if len(items) != 4:
        return None
    coords: list[float] = []
    for item in items:
        if isinstance(item, bool) or not isinstance(item, Real):
            return None
        coord = float(item)
        if not np.isfinite(coord):
            return None
        coords.append(coord)
    x0, y0, x1, y1 = coords
    left, right = sorted((x0, x1))
    top, bottom = sorted((y0, y1))
    if left == right or top == bottom:
        return None
    return [left, top, right, bottom]


def _normalize_bbox_set(value: Any) -> list[list[float]] | None:
    parsed = _parse_json_like(value)
    if parsed is None:
        return None
    single = _normalize_bbox(parsed)
    if single is not None:
        return [single]
    if isinstance(parsed, dict) and "bboxes" in parsed:
        parsed = parsed.get("bboxes")
    if not _is_non_string_sequence(parsed):
        return None
    out: list[list[float]] = []
    for item in list(parsed):
        bbox = _normalize_bbox(item)
        if bbox is None:
            return None
        out.append(bbox)
    return out


def _bbox_iou(box_a: list[float], box_b: list[float]) -> float:
    ax0, ay0, ax1, ay1 = box_a
    bx0, by0, bx1, by1 = box_b
    ix0 = max(ax0, bx0)
    iy0 = max(ay0, by0)
    ix1 = min(ax1, bx1)
    iy1 = min(ay1, by1)
    iw = max(0.0, ix1 - ix0)
    ih = max(0.0, iy1 - iy0)
    inter = iw * ih
    if inter <= 0.0:
        return 0.0
    area_a = max(0.0, ax1 - ax0) * max(0.0, ay1 - ay0)
    area_b = max(0.0, bx1 - bx0) * max(0.0, by1 - by0)
    union = area_a + area_b - inter
    if union <= 0.0:
        return 0.0
    return inter / union


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


def _score_bbox_set_iou(
    pred_boxes: list[list[float]],
    gt_boxes: list[list[float]],
    *,
    iou_threshold: float,
) -> tuple[float, int, float]:
    if not pred_boxes and not gt_boxes:
        return 1.0, 0, 0.0
    if not pred_boxes or not gt_boxes:
        return 0.0, 0, 0.0

    iou_matrix = np.zeros((len(pred_boxes), len(gt_boxes)), dtype=np.float32)
    for row, pred_box in enumerate(pred_boxes):
        for col, gt_box in enumerate(gt_boxes):
            iou_matrix[row, col] = _bbox_iou(pred_box, gt_box)

    if linear_sum_assignment is None:
        row_ind, col_ind = _greedy_assignment(iou_matrix)
    else:
        row_ind, col_ind = linear_sum_assignment(-iou_matrix)

    matched_ious: list[float] = []
    for row, col in zip(row_ind, col_ind):
        iou = float(iou_matrix[row, col])
        if iou >= iou_threshold:
            matched_ious.append(iou)
    if not matched_ious:
        return 0.0, 0, 0.0
    score = float(sum(matched_ious) / max(len(pred_boxes), len(gt_boxes), 1))
    mean_iou = float(sum(matched_ious) / len(matched_ious))
    return score, len(matched_ious), mean_iou


def _score_trace_answer(
    answer_value: Any,
    answer_gt: dict[str, Any],
    *,
    trace_answer_scoring: str = "exact_json",
) -> tuple[float, bool]:
    if not isinstance(answer_gt, dict) or "value" not in answer_gt:
        return 0.0, False
    normalized_scoring = _normalize_trace_answer_scoring(trace_answer_scoring)
    if normalized_scoring == "legacy_strict":
        answer_text = _serialize_candidate(answer_value)
        score, extracted, _, _ = strict_score_response(response=answer_text, ground_truth=answer_gt.get("value"))
        return float(score), bool(extracted)

    normalized_pred = _canonical_jsonable(_parse_json_like(answer_value))
    normalized_gt = _canonical_jsonable(answer_gt.get("value"))
    return (1.0 if normalized_pred == normalized_gt else 0.0), True


def _score_trace_evidence(
    evidence_value: Any,
    evidence_gt: dict[str, Any],
    reward_contract: dict[str, Any],
    *,
    bbox_iou_threshold: float,
) -> tuple[float, bool, dict[str, Any]]:
    if not isinstance(evidence_gt, dict) or "type" not in evidence_gt:
        return 0.0, False, {"reason": "missing_evidence_gt"}
    if not isinstance(reward_contract, dict):
        return 0.0, False, {"reason": "missing_reward_contract"}

    evidence_type = str(evidence_gt.get("type", "")).strip()
    evidence_gt_value = evidence_gt.get("value")
    evidence_contract = reward_contract.get("evidence") if isinstance(reward_contract.get("evidence"), dict) else {}
    evidence_contract_id = str(evidence_contract.get("id", "")).strip()

    if evidence_contract_id == "numeric_exact_v1":
        pred = _normalize_numeric_evidence(evidence_value)
        gt = _normalize_numeric_evidence(evidence_gt_value)
        if pred is None or gt is None:
            return 0.0, False, {"reason": "numeric_parse_failed"}
        return (1.0 if pred == gt else 0.0), True, {"pred_len": len(pred), "gt_len": len(gt)}

    if evidence_contract_id == "symbolic_set_exact_v1":
        pred = _normalize_symbolic_set(evidence_value, evidence_type=evidence_type)
        gt = _normalize_symbolic_set(evidence_gt_value, evidence_type=evidence_type)
        if pred is None or gt is None:
            return 0.0, False, {"reason": "symbolic_set_parse_failed"}
        return (1.0 if pred == gt else 0.0), True, {"pred_size": len(pred), "gt_size": len(gt)}

    if evidence_contract_id == "sequence_exact_v1":
        pred = _normalize_sequence(evidence_value, evidence_type=evidence_type)
        gt = _normalize_sequence(evidence_gt_value, evidence_type=evidence_type)
        if pred is None or gt is None:
            return 0.0, False, {"reason": "sequence_parse_failed"}
        return (1.0 if pred == gt else 0.0), True, {"pred_len": len(pred), "gt_len": len(gt)}

    if evidence_contract_id == "point_set_match_v1":
        pred = _normalize_point_set(evidence_value)
        gt = _normalize_point_set(evidence_gt_value)
        if pred is None or gt is None:
            return 0.0, False, {"reason": "point_set_parse_failed"}
        return (1.0 if pred == gt else 0.0), True, {"pred_size": len(pred), "gt_size": len(gt)}

    if evidence_contract_id == "bbox_set_iou_v1":
        pred = _normalize_bbox_set(evidence_value)
        gt = _normalize_bbox_set(evidence_gt_value)
        if pred is None or gt is None:
            return 0.0, False, {"reason": "bbox_parse_failed"}
        score, matched_count, matched_iou_mean = _score_bbox_set_iou(pred, gt, iou_threshold=bbox_iou_threshold)
        return score, True, {
            "pred_size": len(pred),
            "gt_size": len(gt),
            "matched_count": matched_count,
            "matched_iou_mean": matched_iou_mean,
        }

    return 0.0, False, {"reason": f"unsupported_evidence_contract:{evidence_contract_id}"}


def extract_trace_prediction(response: str) -> tuple[Any | None, Any | None, bool]:
    _, answer_block, structure_ok = _extract_trace_sections(response)
    if structure_ok and answer_block is not None:
        payload = _parse_trace_answer_payload(answer_block)
        if isinstance(payload, dict) and ("answer" in payload or "evidence" in payload):
            return payload.get("answer"), payload.get("evidence"), True
    for candidate in reversed(_collect_json_candidates(response)):
        parsed = _parse_json_like(candidate)
        if not isinstance(parsed, dict):
            continue
        if "answer" in parsed or "evidence" in parsed:
            return parsed.get("answer"), parsed.get("evidence"), True
    return None, None, False


def extract_trace_answer_for_scoring(response: str) -> str | None:
    answer_value, _, json_found = extract_trace_prediction(response)
    if not json_found or answer_value is None:
        return None
    return _serialize_candidate(answer_value)


def is_trace_reward_input(reward_input: dict[str, Any]) -> bool:
    return all(key in reward_input for key in ("answer_gt", "evidence_gt", "reward_contract"))


def score_trace_response(
    *,
    response: str,
    answer_gt: dict[str, Any],
    evidence_gt: dict[str, Any],
    reward_contract: dict[str, Any],
    bbox_iou_threshold: float = 0.5,
    answer_weight: float = 0.5,
    evidence_weight: float = 0.5,
    trace_reward_mode: str = "answer_and_evidence",
    trace_answer_scoring: str = "exact_json",
    format_weight: float = 0.1,
) -> dict[str, float]:
    if format_weight < 0.0 or format_weight > 1.0:
        raise ValueError(f"TRACE format_weight must be in [0, 1], got {format_weight}")

    normalized_mode = _normalize_trace_reward_mode(trace_reward_mode)
    normalized_answer_scoring = _normalize_trace_answer_scoring(trace_answer_scoring)
    format_details = evaluate_trace_response_format(response, trace_reward_mode=normalized_mode)
    payload = format_details.get("payload") if isinstance(format_details.get("payload"), dict) else None

    if payload is not None and ("answer" in payload or "evidence" in payload):
        answer_value = payload.get("answer")
        evidence_value = payload.get("evidence")
        json_found = True
    else:
        answer_value, evidence_value, json_found = extract_trace_prediction(response)

    if answer_value is None:
        answer_value = response

    answer_score, answer_parse_ok = _score_trace_answer(
        answer_value,
        answer_gt,
        trace_answer_scoring=normalized_answer_scoring,
    )
    evidence_score = 0.0
    evidence_parse_ok = False
    evidence_details: dict[str, Any] = {}
    if evidence_value is not None:
        evidence_score, evidence_parse_ok, evidence_details = _score_trace_evidence(
            evidence_value,
            evidence_gt,
            reward_contract,
            bbox_iou_threshold=bbox_iou_threshold,
        )

    total_weight = float(answer_weight + evidence_weight)
    if total_weight <= 0.0:
        raise ValueError("TRACE reward weights must sum to a positive value")
    normalized_answer_weight = float(answer_weight / total_weight)
    normalized_evidence_weight = float(evidence_weight / total_weight)
    if normalized_mode == "answer":
        raw_task_reward = float(answer_score)
    else:
        raw_task_reward = float(answer_score * (normalized_answer_weight + (normalized_evidence_weight * evidence_score)))

    # Match Vero-style reward composition: correctness and format are additive
    # components. Do not hard-gate correctness on format, because early policy
    # outputs often contain a recoverable answer before they learn the wrapper.
    effective_task_reward = raw_task_reward
    overall = float(((1.0 - format_weight) * effective_task_reward) + (format_weight * float(format_details["format"])))
    result = {
        "overall": overall,
        "format": float(format_details["format"]),
        "accuracy": float(answer_score),
        "answer_reward": float(answer_score),
        "evidence_reward": float(evidence_score),
        "task_reward_raw": float(raw_task_reward),
        "task_reward_gated": float(effective_task_reward),
        "format_weight": float(format_weight),
        "trace_reward_mode_answer": 1.0 if normalized_mode == "answer" else 0.0,
        "trace_reward_mode_answer_only": 1.0 if normalized_mode == "answer" else 0.0,
        "trace_reward_mode_answer_and_evidence": 1.0 if normalized_mode == "answer_and_evidence" else 0.0,
        "trace_answer_scoring_exact_json": 1.0 if normalized_answer_scoring == "exact_json" else 0.0,
        "trace_answer_scoring_legacy_strict": 1.0 if normalized_answer_scoring == "legacy_strict" else 0.0,
        "format_structure_ok": 1.0 if format_details["structure_ok"] else 0.0,
        "format_json_ok": 1.0 if format_details["json_ok"] else 0.0,
        "format_schema_ok": 1.0 if format_details["schema_ok"] else 0.0,
        "answer_parse_ok": 1.0 if answer_parse_ok else 0.0,
        "evidence_parse_ok": 1.0 if evidence_parse_ok else 0.0,
        "json_found": 1.0 if json_found else 0.0,
        # Keep zero_reward aligned with task correctness semantics. With
        # additive format reward, overall can be positive even when the answer
        # is wrong, so overall <= 0 no longer means "zero task reward".
        "zero_reward": 1.0 if effective_task_reward <= 0.0 else 0.0,
        "trace_reward": 1.0,
    }
    for key, value in evidence_details.items():
        if isinstance(value, (int, float)):
            result[f"evidence_{key}"] = float(value)
    return result


__all__ = [
    "evaluate_trace_response_format",
    "extract_trace_answer_for_scoring",
    "extract_trace_prediction",
    "is_trace_reward_input",
    "score_trace_response",
]

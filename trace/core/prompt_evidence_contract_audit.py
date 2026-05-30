"""Audit rendered prompts and public evidence contracts for TRACE tasks."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
import json
import math
import multiprocessing
from pathlib import Path
import re
import sys
from typing import Any

from PIL import Image as PILImage

from trace.core.evidence_sanitization import PUBLIC_IMAGE_EVIDENCE_TYPES, sanitize_trace_payload_for_public_evidence
from trace.core.review_overlays import render_evidence_overlay, resolve_overlay_evidence
from trace.core.seed import hash64
from trace.core.task_review_sampling import collect_query_id_samples
from trace.tasks import TASK_REGISTRY, create_task
from trace.tasks.registry import list_default_task_ids


_FORMAT_SECTION_RE = re.compile(
    r"\n(?:"
    r"Answer format:|Required answer format:|Final answer format:|Use this answer format:|"
    r"Evidence format:|Required evidence format:|Use this evidence format:|"
    r"Format for the \"answer\" field:|Format for the \"evidence\" field:|"
    r"Example JSON:"
    r")",
    flags=re.IGNORECASE,
)
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|\n+")
_WORD_RE = re.compile(r"\b[a-z0-9_'-]+\b", flags=re.IGNORECASE)
_POINT_NOTATION_RE = re.compile(r"\[\s*x\s*,\s*y\s*\]", flags=re.IGNORECASE)
_BBOX_NOTATION_RE = re.compile(
    r"\[\s*x0\s*,\s*y0\s*,\s*x1\s*,\s*y1\s*\]",
    flags=re.IGNORECASE,
)
_EVIDENCE_FORMAT_HEADER_RE = re.compile(
    r"(?:Evidence format:|Required evidence format:|Use this evidence format:|Format for the \"evidence\" field:)",
    flags=re.IGNORECASE,
)
_NEXT_FORMAT_HEADER_RE = re.compile(
    r"\n(?:"
    r"Answer format:|Required answer format:|Final answer format:|Use this answer format:|"
    r"Example JSON:|Format for the \"answer\" field:"
    r")",
    flags=re.IGNORECASE,
)
_NEGATIVE_EVIDENCE_FORMAT_RE = re.compile(
    r"\b(?:do not|don't|exclude|excluding|avoid|must not|should not|never)\b"
    r"|\bnot\s+(?:include|mark|box|use|return|select|provide)\b",
    flags=re.IGNORECASE,
)
_EXACT_JSON_KEYS_RE = re.compile(r'"evidence".*"answer"', flags=re.IGNORECASE | re.DOTALL)
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "be",
        "by",
        "for",
        "from",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "with",
    }
)
_PIXEL_EVIDENCE_TYPES = set(PUBLIC_IMAGE_EVIDENCE_TYPES)
_EVIDENCE_MODE = "answer_and_evidence"
_ANSWER_ONLY_MODE = "answer_only"


_EXPLICIT_VARIANT_PARAMS: dict[str, list[tuple[str, dict[str, Any]]]] = {
    "task_games__connect_four__move_count": [
        ("winning_move_count", {"query_id": "winning_move_count"}),
        ("safe_move_count", {"query_id": "safe_move_count"}),
    ],
}


def _issue(
    *,
    category: str,
    code: str,
    severity: str,
    message: str,
    mode: str = "",
    excerpt: str = "",
) -> dict[str, str]:
    return {
        "category": str(category),
        "code": str(code),
        "severity": str(severity),
        "mode": str(mode),
        "message": str(message),
        "excerpt": str(excerpt).strip(),
    }


def _word_count(text: str) -> int:
    return len(_WORD_RE.findall(str(text)))


def _semantic_body(text: str) -> str:
    match = _FORMAT_SECTION_RE.search(str(text))
    if match is None:
        return str(text).strip()
    return str(text)[: match.start()].strip()


def _sentence_tokens(sentence: str) -> list[str]:
    return [
        token.lower()
        for token in _WORD_RE.findall(str(sentence))
        if token.lower() not in _STOPWORDS
    ]


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in _SENTENCE_RE.split(str(text).strip()) if part.strip()]


def _token_jaccard(left: Sequence[str], right: Sequence[str]) -> float:
    left_set = set(left)
    right_set = set(right)
    if not left_set or not right_set:
        return 0.0
    return float(len(left_set & right_set)) / float(len(left_set | right_set))


def _find_redundancy_issues(prompt: str, *, mode: str) -> list[dict[str, str]]:
    body = _semantic_body(prompt)
    sentences = _sentences(body)
    issues: list[dict[str, str]] = []

    tokenized = [_sentence_tokens(sentence) for sentence in sentences]
    for index in range(1, len(sentences)):
        prev_tokens = tokenized[index - 1]
        curr_tokens = tokenized[index]
        if len(prev_tokens) < 4 or len(curr_tokens) < 4:
            continue
        overlap = _token_jaccard(prev_tokens, curr_tokens)
        exact_norm = " ".join(prev_tokens) == " ".join(curr_tokens)
        same_start = prev_tokens[:4] == curr_tokens[:4]
        if exact_norm or overlap >= 0.78 or (same_start and overlap >= 0.55):
            issues.append(
                _issue(
                    category="prompt_redundancy",
                    code="adjacent_sentence_overlap",
                    severity="warning",
                    mode=mode,
                    message=f"Adjacent prompt-body sentences have high token overlap ({overlap:.2f}).",
                    excerpt=f"{sentences[index - 1]} / {sentences[index]}",
                )
            )

    for index, tokens in enumerate(tokenized):
        if len(tokens) < 8:
            continue
        grams = Counter(tuple(tokens[pos : pos + 4]) for pos in range(0, max(0, len(tokens) - 3)))
        repeated = [" ".join(gram) for gram, count in grams.items() if count > 1]
        if repeated:
            issues.append(
                _issue(
                    category="prompt_redundancy",
                    code="repeated_phrase_in_sentence",
                    severity="info",
                    mode=mode,
                    message=f"Prompt-body sentence repeats phrase(s): {', '.join(repeated[:3])}.",
                    excerpt=sentences[index],
                )
            )

    answer_format_terms = len(re.findall(r"\b(answer format|final answer|json object|example json)\b", body, re.I))
    if answer_format_terms > 0:
        issues.append(
            _issue(
                category="prompt_redundancy",
                code="format_instruction_in_body",
                severity="info",
                mode=mode,
                message="Prompt body appears to include answer-format wording before the format section.",
                excerpt=body[:220],
            )
        )
    return issues


def _extract_example_json(prompt: str) -> tuple[dict[str, Any] | None, str]:
    match = re.search(r"Example JSON:\s*", str(prompt), flags=re.IGNORECASE)
    if match is None:
        return None, "missing Example JSON section"
    start = str(prompt).find("{", match.end())
    if start < 0:
        return None, "missing JSON object after Example JSON"
    try:
        obj, _end = json.JSONDecoder().raw_decode(str(prompt)[start:])
    except json.JSONDecodeError as exc:
        return None, f"invalid Example JSON: {exc.msg}"
    if not isinstance(obj, dict):
        return None, "Example JSON is not an object"
    return obj, ""


def _extract_evidence_format_section(prompt: str) -> str:
    match = _EVIDENCE_FORMAT_HEADER_RE.search(str(prompt))
    if match is None:
        return ""
    next_match = _NEXT_FORMAT_HEADER_RE.search(str(prompt), match.end())
    end = next_match.start() if next_match is not None else len(str(prompt))
    return str(prompt)[match.start() : end].strip()


def _as_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        parsed = float(value)
        if math.isfinite(parsed):
            return parsed
    return None


def _parse_point(value: Any) -> tuple[float, float] | None:
    if isinstance(value, (list, tuple)) and len(value) == 2:
        x = _as_number(value[0])
        y = _as_number(value[1])
        if x is not None and y is not None:
            return float(x), float(y)
    return None


def _parse_bbox(value: Any) -> tuple[float, float, float, float] | None:
    if isinstance(value, (list, tuple)) and len(value) == 4:
        parsed = [_as_number(item) for item in value]
        if all(item is not None for item in parsed):
            x0, y0, x1, y1 = (float(parsed[0]), float(parsed[1]), float(parsed[2]), float(parsed[3]))
            if x1 > x0 and y1 > y0:
                return x0, y0, x1, y1
    return None


def _validate_point(point: Any, *, image_size: tuple[int, int] | None, field: str) -> list[str]:
    parsed = _parse_point(point)
    if parsed is None:
        return [f"{field} is not a numeric [x, y] point"]
    if image_size is None:
        return []
    width, height = image_size
    x, y = parsed
    if not (0.0 <= x <= float(width) and 0.0 <= y <= float(height)):
        return [f"{field} point {list(parsed)} is outside image bounds {width}x{height}"]
    return []


def _validate_bbox(bbox: Any, *, image_size: tuple[int, int] | None, field: str) -> list[str]:
    parsed = _parse_bbox(bbox)
    if parsed is None:
        return [f"{field} is not a numeric positive-area [x0, y0, x1, y1] box"]
    if image_size is None:
        return []
    width, height = image_size
    x0, y0, x1, y1 = parsed
    if not (0.0 <= x0 <= float(width) and 0.0 <= x1 <= float(width) and 0.0 <= y0 <= float(height) and 0.0 <= y1 <= float(height)):
        return [f"{field} box {list(parsed)} is outside image bounds {width}x{height}"]
    return []


def _validate_evidence_value(
    evidence_type: str,
    value: Any,
    *,
    image_size: tuple[int, int] | None = None,
    field: str = "evidence",
) -> list[str]:
    kind = str(evidence_type)
    errors: list[str] = []
    if kind in {"bbox_sequence", "bbox_set"}:
        if not isinstance(value, list):
            return [f"{field} must be a list of bounding boxes"]
        for index, bbox in enumerate(value):
            errors.extend(_validate_bbox(bbox, image_size=image_size, field=f"{field}[{index}]"))
        return errors
    if kind == "keyed_bbox_map":
        if not isinstance(value, Mapping):
            return [f"{field} must be an object mapping string keys to bounding boxes"]
        for key, bbox in value.items():
            if not str(key).strip():
                errors.append(f"{field} has an empty key")
                continue
            errors.extend(_validate_bbox(bbox, image_size=image_size, field=f"{field}.{key}"))
        return errors
    if kind in {"point_sequence", "point_set"}:
        if not isinstance(value, list):
            return [f"{field} must be a list of points"]
        for index, point in enumerate(value):
            errors.extend(_validate_point(point, image_size=image_size, field=f"{field}[{index}]"))
        return errors
    if kind == "keyed_point_map":
        if not isinstance(value, Mapping):
            return [f"{field} must be an object mapping string keys to points"]
        for key, point in value.items():
            if not str(key).strip():
                errors.append(f"{field} has an empty key")
                continue
            errors.extend(_validate_point(point, image_size=image_size, field=f"{field}.{key}"))
        return errors
    if kind == "point_pair_set":
        if not isinstance(value, list):
            return [f"{field} must be a list of point pairs"]
        for pair_index, pair in enumerate(value):
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                errors.append(f"{field}[{pair_index}] is not a two-point pair")
                continue
            for endpoint_index, point in enumerate(pair):
                errors.extend(
                    _validate_point(
                        point,
                        image_size=image_size,
                        field=f"{field}[{pair_index}][{endpoint_index}]",
                    )
                )
        return errors
    return [f"{field} uses unsupported public pixel evidence type {kind!r}"]


def _audit_evidence_prompt(prompt: str, *, evidence_type: str, mode: str) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    prompt_text = str(prompt)
    lower = prompt_text.lower()

    if "evidence format:" not in lower and 'format for the "evidence" field:' not in lower:
        issues.append(
            _issue(
                category="evidence_prompt",
                code="missing_evidence_format_section",
                severity="error",
                mode=mode,
                message="Evidence prompt is missing a named evidence-format section.",
            )
        )
    if "example json:" not in lower:
        issues.append(
            _issue(
                category="evidence_prompt",
                code="missing_example_json",
                severity="error",
                mode=mode,
                message="Evidence prompt is missing an Example JSON section.",
            )
        )
    if _EXACT_JSON_KEYS_RE.search(prompt_text) is None:
        issues.append(
            _issue(
                category="evidence_prompt",
                code="missing_ordered_json_keys",
                severity="warning",
                mode=mode,
                message='Evidence prompt does not clearly show "evidence" before "answer".',
            )
        )
    evidence_format_section = _extract_evidence_format_section(prompt_text)
    negative_match = _NEGATIVE_EVIDENCE_FORMAT_RE.search(evidence_format_section)
    if negative_match is not None:
        issues.append(
            _issue(
                category="evidence_prompt",
                code="negative_evidence_format_instruction",
                severity="error",
                mode=mode,
                message=(
                    "Evidence-format prompt text must describe only the requested witness category/shape; "
                    "move exclusions and non-witness policy to task docs or trace metadata."
                ),
                excerpt=evidence_format_section[:260],
            )
        )

    if str(evidence_type) in {"bbox_sequence", "bbox_set", "keyed_bbox_map"} and _BBOX_NOTATION_RE.search(prompt_text) is None:
        issues.append(
            _issue(
                category="evidence_prompt",
                code="missing_bbox_notation",
                severity="warning",
                mode=mode,
                message=f"{evidence_type} evidence prompt should explicitly use [x0, y0, x1, y1] pixel boxes.",
            )
        )
    if str(evidence_type) in {"point_sequence", "point_set", "point_pair_set", "keyed_point_map"}:
        if _POINT_NOTATION_RE.search(prompt_text) is None:
            issues.append(
                _issue(
                    category="evidence_prompt",
                    code="missing_point_notation",
                    severity="warning",
                    mode=mode,
                    message=f"{evidence_type} prompt should explicitly use [x, y] pixel points.",
                )
            )
        if "pixel" not in lower:
            issues.append(
                _issue(
                    category="evidence_prompt",
                    code="missing_pixel_space_wording",
                    severity="warning",
                    mode=mode,
                    message=f"{evidence_type} prompt should state that evidence coordinates are in pixel space.",
            )
        )
    if str(evidence_type) in {"keyed_bbox_map", "keyed_point_map"} and not any(
        term in lower for term in ("object", "dictionary", "mapping", "keys")
    ):
        issues.append(
            _issue(
                category="evidence_prompt",
                code="missing_keyed_evidence_wording",
                severity="warning",
                mode=mode,
                message=f"{evidence_type} prompt should state that evidence is an object/dictionary keyed by witness role.",
            )
        )

    example, error = _extract_example_json(prompt_text)
    if example is None:
        issues.append(
            _issue(
                category="evidence_prompt",
                code="invalid_example_json",
                severity="error",
                mode=mode,
                message=error,
            )
        )
        return issues

    if list(example.keys()) != ["evidence", "answer"]:
        issues.append(
            _issue(
                category="evidence_prompt",
                code="example_key_order",
                severity="warning",
                mode=mode,
                message='Example JSON should have exactly keys "evidence" then "answer".',
                excerpt=json.dumps(example, ensure_ascii=True)[:220],
            )
        )
    shape_errors = _validate_evidence_value(str(evidence_type), example.get("evidence"), field="example.evidence")
    for shape_error in shape_errors[:5]:
        issues.append(
            _issue(
                category="evidence_prompt",
                code="example_evidence_shape",
                severity="warning",
                mode=mode,
                message=shape_error,
                excerpt=json.dumps(example, ensure_ascii=True)[:220],
            )
        )
    return issues


def _audit_prompts(output: Any) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    rows: list[dict[str, Any]] = []
    issues: list[dict[str, str]] = []
    prompt_variants = dict(getattr(output, "prompt_variants", {}) or {"active": getattr(output, "prompt", "")})
    evidence_type = str(getattr(getattr(output, "evidence_gt", None), "type", "") or "")
    for mode, prompt in sorted(prompt_variants.items()):
        mode_text = str(mode)
        prompt_text = str(prompt)
        body = _semantic_body(prompt_text)
        rows.append(
            {
                "mode": mode_text,
                "word_count": _word_count(prompt_text),
                "body_word_count": _word_count(body),
                "prompt": prompt_text,
            }
        )
        issues.extend(_find_redundancy_issues(prompt_text, mode=mode_text))
        if mode_text == _EVIDENCE_MODE:
            issues.extend(_audit_evidence_prompt(prompt_text, evidence_type=evidence_type, mode=mode_text))
        elif mode_text == _ANSWER_ONLY_MODE:
            example, error = _extract_example_json(prompt_text)
            if example is None:
                issues.append(
                    _issue(
                        category="answer_prompt",
                        code="invalid_answer_only_example",
                        severity="error",
                        mode=mode_text,
                        message=error,
                    )
                )
            elif list(example.keys()) != ["answer"]:
                issues.append(
                    _issue(
                        category="answer_prompt",
                        code="answer_only_example_keys",
                        severity="warning",
                        mode=mode_text,
                        message='Answer-only Example JSON should have exactly key "answer".',
                        excerpt=json.dumps(example, ensure_ascii=True)[:220],
                    )
                )
    return rows, issues


def _normalize_jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _normalize_jsonable(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_normalize_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_normalize_jsonable(item) for item in value]
    return value


def _audit_evidence_payload(output: Any) -> tuple[dict[str, Any], list[dict[str, str]]]:
    issues: list[dict[str, str]] = []
    evidence_gt = getattr(output, "evidence_gt")
    evidence_type = str(evidence_gt.type)
    evidence_value = _normalize_jsonable(evidence_gt.value)
    image = getattr(output, "image", None)
    image_size = tuple(image.size) if isinstance(image, PILImage.Image) else None

    if evidence_type not in _PIXEL_EVIDENCE_TYPES:
        issues.append(
            _issue(
                category="evidence_format",
                code="unsupported_public_evidence_type",
                severity="error",
                message=f"Public evidence type {evidence_type!r} is not one of {sorted(_PIXEL_EVIDENCE_TYPES)}.",
            )
        )

    for message in _validate_evidence_value(evidence_type, evidence_value, image_size=image_size, field="evidence_gt"):
        issues.append(
            _issue(
                category="evidence_geometry",
                code="invalid_evidence_gt_geometry",
                severity="error",
                message=message,
            )
        )

    trace_payload = getattr(output, "trace_payload", {})
    sanitized = sanitize_trace_payload_for_public_evidence(
        trace_payload if isinstance(trace_payload, Mapping) else {},
        evidence_gt=evidence_gt,
    )
    projected = sanitized.get("projected_evidence", {})
    projected_type = str(projected.get("type", "")) if isinstance(projected, Mapping) else ""
    if projected_type != evidence_type:
        issues.append(
            _issue(
                category="evidence_projection",
                code="projected_type_mismatch",
                severity="error",
                message=f"Projected evidence type {projected_type!r} does not match evidence_gt.type {evidence_type!r}.",
            )
        )

    projected_value = projected.get(evidence_type) if isinstance(projected, Mapping) else None
    if projected_value is None and evidence_type == "point_set" and isinstance(projected, Mapping):
        projected_value = projected.get("pixel_point_set")
    if projected_value is None and evidence_type == "keyed_point_map" and isinstance(projected, Mapping):
        projected_value = projected.get("pixel_keyed_point_map")
    if projected_value is None and evidence_type == "keyed_bbox_map" and isinstance(projected, Mapping):
        projected_value = projected.get("pixel_keyed_bbox_map")
    if projected_value is None:
        issues.append(
            _issue(
                category="evidence_projection",
                code="missing_projected_value",
                severity="error",
                message=f"Projected evidence does not include a {evidence_type!r} payload.",
            )
        )
    else:
        projected_value = _normalize_jsonable(projected_value)
        if projected_value != evidence_value:
            issues.append(
                _issue(
                    category="evidence_projection",
                    code="projected_value_mismatch",
                    severity="warning",
                    message="Projected public evidence payload differs from evidence_gt.value.",
                )
            )
        for message in _validate_evidence_value(
            evidence_type,
            projected_value,
            image_size=image_size,
            field="projected_evidence",
        ):
            issues.append(
                _issue(
                    category="evidence_geometry",
                    code="invalid_projected_geometry",
                    severity="error",
                    message=message,
                )
            )

    overlay_type, overlay_value = resolve_overlay_evidence(
        evidence_type=evidence_type,
        evidence_value=evidence_value,
        trace_payload=sanitized,
    )
    overlay_errors = _validate_evidence_value(
        str(overlay_type),
        _normalize_jsonable(overlay_value),
        image_size=image_size,
        field="overlay_evidence",
    )
    for message in overlay_errors:
        issues.append(
            _issue(
                category="evidence_geometry",
                code="invalid_overlay_geometry",
                severity="error",
                message=message,
            )
        )

    summary = {
        "evidence_type": evidence_type,
        "evidence_value_count": len(evidence_value) if isinstance(evidence_value, (list, Mapping)) else 1,
        "image_size": list(image_size) if image_size is not None else [],
        "projected_type": projected_type,
        "overlay_evidence_type": str(overlay_type),
        "overlay_evidence_value": _normalize_jsonable(overlay_value),
    }
    return summary, issues


def _trace_question_variant(task_id: str, output: Any, fallback: str) -> str:
    return str(fallback or getattr(output, "query_id", "") or "default")


def _audit_output(task_id: str, output: Any, *, instance_seed: int, requested_variant: str = "") -> dict[str, Any]:
    query_id = _trace_question_variant(task_id, output, requested_variant)
    prompt_rows, prompt_issues = _audit_prompts(output)
    evidence_summary, evidence_issues = _audit_evidence_payload(output)
    issues = [dict(issue) for issue in prompt_issues + evidence_issues]
    for issue in issues:
        issue["task"] = str(task_id)
        issue["query_id"] = str(query_id)
        issue["instance_seed"] = str(int(instance_seed))
    return {
        "task": str(task_id),
        "query_id": str(query_id),
        "observed_query_id": str(getattr(output, "query_id", "") or ""),
        "instance_seed": int(instance_seed),
        "answer_type": str(getattr(output.answer_gt, "type", "")),
        "evidence": evidence_summary,
        "prompts": prompt_rows,
        "issues": issues,
    }


def _collector_for_task(task_id: str):
    def _collector(output: Any, instance_seed: int) -> dict[str, Any]:
        return _audit_output(str(task_id), output, instance_seed=int(instance_seed))

    return _collector


def _generate_explicit_samples(
    *,
    task_id: str,
    variants: Sequence[tuple[str, Mapping[str, Any]]],
    samples_per_query_id: int,
    seed: int,
    max_attempts: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    task = create_task(str(task_id))
    records: list[dict[str, Any]] = []
    generated_counts: Counter[str] = Counter()
    errors: Counter[str] = Counter()
    for variant, params in variants:
        for sample_index in range(int(samples_per_query_id)):
            instance_seed = int(hash64(int(seed), f"prompt_evidence.explicit.{task_id}.{variant}", int(sample_index)))
            generation_params = dict(params)
            try:
                output = task.generate(
                    instance_seed,
                    params=generation_params,
                    max_attempts=int(max_attempts),
                )
            except Exception as exc:  # pragma: no cover - audit resilience
                errors[str(type(exc).__name__)] += 1
                continue
            generated_counts[str(variant)] += 1
            records.append(
                _audit_output(
                    str(task_id),
                    output,
                    instance_seed=int(instance_seed),
                    requested_variant=str(variant),
                )
            )
    expected_query_ids = [str(variant) for variant, _params in variants]
    collected_counts = Counter(str(record["query_id"]) for record in records)
    coverage = {
        "task": str(task_id),
        "sampling_mode": "explicit_manifest",
        "expected_query_ids": expected_query_ids,
        "generated_query_id_counts": dict(sorted(generated_counts.items())),
        "collected_query_id_counts": {variant: int(collected_counts.get(variant, 0)) for variant in expected_query_ids},
        "incomplete_query_ids": [
            variant
            for variant in expected_query_ids
            if int(collected_counts.get(variant, 0)) < int(samples_per_query_id)
        ],
        "generation_error_counts": dict(sorted(errors.items())),
        "total_generated": int(sum(generated_counts.values())),
    }
    return records, coverage


def _collect_task_records(
    *,
    task_id: str,
    samples_per_query_id: int,
    seed: int,
    max_attempts: int,
    max_total_samples_per_task: int,
    workers: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    explicit_variants = _EXPLICIT_VARIANT_PARAMS.get(str(task_id))
    if explicit_variants is not None:
        return _generate_explicit_samples(
            task_id=str(task_id),
            variants=explicit_variants,
            samples_per_query_id=int(samples_per_query_id),
            seed=int(seed),
            max_attempts=int(max_attempts),
        )

    collected = collect_query_id_samples(
        task_id=str(task_id),
        target_count_per_query_id=int(samples_per_query_id),
        seed=int(seed),
        max_attempts_per_instance=int(max_attempts),
        max_total_samples_per_task=int(max_total_samples_per_task),
        workers=int(workers),
        collector=_collector_for_task(str(task_id)),
    )
    records: list[dict[str, Any]] = []
    for variant_samples in collected.get("samples_by_query_id", {}).values():
        for sample in variant_samples:
            records.append(dict(sample))
    coverage = {
        "task": str(task_id),
        "sampling_mode": "variant_sampler",
        "expected_query_ids": list(collected.get("expected_query_ids", [])),
        "generated_query_id_counts": dict(collected.get("generated_query_id_counts", {})),
        "collected_query_id_counts": dict(collected.get("collected_query_id_counts", {})),
        "incomplete_query_ids": list(collected.get("incomplete_query_ids", [])),
        "generation_error_counts": dict(collected.get("generation_error_counts", {})),
        "total_generated": int(collected.get("total_generated", 0)),
    }
    return records, coverage


def _collect_task_records_worker(queue: Any, kwargs: Mapping[str, Any]) -> None:
    try:
        records, coverage = _collect_task_records(**dict(kwargs))
        queue.put({"records": records, "coverage": coverage, "error": ""})
    except Exception as exc:  # pragma: no cover - audit resilience
        queue.put(
            {
                "records": [],
                "coverage": {
                    "task": str(kwargs.get("task_id", "")),
                    "sampling_mode": "failed_worker",
                    "expected_query_ids": [],
                    "generated_query_id_counts": {},
                    "collected_query_id_counts": {},
                    "incomplete_query_ids": [],
                    "generation_error_counts": {str(type(exc).__name__): 1},
                    "total_generated": 0,
                },
                "error": str(exc),
            }
        )


def _collect_task_records_with_timeout(
    *,
    task_id: str,
    samples_per_query_id: int,
    seed: int,
    max_attempts: int,
    max_total_samples_per_task: int,
    workers: int,
    timeout_seconds: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if int(timeout_seconds) <= 0:
        return _collect_task_records(
            task_id=str(task_id),
            samples_per_query_id=int(samples_per_query_id),
            seed=int(seed),
            max_attempts=int(max_attempts),
            max_total_samples_per_task=int(max_total_samples_per_task),
            workers=int(workers),
        )

    ctx = multiprocessing.get_context("fork")
    queue = ctx.Queue(maxsize=1)
    kwargs = {
        "task_id": str(task_id),
        "samples_per_query_id": int(samples_per_query_id),
        "seed": int(seed),
        "max_attempts": int(max_attempts),
        "max_total_samples_per_task": int(max_total_samples_per_task),
        "workers": int(workers),
    }
    process = ctx.Process(target=_collect_task_records_worker, args=(queue, kwargs))
    process.start()
    process.join(float(timeout_seconds))
    if process.is_alive():
        process.terminate()
        process.join(5.0)
        if process.is_alive():  # pragma: no cover - extreme hang protection
            process.kill()
            process.join(5.0)
        return (
            [],
            {
                "task": str(task_id),
                "sampling_mode": "timeout",
                "expected_query_ids": [],
                "generated_query_id_counts": {},
                "collected_query_id_counts": {},
                "incomplete_query_ids": [],
                "generation_error_counts": {"TaskTimeout": 1},
                "total_generated": 0,
                "timeout_seconds": int(timeout_seconds),
            },
        )
    if queue.empty():
        error_name = "WorkerExit" if int(process.exitcode or 0) != 0 else "EmptyWorkerResult"
        return (
            [],
            {
                "task": str(task_id),
                "sampling_mode": "failed_worker",
                "expected_query_ids": [],
                "generated_query_id_counts": {},
                "collected_query_id_counts": {},
                "incomplete_query_ids": [],
                "generation_error_counts": {error_name: 1},
                "total_generated": 0,
            },
        )
    payload = queue.get()
    return list(payload.get("records", [])), dict(payload.get("coverage", {}))


def _resolve_task_ids(raw_tasks: str, *, default_only: bool) -> list[str]:
    if not str(raw_tasks).strip():
        return list_default_task_ids() if bool(default_only) else sorted(TASK_REGISTRY)
    task_ids = [item.strip() for item in str(raw_tasks).split(",") if item.strip()]
    unknown = [task_id for task_id in task_ids if task_id not in TASK_REGISTRY]
    if unknown:
        raise ValueError(f"unknown task ids: {', '.join(sorted(unknown))}")
    return sorted(dict.fromkeys(task_ids))


def _issue_sort_key(issue: Mapping[str, Any]) -> tuple[int, str, str, str]:
    severity_rank = {"error": 0, "warning": 1, "info": 2}
    return (
        severity_rank.get(str(issue.get("severity", "")), 99),
        str(issue.get("category", "")),
        str(issue.get("task", "")),
        str(issue.get("query_id", "")),
    )


def _coverage_issues(coverage_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for row in coverage_rows:
        task_id = str(row.get("task", ""))
        for variant in row.get("incomplete_query_ids", []):
            issues.append(
                {
                    **_issue(
                        category="generation",
                        code="incomplete_query_id_coverage",
                        severity="error",
                        message="Audit could not generate the requested sample count for this variant.",
                    ),
                    "task": task_id,
                    "query_id": str(variant),
                    "instance_seed": "",
                }
            )
        error_counts = row.get("generation_error_counts", {})
        if isinstance(error_counts, Mapping) and error_counts:
            issues.append(
                {
                    **_issue(
                        category="generation",
                        code="generation_errors",
                        severity="error",
                        message=f"Generation errors while auditing task: {dict(error_counts)}.",
                    ),
                    "task": task_id,
                    "query_id": "",
                    "instance_seed": "",
                }
            )
    return issues


def _issue_summary(
    records: Sequence[Mapping[str, Any]],
    coverage_rows: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    issues: list[dict[str, Any]] = []
    for record in records:
        for issue in record.get("issues", []):
            if isinstance(issue, Mapping):
                issues.append(dict(issue))
    issues.extend(_coverage_issues(coverage_rows))
    counts = Counter(str(issue.get("category", "unknown")) for issue in issues)
    return sorted(issues, key=_issue_sort_key), dict(sorted(counts.items()))


def _task_domain(task_id: str) -> str:
    task = create_task(str(task_id))
    return str(getattr(task, "domain", "unknown"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def _markdown_issue_table(issues: Sequence[Mapping[str, Any]], *, limit: int = 200) -> list[str]:
    if not issues:
        return ["No issues found.", ""]
    lines = [
        "| severity | category | code | task | variant | mode | message |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for issue in list(issues)[: int(limit)]:
        lines.append(
            "| "
            + " | ".join(
                str(issue.get(key, "")).replace("|", "\\|").replace("\n", " ")[:240]
                for key in ("severity", "category", "code", "task", "query_id", "mode", "message")
            )
            + " |"
        )
    if len(issues) > int(limit):
        lines.append(f"\n_Showing first {int(limit)} of {len(issues)} issues._")
    lines.append("")
    return lines


def _write_prompt_report(path: Path, *, records: Sequence[Mapping[str, Any]], issues: Sequence[Mapping[str, Any]]) -> None:
    prompt_issues = [issue for issue in issues if str(issue.get("category", "")).startswith("prompt") or str(issue.get("category", "")) == "answer_prompt"]
    prompt_rows = [prompt for record in records for prompt in record.get("prompts", []) if isinstance(prompt, Mapping)]
    word_counts = [int(row.get("word_count", 0)) for row in prompt_rows]
    body_counts = [int(row.get("body_word_count", 0)) for row in prompt_rows]
    lines = [
        "# Prompt Redundancy Audit",
        "",
        f"- rendered prompts: `{len(prompt_rows)}`",
        f"- prompt issues: `{len(prompt_issues)}`",
        f"- max prompt words: `{max(word_counts) if word_counts else 0}`",
        f"- max prompt-body words: `{max(body_counts) if body_counts else 0}`",
        "",
        "## Issues",
        "",
        *_markdown_issue_table(prompt_issues),
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_evidence_prompt_report(path: Path, *, issues: Sequence[Mapping[str, Any]]) -> None:
    evidence_prompt_issues = [issue for issue in issues if str(issue.get("category", "")) == "evidence_prompt"]
    lines = [
        "# Evidence Prompt Audit",
        "",
        f"- evidence prompt issues: `{len(evidence_prompt_issues)}`",
        "",
        "## Issues",
        "",
        *_markdown_issue_table(evidence_prompt_issues),
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_projection_report(
    path: Path,
    *,
    records: Sequence[Mapping[str, Any]],
    coverage_rows: Sequence[Mapping[str, Any]],
    issues: Sequence[Mapping[str, Any]],
) -> None:
    projection_issues = [
        issue
        for issue in issues
        if str(issue.get("category", "")) in {"evidence_format", "evidence_geometry", "evidence_projection"}
    ]
    evidence_types = Counter(str(record.get("evidence", {}).get("evidence_type", "")) for record in records)
    query_ids = {(str(record.get("task", "")), str(record.get("query_id", ""))) for record in records}
    incomplete = [
        row
        for row in coverage_rows
        if row.get("incomplete_query_ids") or row.get("generation_error_counts")
    ]
    lines = [
        "# Evidence Projection Validation",
        "",
        f"- sampled instances: `{len(records)}`",
        f"- query ids covered: `{len(query_ids)}`",
        f"- evidence projection/geometry issues: `{len(projection_issues)}`",
        f"- evidence types: `{dict(sorted(evidence_types.items()))}`",
        f"- tasks with incomplete coverage or generation errors: `{len(incomplete)}`",
        "",
        "## Coverage",
        "",
        "| task | expected query ids | collected counts | generated | issues |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for row in coverage_rows:
        row_issues: list[str] = []
        if row.get("incomplete_query_ids"):
            row_issues.append(f"incomplete={row.get('incomplete_query_ids')}")
        if row.get("generation_error_counts"):
            row_issues.append(f"errors={row.get('generation_error_counts')}")
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("task", "")),
                    "`" + ", ".join(str(value) for value in row.get("expected_query_ids", [])) + "`",
                    "`" + str(dict(row.get("collected_query_id_counts", {}))) + "`",
                    str(row.get("total_generated", 0)),
                    "`" + "; ".join(row_issues) + "`",
                ]
            )
            + " |"
        )
    lines.extend(["", "## Issues", "", *_markdown_issue_table(projection_issues)])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_summary_report(
    path: Path,
    *,
    task_ids: Sequence[str],
    records: Sequence[Mapping[str, Any]],
    coverage_rows: Sequence[Mapping[str, Any]],
    issues: Sequence[Mapping[str, Any]],
    issue_counts: Mapping[str, int],
    output_dir: Path,
) -> None:
    variant_pairs = {(str(record.get("task", "")), str(record.get("query_id", ""))) for record in records}
    expected_query_id_count = sum(len(row.get("expected_query_ids", [])) for row in coverage_rows)
    domain_counts: dict[str, set[str]] = defaultdict(set)
    for task_id in task_ids:
        domain_counts[_task_domain(str(task_id))].add(str(task_id))
    lines = [
        "# Prompt/Evidence Contract Audit",
        "",
        f"- tasks: `{len(task_ids)}`",
        f"- expected public-facing query ids: `{expected_query_id_count}`",
        f"- sampled query ids: `{len(variant_pairs)}`",
        f"- sampled instances: `{len(records)}`",
        f"- issues: `{len(issues)}`",
        f"- issue categories: `{dict(issue_counts)}`",
        f"- report directory: `{output_dir}`",
        "",
        "Artifacts:",
        f"- Prompt redundancy: `{output_dir / 'prompt_redundancy_audit.md'}`",
        f"- Evidence prompt clarity: `{output_dir / 'evidence_prompt_audit.md'}`",
        f"- Evidence projection validation: `{output_dir / 'evidence_projection_validation.md'}`",
        f"- Evidence overlay samples: `{output_dir / 'evidence_overlay_samples'}`",
        f"- Machine-readable report: `{output_dir / 'prompt_evidence_audit.json'}`",
        "",
        "## Domain Task Counts",
        "",
        "| domain | tasks |",
        "| --- | ---: |",
    ]
    for domain, tasks in sorted(domain_counts.items()):
        lines.append(f"| {domain} | {len(tasks)} |")
    lines.extend(["", "## Highest Priority Issues", "", *_markdown_issue_table(issues, limit=50)])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_overlay_samples(
    *,
    records: Sequence[Mapping[str, Any]],
    output_dir: Path,
    sample_limit: int,
    max_attempts: int,
) -> None:
    if int(sample_limit) <= 0:
        return
    overlay_root = output_dir / "evidence_overlay_samples"
    overlay_root.mkdir(parents=True, exist_ok=True)
    for old_png in overlay_root.glob("*.png"):
        old_png.unlink()
    selected = sorted(
        records,
        key=lambda record: (
            0
            if any(str(issue.get("severity", "")) == "error" for issue in record.get("issues", []))
            else (1 if record.get("issues") else 2),
            str(record.get("task", "")),
            str(record.get("query_id", "")),
        ),
    )[: int(sample_limit)]
    for index, record in enumerate(selected):
        task_id = str(record.get("task", ""))
        query_id = str(record.get("query_id", ""))
        seed = int(record.get("instance_seed", 0))
        task = create_task(task_id)
        params: dict[str, Any] = {}
        if task_id in _EXPLICIT_VARIANT_PARAMS:
            for variant, variant_params in _EXPLICIT_VARIANT_PARAMS[task_id]:
                if str(variant) == query_id:
                    params = dict(variant_params)
                    break
        elif query_id and query_id != "default":
            params["query_id"] = query_id
        output = task.generate(seed, params=params, max_attempts=int(max_attempts))
        sanitized = sanitize_trace_payload_for_public_evidence(output.trace_payload, evidence_gt=output.evidence_gt)
        overlay_type, overlay_value = resolve_overlay_evidence(
            evidence_type=str(output.evidence_gt.type),
            evidence_value=output.evidence_gt.value,
            trace_payload=sanitized,
        )
        overlay = render_evidence_overlay(
            output.image,
            evidence_type=str(overlay_type),
            evidence_value=overlay_value,
        )
        safe_variant = re.sub(r"[^a-zA-Z0-9_.-]+", "_", query_id or "default")
        overlay.save(overlay_root / f"{index:03d}_{task_id}_{safe_variant}.png")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", default="", help="Comma-separated task ids. Defaults to default-enabled tasks.")
    parser.add_argument("--all-registered", action="store_true", help="Audit every registered task, including disabled tasks.")
    parser.add_argument("--samples-per-query-id", type=int, default=1)
    parser.add_argument("--seed", type=int, default=20260504)
    parser.add_argument("--max-attempts", type=int, default=200)
    parser.add_argument("--max-total-samples-per-task", type=int, default=1024)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument(
        "--task-timeout-seconds",
        type=int,
        default=240,
        help="Per-task wall-clock timeout. Set to 0 to disable.",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("review/prompt-evidence-clarity"))
    parser.add_argument("--progress", action="store_true")
    parser.add_argument(
        "--overlay-samples",
        type=int,
        default=0,
        help="Write this many evidence-overlay PNG samples for visual inspection.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if int(args.samples_per_query_id) <= 0:
        raise ValueError("--samples-per-query-id must be > 0")
    if int(args.max_attempts) <= 0:
        raise ValueError("--max-attempts must be > 0")
    if int(args.max_total_samples_per_task) <= 0:
        raise ValueError("--max-total-samples-per-task must be > 0")
    if int(args.workers) <= 0:
        raise ValueError("--workers must be > 0")
    if int(args.task_timeout_seconds) < 0:
        raise ValueError("--task-timeout-seconds must be >= 0")

    task_ids = _resolve_task_ids(str(args.tasks), default_only=not bool(args.all_registered))
    all_records: list[dict[str, Any]] = []
    coverage_rows: list[dict[str, Any]] = []
    for index, task_id in enumerate(task_ids, start=1):
        if bool(args.progress):
            print(f"[{index}/{len(task_ids)}] auditing {task_id}", file=sys.stderr, flush=True)
        records, coverage = _collect_task_records_with_timeout(
            task_id=str(task_id),
            samples_per_query_id=int(args.samples_per_query_id),
            seed=int(hash64(int(args.seed), f"prompt_evidence_contracts.{task_id}", 0)),
            max_attempts=int(args.max_attempts),
            max_total_samples_per_task=int(args.max_total_samples_per_task),
            workers=int(args.workers),
            timeout_seconds=int(args.task_timeout_seconds),
        )
        all_records.extend(records)
        coverage_rows.append(coverage)
        if bool(args.progress):
            print(
                f"[{index}/{len(task_ids)}] done {task_id}: "
                f"query_ids={len(coverage.get('expected_query_ids', []))}, "
                f"records={len(records)}, issues={sum(len(record.get('issues', [])) for record in records)}",
                file=sys.stderr,
                flush=True,
            )

    issues, issue_counts = _issue_summary(all_records, coverage_rows)
    expected_query_id_count = sum(len(row.get("expected_query_ids", [])) for row in coverage_rows)
    output_dir = Path(args.output_dir)
    payload = {
        "config": {
            "tasks": list(task_ids),
            "default_only": not bool(args.all_registered),
            "samples_per_query_id": int(args.samples_per_query_id),
            "seed": int(args.seed),
            "max_attempts": int(args.max_attempts),
            "max_total_samples_per_task": int(args.max_total_samples_per_task),
            "workers": int(args.workers),
            "task_timeout_seconds": int(args.task_timeout_seconds),
        },
        "summary": {
            "task_count": int(len(task_ids)),
            "expected_public_query_id_count": int(expected_query_id_count),
            "sampled_instance_count": int(len(all_records)),
            "sampled_query_id_count": int(len({(record["task"], record["query_id"]) for record in all_records})),
            "issue_count": int(len(issues)),
            "issue_counts_by_category": dict(issue_counts),
            "issue_counts_by_severity": dict(Counter(str(issue.get("severity", "")) for issue in issues)),
        },
        "coverage": list(coverage_rows),
        "issues": list(issues),
        "records": list(all_records),
    }
    _write_json(output_dir / "prompt_evidence_audit.json", payload)
    _write_prompt_report(output_dir / "prompt_redundancy_audit.md", records=all_records, issues=issues)
    _write_evidence_prompt_report(output_dir / "evidence_prompt_audit.md", issues=issues)
    _write_projection_report(
        output_dir / "evidence_projection_validation.md",
        records=all_records,
        coverage_rows=coverage_rows,
        issues=issues,
    )
    _write_summary_report(
        output_dir / "prompt_evidence_contract_audit.md",
        task_ids=task_ids,
        records=all_records,
        coverage_rows=coverage_rows,
        issues=issues,
        issue_counts=issue_counts,
        output_dir=output_dir,
    )
    _write_overlay_samples(
        records=all_records,
        output_dir=output_dir,
        sample_limit=int(args.overlay_samples),
        max_attempts=int(args.max_attempts),
    )
    print(
        f"audited {len(task_ids)} tasks, {expected_query_id_count} expected query ids, "
        f"{len(all_records)} samples, {len(issues)} issues; wrote {output_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

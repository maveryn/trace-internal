from __future__ import annotations

import ast
import json
import re
from numbers import Integral
from typing import Any

import numpy as np
from mathruler.grader import extract_boxed_content, grade_answer

NO_ANSWER = "__NO_ANSWER__"
CHOICE_LETTERS = "ABCDEFG"
MCQ_LETTER_RE = re.compile(r"^\s*\(?([A-Ga-g])\)?\s*[\).:]?\s*$")
LEADING_LETTER_RE = re.compile(r"^\s*\(?([A-Ga-g])\)?\s*[\).:\-]\s*(.+?)\s*$")
DOUBLE_LEADING_LETTER_RE = re.compile(
    r"^\s*\(?([A-Ga-g])\)?\s*[\).:\-]\s*\(?([A-Ga-g])\)?\s*[\).:\-]\s*(.*?)\s*$"
)
ANS_PREFIX_RE = re.compile(r"(?is)\b(?:final\s*answer|answer|option|choice)\b\s*[:：\-]?\s*(.+)$")
SENTENCEY_RE = re.compile(r"(?i)\b(?:therefore|because|since|hence|thus|we have|let us|so that|this means)\b")
YES_NO_RE = re.compile(r"(?i)\b(yes|no|true|false)\b")
INT_RE = re.compile(r"[-+]?\d+")
NUMBER_OR_FRAC_RE = re.compile(r"[-+]?\d+\s*/\s*\d+|[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?")
OPTION_LINE_RE = re.compile(r"(?mi)^\s*([A-G])\s*[\).:]\s*(.+?)\s*$")


def _is_non_string_sequence(value: Any) -> bool:
    return isinstance(value, (list, tuple, np.ndarray)) and not isinstance(value, (str, bytes))


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


def _parse_response_grid(text: str | None) -> np.ndarray | None:
    if not text:
        return None
    try:
        parsed = ast.literal_eval(text)
    except (SyntaxError, ValueError, TypeError):
        normalized = text.replace("{", "[").replace("}", "]")
        try:
            parsed = ast.literal_eval(normalized)
        except (SyntaxError, ValueError, TypeError):
            return None
    return _to_numpy_grid(parsed)


def _normalize_text(text: str) -> str:
    s = str(text).strip()
    s = s.replace("\u2212", "-")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def strip_wrappers(text: str) -> str:
    s = _normalize_text(text)
    if not s:
        return s
    for _ in range(3):
        s2 = s
        s2 = re.sub(r"^\$([^$]+)\$$", r"\1", s2)
        s2 = re.sub(r"^\\\((.+)\\\)$", r"\1", s2)
        s2 = re.sub(r"^\\\[(.+)\\\]$", r"\1", s2)
        s2 = re.sub(r"^\\text\{(.+)\}$", r"\1", s2)
        s2 = s2.strip("`\"' ")
        if s2 == s:
            break
        s = s2
    return s.strip()


def _normalize_option_text(text: str) -> str:
    s = strip_wrappers(text).strip()
    s = re.sub(r"[ \t\r\n]+", " ", s)
    s = re.sub(r"^[\-\.:;,]+", "", s)
    s = re.sub(r"[\-\.:;,]+$", "", s)
    return s.strip().lower()


def _normalize_exact_answer_text(text: str) -> str:
    s = strip_wrappers(text).strip()
    if not s:
        return ""
    for _ in range(3):
        s2 = s
        s2 = re.sub(r"^\*{1,3}(.+?)\*{1,3}$", r"\1", s2)
        s2 = re.sub(r"^_{1,3}(.+?)_{1,3}$", r"\1", s2)
        s2 = re.sub(r"^~{1,2}(.+?)~{1,2}$", r"\1", s2)
        s2 = re.sub(r"^`(.+?)`$", r"\1", s2)
        s2 = s2.strip()
        if s2 == s:
            break
        s = s2
    return _normalize_text(s).casefold()


def _extract_prompt_choice_map(prompt_text: str | None) -> dict[str, str]:
    if not prompt_text:
        return {}
    mapping: dict[str, str] = {}
    for letter, option_text in OPTION_LINE_RE.findall(prompt_text):
        normalized = _normalize_option_text(option_text)
        if normalized:
            mapping[letter.upper()] = normalized
    return mapping


def _normalize_yes_no(text: str) -> str | None:
    s = _normalize_text(text).lower()
    if s in {"yes", "true", "y", "1"}:
        return "yes"
    if s in {"no", "false", "n", "0"}:
        return "no"
    return None


def _to_scalar_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, Integral):
        return int(value)
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _parse_scalar_int_text(text: str) -> int | None:
    if not text:
        return None
    s = strip_wrappers(text)
    if not s:
        return None
    try:
        parsed = json.loads(s)
    except Exception:
        try:
            parsed = ast.literal_eval(s)
        except Exception:
            parsed = None
    value = _to_scalar_int(parsed)
    if value is not None:
        return value
    matches = INT_RE.findall(s)
    if not matches:
        return None
    try:
        return int(matches[0])
    except ValueError:
        return None


def _normalize_index_list(items: Any) -> list[int] | None:
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


def _parse_index_list_text(text: str) -> list[int] | None:
    if not text:
        return None
    s = strip_wrappers(text)
    if not s:
        return None
    parsed: Any = None
    try:
        parsed = json.loads(s)
    except Exception:
        parsed = None
    if parsed is None:
        try:
            parsed = ast.literal_eval(s)
        except Exception:
            parsed = None
    if isinstance(parsed, (list, tuple, set)):
        return _normalize_index_list(parsed)

    matches = INT_RE.findall(s)
    if not matches:
        return None
    try:
        return [int(m) for m in matches]
    except ValueError:
        return None


def _parse_gt_index_list_text(text: str) -> list[int] | None:
    if not text:
        return None
    s = strip_wrappers(text)
    if not s:
        return None
    parsed: Any = None
    try:
        parsed = json.loads(s)
    except Exception:
        parsed = None
    if parsed is None:
        try:
            parsed = ast.literal_eval(s)
        except Exception:
            parsed = None
    if isinstance(parsed, (list, tuple, set)):
        return _normalize_index_list(parsed)
    return None


def _parse_json_list(text: str) -> list[Any] | None:
    if not text:
        return None
    s = text.strip()
    if not (s.startswith("[") and s.endswith("]")):
        return None
    try:
        parsed = json.loads(s)
    except Exception:
        return None
    return parsed if isinstance(parsed, list) else None


def _parse_choice_list(items: list[Any]) -> list[str] | None:
    letters: list[str] = []
    for item in items:
        s = str(item).strip().upper()
        if len(s) != 1 or s not in CHOICE_LETTERS:
            return None
        letters.append(s)
    return letters if letters else None


def _parse_numeric_list(items: list[Any]) -> list[float] | None:
    values: list[float] = []
    for item in items:
        val = _parse_numeric_value(str(item))
        if val is None:
            return None
        values.append(val)
    return values if values else None


def _index_list_similarity(pred_list: list[int], gt_list: list[int], mode: str = "exact") -> float:
    pred_set = set(int(v) for v in pred_list)
    gt_set = set(int(v) for v in gt_list)
    if mode == "exact":
        return 1.0 if pred_set == gt_set else 0.0
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


def _parse_numeric_value(value: str) -> float | None:
    if value is None:
        return None
    s = strip_wrappers(value)
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
    s = strip_wrappers(text)
    if not s:
        return []
    values: list[float] = []
    for match in NUMBER_OR_FRAC_RE.findall(s):
        val = _parse_numeric_value(match)
        if val is not None:
            values.append(val)
    return values


def _is_simple_numeric_or_unit(gt: str) -> bool:
    if not gt:
        return False
    if "\\" in gt or "$" in gt or "frac" in gt or "sqrt" in gt:
        return False
    return len(_extract_numeric_values(gt)) == 1


def _split_prefixed_choice_answer(gt: str) -> tuple[str, str] | None:
    if not gt:
        return None
    m = LEADING_LETTER_RE.match(gt.strip())
    if not m:
        return None
    return m.group(1).upper(), m.group(2).strip()


def _parse_choice_ground_truth(gt: str) -> list[str] | None:
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
    s_norm = re.sub(r"\b(AND|OR)\b", "", s)
    if re.search(rf"[H-Z]", s_norm):
        return None
    letters = re.findall(rf"[{CHOICE_LETTERS}]", s_norm)
    if not letters:
        return None
    cleaned = re.sub(rf"[{CHOICE_LETTERS}\s,;/\\()\[\]-]", "", s_norm)
    if cleaned:
        return None
    return letters


def _parse_numeric_sequence_gt(gt: str) -> list[float] | None:
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


def _extract_mcq_letter(text: str) -> str | None:
    s = strip_wrappers(text)
    if not s:
        return None
    m = MCQ_LETTER_RE.match(s)
    if m:
        return m.group(1).upper()
    # Accept anchored option formats before conjunction checks, e.g.:
    # "A. ...", "(A) ...", "(A) A. ..."
    m = DOUBLE_LEADING_LETTER_RE.match(s)
    if m:
        first = m.group(1).upper()
        second = m.group(2).upper()
        if first == second:
            return first
    m = LEADING_LETTER_RE.match(s)
    if m:
        return m.group(1).upper()
    # Keep conservative guard for non-anchored free-form text like "A and B".
    if re.search(r"(?i)\b(or|and|either|neither)\b", s):
        return None
    m = re.search(
        r"(?is)\b(?:final\s*answer|answer|option|choice)\b[^A-G]{0,16}\(?([A-Ga-g])\)?\b",
        s,
    )
    if m:
        return m.group(1).upper()
    return None


def _looks_like_open_answer(text: str, gt_raw: str) -> bool:
    s = strip_wrappers(text)
    if not s:
        return False
    if len(s) > 96:
        return False
    if SENTENCEY_RE.search(s):
        return False
    words = s.split()
    if len(words) > 12:
        return False
    has_letters = bool(re.search(r"[A-Za-z]", s))
    num_tokens = re.findall(r"[-+]?\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)?", s)
    if has_letters and len(num_tokens) > 1:
        return False
    if _normalize_yes_no(s) is not None:
        return True
    if re.fullmatch(r"[A-Za-z ]+", gt_raw) and len(words) <= 4:
        return True
    if re.search(r"[0-9\\/\^\+\-\=\(\)\[\]\{\}\$%]", s):
        return True
    return False


def collect_candidates(response: str) -> list[tuple[str, str]]:
    text = "" if response is None else str(response)
    out: list[tuple[str, str]] = []

    boxed = extract_boxed_content(text)
    if boxed is not None:
        b = strip_wrappers(str(boxed))
        if b and b.lower() != "none":
            out.append(("boxed", b))

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if lines:
        for ln in reversed(lines[-12:]):
            clean = strip_wrappers(ln)
            m = ANS_PREFIX_RE.search(clean)
            if m:
                val = strip_wrappers(m.group(1))
                val = re.sub(r"(?is)^\s*(?:is|are|=|:|-)\s*", "", val).strip()
                if val:
                    out.append(("marker", val))
        out.append(("last_line", strip_wrappers(lines[-1])))

    uniq: list[tuple[str, str]] = []
    seen = set()
    for method, cand in out:
        key = _normalize_text(cand)
        if not key or key in seen:
            continue
        seen.add(key)
        uniq.append((method, key))
    return uniq


def _score_prefixed_choice(
    candidates: list[tuple[str, str]],
    expected_letter: str,
    remainder: str,
) -> tuple[float, bool, str | None, str]:
    extracted_letter: str | None = None
    method = "none"
    for m, cand in candidates:
        letter = _extract_mcq_letter(cand)
        if letter is not None:
            extracted_letter = letter
            method = m
            break
    if extracted_letter is not None and extracted_letter == expected_letter:
        return 1.0, True, extracted_letter, method
    if remainder:
        score, extracted, extracted_answer, extracted_method = strict_score_response(
            response="\n".join([x[1] for x in candidates]),
            ground_truth=remainder,
        )
        if extracted:
            return score, True, extracted_answer, extracted_method
    return 0.0, extracted_letter is not None, extracted_letter, method


def strict_score_response(
    response: str,
    ground_truth: Any,
    list_reward_mode: str = "exact",
    prompt_text: str | None = None,
) -> tuple[float, bool, str | None, str]:
    candidates = collect_candidates(response)
    if not candidates:
        return 0.0, False, None, "none"
    prompt_choice_map = _extract_prompt_choice_map(prompt_text)

    gt_grid = _to_numpy_grid(ground_truth)
    if gt_grid is not None:
        for method, cand in candidates:
            pred_grid = _parse_response_grid(cand)
            if pred_grid is None:
                continue
            if pred_grid.shape != gt_grid.shape:
                return 0.0, True, cand, method
            correct = bool(np.array_equal(pred_grid, gt_grid))
            return (1.0 if correct else 0.0), True, cand, method
        return 0.0, False, None, "none"

    gt_items: list[Any] | None = None
    if _is_non_string_sequence(ground_truth):
        gt_items = list(ground_truth)
    elif isinstance(ground_truth, str):
        gt_items = _parse_json_list(ground_truth)

    if gt_items is not None:
        gt_index_list = _normalize_index_list(gt_items)
        if gt_index_list is not None:
            best_score = 0.0
            extracted = False
            best_answer = None
            best_method = "none"
            for method, cand in candidates:
                pred_list = _parse_index_list_text(cand)
                if pred_list is None:
                    continue
                extracted = True
                score = _index_list_similarity(pred_list, gt_index_list, mode=list_reward_mode)
                if score >= best_score:
                    best_score = score
                    best_answer = cand
                    best_method = method
            return float(best_score), extracted, best_answer, best_method

        choice_letters = _parse_choice_list(gt_items)
        if choice_letters is not None:
            extracted_letter = None
            method = "none"
            for m, cand in candidates:
                letter = _extract_mcq_letter(cand)
                if letter is not None:
                    extracted_letter = letter
                    method = m
                    break
            if extracted_letter is None:
                expected_option_texts = {
                    prompt_choice_map[letter]
                    for letter in sorted(set(choice_letters))
                    if letter in prompt_choice_map
                }
                if expected_option_texts:
                    for m, cand in candidates:
                        normalized_cand = _normalize_option_text(cand)
                        if normalized_cand and normalized_cand in expected_option_texts:
                            return 1.0, True, cand, m
                return 0.0, False, None, "none"
            expected = sorted(set(choice_letters))
            if len(expected) == 1:
                return (1.0 if extracted_letter == expected[0] else 0.0), True, extracted_letter, method
            return (1.0 if sorted(set([extracted_letter])) == expected else 0.0), True, extracted_letter, method

        numeric_list = _parse_numeric_list(gt_items)
        if numeric_list is not None and len(numeric_list) > 1:
            for method, cand in candidates:
                values = _extract_numeric_values(cand)
                if len(values) < len(numeric_list):
                    continue
                tail = values[-len(numeric_list) :]
                ok = len(tail) == len(numeric_list) and all(abs(a - b) < 1e-6 for a, b in zip(tail, numeric_list))
                return (1.0 if ok else 0.0), True, cand, method
            return 0.0, False, None, "none"

        any_extracted = False
        extracted_answer = None
        extracted_method = "none"
        for item in gt_items:
            score, extracted, answer, method = strict_score_response(
                response=response,
                ground_truth=item,
                list_reward_mode=list_reward_mode,
            )
            if score > 0.5:
                return score, extracted, answer, method
            if extracted and not any_extracted:
                any_extracted = True
                extracted_answer = answer
                extracted_method = method
        return 0.0, any_extracted, extracted_answer, extracted_method

    scalar_gt = _to_scalar_int(ground_truth)
    if scalar_gt is not None:
        for method, cand in candidates:
            pred_scalar = _parse_scalar_int_text(cand)
            if pred_scalar is None:
                continue
            return (1.0 if pred_scalar == scalar_gt else 0.0), True, str(pred_scalar), method
        return 0.0, False, None, "none"

    gt_str = str(ground_truth).strip() if ground_truth is not None else ""
    if not gt_str:
        return 0.0, False, None, "none"

    prefixed = _split_prefixed_choice_answer(gt_str)
    if prefixed is not None:
        return _score_prefixed_choice(candidates, prefixed[0], prefixed[1])

    choice_letters = _parse_choice_ground_truth(gt_str)
    if choice_letters is not None:
        extracted_letter = None
        method = "none"
        for m, cand in candidates:
            letter = _extract_mcq_letter(cand)
            if letter is not None:
                extracted_letter = letter
                method = m
                break
        if extracted_letter is None:
            expected_option_texts = {
                prompt_choice_map[letter]
                for letter in sorted(set(choice_letters))
                if letter in prompt_choice_map
            }
            if expected_option_texts:
                for m, cand in candidates:
                    normalized_cand = _normalize_option_text(cand)
                    if normalized_cand and normalized_cand in expected_option_texts:
                        return 1.0, True, cand, m
            return 0.0, False, None, "none"
        expected = sorted(set(choice_letters))
        if len(expected) == 1:
            return (1.0 if extracted_letter == expected[0] else 0.0), True, extracted_letter, method
        return (1.0 if sorted(set([extracted_letter])) == expected else 0.0), True, extracted_letter, method

    yn_expected = _normalize_yes_no(gt_str)
    if yn_expected is not None:
        for method, cand in candidates:
            yn = _normalize_yes_no(cand)
            if yn is not None:
                return (1.0 if yn == yn_expected else 0.0), True, yn, method
        return 0.0, False, None, "none"

    num_seq_gt = _parse_numeric_sequence_gt(gt_str)
    if num_seq_gt is not None:
        for method, cand in candidates:
            values = _extract_numeric_values(cand)
            if len(values) < len(num_seq_gt):
                continue
            tail = values[-len(num_seq_gt) :]
            ok = len(tail) == len(num_seq_gt) and all(abs(a - b) < 1e-6 for a, b in zip(tail, num_seq_gt))
            return (1.0 if ok else 0.0), True, cand, method
        return 0.0, False, None, "none"

    if _is_simple_numeric_or_unit(gt_str):
        gt_values = _extract_numeric_values(gt_str)
        if gt_values:
            gt_val = gt_values[0]
            for method, cand in candidates:
                values = _extract_numeric_values(cand)
                if not values:
                    continue
                ok = any(abs(v - gt_val) < 1e-6 for v in values)
                return (1.0 if ok else 0.0), True, cand, method
        return 0.0, False, None, "none"

    normalized_gt = _normalize_exact_answer_text(gt_str)
    if normalized_gt:
        for method, cand in candidates:
            if _normalize_exact_answer_text(cand) == normalized_gt:
                return 1.0, True, cand, method

    for method, cand in candidates:
        if not _looks_like_open_answer(cand, gt_str):
            continue
        try:
            ok = bool(grade_answer(cand, gt_str))
        except Exception:
            ok = False
        return (1.0 if ok else 0.0), True, cand, method

    return 0.0, False, None, "none"

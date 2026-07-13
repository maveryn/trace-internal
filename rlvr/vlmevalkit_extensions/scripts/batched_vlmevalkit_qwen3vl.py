#!/usr/bin/env python3
from __future__ import annotations

import gc
import json
import math
import os
import re
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
from PIL import Image

from vlmeval.smp import dump, get_intermediate_file_path, load


def load_jsonl_by_index(path: str | Path) -> dict[str, dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return {}
    rows: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            rows[str(row["index"])] = row
    return rows


def append_jsonl(path: str | Path, rows: Iterable[dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, default=_json_default) + "\n")


def _json_default(value: Any) -> Any:
    try:
        import numpy as np

        if isinstance(value, np.integer):
            return int(value)
        if isinstance(value, np.floating):
            return float(value)
        if isinstance(value, np.ndarray):
            return value.tolist()
        if isinstance(value, np.bool_):
            return bool(value)
    except Exception:
        pass
    return str(value)


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value)


def _load_image(value: Any) -> Image.Image:
    if isinstance(value, Image.Image):
        return value.convert("RGB")
    if isinstance(value, (str, Path)):
        return Image.open(value).convert("RGB")
    if hasattr(value, "convert"):
        return value.convert("RGB")
    raise TypeError(f"Unsupported image value type: {type(value)!r}")


def build_prompt_for_runner(dataset: Any, row: Any, *, video_llm: bool = False) -> list[dict[str, Any]]:
    del video_llm
    return dataset.build_prompt(row)


def make_vllm_request(
    processor: Any,
    struct: list[dict[str, Any]],
    *,
    max_pixels: int | None = None,
    total_pixels: int | None = None,
) -> dict[str, Any]:
    content: list[dict[str, Any]] = []
    images: list[Image.Image] = []
    videos: list[Any] = []
    text_parts: list[str] = []

    for item in struct:
        typ = item.get("type")
        value = item.get("value")
        if typ == "image":
            image = _load_image(value)
            images.append(image)
            image_item: dict[str, Any] = {"type": "image"}
            if max_pixels is not None:
                image_item["max_pixels"] = max_pixels
            if total_pixels is not None:
                image_item["total_pixels"] = total_pixels
            content.append(image_item)
        elif typ == "video":
            videos.append(value)
            content.append({"type": "video"})
        elif typ == "text":
            text = _as_text(value)
            if text:
                text_parts.append(text)
                content.append({"type": "text", "text": text})
        else:
            text = _as_text(value)
            if text:
                text_parts.append(text)
                content.append({"type": "text", "text": text})

    if not content:
        content = [{"type": "text", "text": "\n".join(text_parts)}]
    messages = [{"role": "user", "content": content}]
    prompt = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    req: dict[str, Any] = {"prompt": prompt}
    mm: dict[str, Any] = {}
    if images:
        mm["image"] = images
    if videos:
        mm["video"] = videos
    if mm:
        req["multi_modal_data"] = mm
    return req


def write_eval_files(dataset: Any, pred_map: dict[str, dict[str, Any]], output_dir: str | Path) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for _, row in dataset.data.iterrows():
        record = row.to_dict()
        pred = pred_map.get(str(record["index"]), {})
        record["prediction"] = pred.get("prediction", "")
        record["finish_reason"] = pred.get("finish_reason", "")
        record["output_token_count"] = pred.get("output_token_count", None)
        rows.append(record)
    frame = pd.DataFrame(rows)
    alias = dataset.dataset_name
    xlsx = output_dir / f"{alias}_predictions.xlsx"
    frame.to_excel(xlsx, index=False)
    table_jsonl = output_dir / f"{alias}_predictions_table.jsonl"
    with table_jsonl.open("w", encoding="utf-8") as f:
        for record in rows:
            f.write(json.dumps(record, ensure_ascii=False, default=_json_default) + "\n")
    return xlsx


def cleanup_vllm_engine(llm: Any) -> None:
    if llm is None:
        return
    for attr in ("llm_engine", "engine"):
        engine = getattr(llm, attr, None)
        if engine is not None and hasattr(engine, "shutdown"):
            try:
                engine.shutdown()
            except Exception:
                pass
    try:
        del llm
    except Exception:
        pass
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


def _score_to_percent(value: Any) -> float | None:
    try:
        out = float(value)
    except Exception:
        return None
    if math.isnan(out):
        return None
    if abs(out) <= 1.0:
        out *= 100.0
    return out


def _df_to_scores(result: pd.DataFrame) -> dict[str, Any]:
    table = result.to_dict(orient="records")
    scores: dict[str, Any] = {"table": table}
    if len(result) == 1:
        for col in result.columns:
            parsed = _score_to_percent(result.iloc[0][col])
            if parsed is not None:
                scores[str(col)] = parsed
    for _, row in result.iterrows():
        lower_values = {str(v).strip().lower() for v in row.values}
        if "overall" not in lower_values:
            continue
        for col in ("acc", "accuracy", "Accuracy (%)", "score", "Score", "Overall", "overall", "average_scores"):
            if col in row:
                parsed = _score_to_percent(row[col])
                if parsed is not None:
                    scores["Overall"] = parsed
                    return scores
        for col, value in row.items():
            if str(value).strip().lower() == "overall":
                continue
            parsed = _score_to_percent(value)
            if parsed is not None:
                scores["Overall"] = parsed
                return scores
    for col in ("Overall", "overall", "acc", "accuracy", "Score", "score", "Score (Strict)", "Score (Loose)"):
        if col in result.columns:
            vals = [_score_to_percent(v) for v in result[col]]
            vals = [v for v in vals if v is not None]
            if vals:
                scores["Overall"] = sum(vals) / len(vals)
                return scores
    return scores


def _normalize_eval_result(result: Any) -> dict[str, Any]:
    if isinstance(result, pd.DataFrame):
        return _df_to_scores(result)
    if isinstance(result, dict):
        return result
    return {"raw": str(result)}


def _primary_score(scores: dict[str, Any]) -> float | None:
    for key in ("Overall", "overall", "accuracy", "acc", "score", "Score", "Overall_Accuracy", "Accuracy (%)"):
        if key in scores:
            parsed = _score_to_percent(scores[key])
            if parsed is not None:
                return parsed
    table = scores.get("table")
    if isinstance(table, list):
        nested = _df_to_scores(pd.DataFrame(table))
        for key in ("Overall", "acc", "accuracy"):
            if key in nested:
                return _score_to_percent(nested[key])
    numeric = []
    for key, value in scores.items():
        if key in {"table", "raw", "rows", "samples"}:
            continue
        parsed = _score_to_percent(value)
        if parsed is not None:
            numeric.append(parsed)
    return sum(numeric) / len(numeric) if numeric else None


def run_vlmeval_evaluate(args: Any) -> dict[str, Any]:
    from vlmeval.dataset import build_dataset

    dataset = build_dataset(args.dataset)
    if dataset is None:
        raise RuntimeError(f"VLMEvalKit could not build dataset {args.dataset}")
    output_dir = Path(args.output_dir)
    pred_table = output_dir / f"{args.dataset}_predictions.xlsx"
    if not pred_table.exists():
        raise FileNotFoundError(pred_table)

    judge_kwargs = {"model": args.eval_judge_model, "nproc": args.eval_nproc}
    result = dataset.evaluate(str(pred_table), **judge_kwargs)
    scores = _normalize_eval_result(result)
    score = _primary_score(scores)
    rows = len(load(str(pred_table)))
    summary = {
        "dataset": args.dataset,
        "model": args.model,
        "rows": rows,
        "score": score,
        "scores": scores,
        "artifacts": {
            "prediction_table": str(pred_table),
        },
    }
    _write_json(output_dir / "scores.json", summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=_json_default))
    return summary


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=_json_default), encoding="utf-8")
    tmp.replace(path)


def _run_local_text_judge(
    args: Any,
    *,
    prompts: list[tuple[str, str]],
    cache_name: str,
    max_tokens: int | None = None,
    temperature: float = 0.0,
    top_p: float = 1.0,
) -> dict[str, dict[str, Any]]:
    del args, prompts, cache_name, max_tokens, temperature, top_p
    raise RuntimeError("A persistent local judge must monkey-patch _run_local_text_judge")


def _build_summary(
    *,
    output_dir: Path,
    dataset: str,
    model: str,
    rows: int,
    scores: Any,
    artifacts: dict[str, Any],
) -> dict[str, Any]:
    norm_scores = _normalize_eval_result(scores)
    summary = {
        "dataset": dataset,
        "model": model,
        "rows": rows,
        "score": _primary_score(norm_scores),
        "scores": norm_scores,
        "artifacts": artifacts,
    }
    _write_json(output_dir / "scores.json", summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=_json_default))
    return summary


def run_mathv_local_judge(args: Any) -> dict[str, Any]:
    from vlmeval.dataset.utils.mathv import MATH_V_acc, build_mathv_gpt4_prompt, post_check

    output_dir = Path(args.output_dir)
    pred_table = output_dir / f"{args.dataset}_predictions.xlsx"
    data = load(str(pred_table))
    prompts = []
    rows: list[dict[str, Any]] = []
    for _, row in data.iterrows():
        row = row.copy()
        try:
            prefetched = post_check(row, prefetch=True)
        except Exception:
            prefetched = False
        if prefetched:
            row["res"] = prefetched
            row["log"] = "Prefetch succeed"
        else:
            prompts.append((str(row["index"]), build_mathv_gpt4_prompt(row)))
            row["res"] = ""
            row["log"] = "Pending local judge"
        rows.append(row.to_dict())
    judged = _run_local_text_judge(args, prompts=prompts, cache_name="mathvision_qwen3_32b_extract.jsonl", max_tokens=128)
    for row in rows:
        if row["log"] == "Pending local judge":
            item = judged.get(str(row["index"]), {})
            row["res"] = str(item.get("judge_output", "")).strip()
            row["log"] = "Succeed" if row["res"] else "Local judge empty"
    judged_table = output_dir / f"{args.dataset}_judged_qwen3_32b.xlsx"
    pd.DataFrame(rows).to_excel(judged_table, index=False)
    score = MATH_V_acc(str(judged_table))
    dump(score, str(get_intermediate_file_path(str(judged_table), "_score", "csv")))
    return _build_summary(
        output_dir=output_dir,
        dataset=args.dataset,
        model=args.model,
        rows=len(rows),
        scores=score,
        artifacts={"prediction_table": str(pred_table), "judged_table": str(judged_table)},
    )


def run_mathvista_local_judge(args: Any) -> dict[str, Any]:
    from vlmeval.dataset.utils.mathvista import MathVista_acc, build_mathvista_gpt4_prompt, post_check

    output_dir = Path(args.output_dir)
    pred_table = output_dir / f"{args.dataset}_predictions.xlsx"
    data = load(str(pred_table))
    prompts = []
    rows: list[dict[str, Any]] = []
    for _, row in data.iterrows():
        row = row.copy()
        try:
            prefetched = post_check(row, prefetch=True)
        except Exception:
            prefetched = False
        if prefetched:
            row["res"] = prefetched
            row["log"] = "Prefetch succeed"
        else:
            prompts.append((str(row["index"]), build_mathvista_gpt4_prompt(row)))
            row["res"] = ""
            row["log"] = "Pending local judge"
        rows.append(row.to_dict())
    judged = _run_local_text_judge(args, prompts=prompts, cache_name="mathvista_qwen3_32b_extract.jsonl", max_tokens=128)
    for row in rows:
        if row["log"] == "Pending local judge":
            item = judged.get(str(row["index"]), {})
            row["res"] = str(item.get("judge_output", "")).strip()
            row["log"] = "Succeed" if row["res"] else "Local judge empty"
    judged_table = output_dir / f"{args.dataset}_judged_qwen3_32b.xlsx"
    pd.DataFrame(rows).to_excel(judged_table, index=False)
    score = MathVista_acc(str(judged_table))
    dump(score, str(get_intermediate_file_path(str(judged_table), "_score", "csv")))
    return _build_summary(
        output_dir=output_dir,
        dataset=args.dataset,
        model=args.model,
        rows=len(rows),
        scores=score,
        artifacts={"prediction_table": str(pred_table), "judged_table": str(judged_table)},
    )


def run_mathverse_local_judge(args: Any) -> dict[str, Any]:
    from vlmeval.dataset.utils.mathverse import (
        MathVerse_acc,
        build_mathverse_gpt4_extract_prompt,
        build_mathverse_gpt4_score_prompt,
        post_check_score,
    )

    output_dir = Path(args.output_dir)
    pred_table = output_dir / f"{args.dataset}_predictions.xlsx"
    data = load(str(pred_table))
    extract_prompts = [(str(row["index"]), build_mathverse_gpt4_extract_prompt(row)) for _, row in data.iterrows()]
    extracted = _run_local_text_judge(
        args,
        prompts=extract_prompts,
        cache_name="mathverse_qwen3_32b_extract.jsonl",
        max_tokens=128,
    )
    rows = []
    score_prompts = []
    for _, row in data.iterrows():
        row = row.copy()
        row["extract"] = str(extracted.get(str(row["index"]), {}).get("judge_output", "")).strip()
        row["log_extract"] = "Succeed" if row["extract"] else "Local judge empty"
        try:
            prefetched = post_check_score(row, prefetch=True)
        except Exception:
            prefetched = False
        if prefetched:
            row["score"] = True
            row["log_score"] = "Prefetch succeed"
        else:
            score_prompts.append((str(row["index"]), build_mathverse_gpt4_score_prompt(row)))
            row["score"] = False
            row["log_score"] = "Pending local judge"
        rows.append(row.to_dict())
    scored = _run_local_text_judge(
        args,
        prompts=score_prompts,
        cache_name="mathverse_qwen3_32b_score.jsonl",
        max_tokens=16,
    )
    for row in rows:
        if row["log_score"] == "Pending local judge":
            out = str(scored.get(str(row["index"]), {}).get("judge_output", "")).strip()
            row["score"] = out[:1] == "1"
            row["log_score"] = f"Judge output: {out}"
    judged_table = output_dir / f"{args.dataset}_judged_qwen3_32b.xlsx"
    pd.DataFrame(rows).to_excel(judged_table, index=False)
    score = MathVerse_acc(str(judged_table))
    dump(score, str(get_intermediate_file_path(str(judged_table), "_score", "csv")))
    return _build_summary(
        output_dir=output_dir,
        dataset=args.dataset,
        model=args.model,
        rows=len(rows),
        scores=score,
        artifacts={"prediction_table": str(pred_table), "judged_table": str(judged_table)},
    )


def run_logicvista_local_judge(args: Any) -> dict[str, Any]:
    from vlmeval.dataset.utils.logicvista import build_prompt_logicvista, evaluate_logicvista

    output_dir = Path(args.output_dir)
    pred_table = output_dir / f"{args.dataset}_predictions.xlsx"
    data = load(str(pred_table))
    prompts = [(str(row["index"]), build_prompt_logicvista(row)) for _, row in data.iterrows()]
    judged = _run_local_text_judge(args, prompts=prompts, cache_name="logicvista_qwen3_32b_extract.jsonl", max_tokens=16)
    rows = []
    for _, row in data.iterrows():
        item = judged.get(str(row["index"]), {})
        res = re.sub(r"[^A-Za-z]", "", str(item.get("judge_output", "")).upper())
        answer = sorted([x.strip().lower() for x in str(row["answer"]).split(",") if x.strip()])
        extracted = sorted([x.lower() for x in res])
        out = row.to_dict()
        out["res"] = res
        out["log"] = "Succeed" if res else "Local judge empty"
        out["hit"] = int("".join(extracted) == "".join(answer))
        rows.append(out)
    judged_table = output_dir / f"{args.dataset}_judged_qwen3_32b.xlsx"
    pd.DataFrame(rows).to_excel(judged_table, index=False)
    score = evaluate_logicvista(str(judged_table))
    dump(score, str(get_intermediate_file_path(str(judged_table), "_score", "csv")))
    return _build_summary(
        output_dir=output_dir,
        dataset=args.dataset,
        model=args.model,
        rows=len(rows),
        scores=score,
        artifacts={"prediction_table": str(pred_table), "judged_table": str(judged_table)},
    )


def run_seephys_local_judge(args: Any) -> dict[str, Any]:
    from vlmeval.dataset.utils.seephys import build_extract_prompt, eval_acc, post_check, prompt_scoring

    output_dir = Path(args.output_dir)
    pred_table = output_dir / f"{args.dataset}_predictions.xlsx"
    data = load(str(pred_table))
    rows = []
    extract_prompts = []
    for _, row in data.iterrows():
        row = row.copy()
        try:
            prefetched = post_check(row, prefetch=True)
        except Exception:
            prefetched = False
        if prefetched:
            row["extract"] = prefetched
            row["score"] = 1
            row["log"] = "Prefetch succeed"
        else:
            extract_prompts.append((str(row["index"]), build_extract_prompt(row)))
            row["extract"] = ""
            row["score"] = -1
            row["log"] = "Pending extract"
        rows.append(row.to_dict())
    extracted = _run_local_text_judge(args, prompts=extract_prompts, cache_name="seephys_qwen3_32b_extract.jsonl", max_tokens=128)
    score_prompts = []
    for row in rows:
        if row["log"] == "Pending extract":
            row["extract"] = str(extracted.get(str(row["index"]), {}).get("judge_output", "")).strip()
            if row["extract"]:
                query = "Please answer this question in the image." if str(row.get("question")) == "nan" else str(row.get("question", ""))
                prompt = prompt_scoring.strip() + (
                    f"\n[Question]: {query}\n[Standard Answer]: {row.get('answer', '')}\n"
                    f"[Model Answer]: {row['extract']}\nJudgement: "
                )
                score_prompts.append((str(row["index"]), prompt))
            else:
                row["score"] = 0
                row["log"] = "Local extract empty"
    scored = _run_local_text_judge(args, prompts=score_prompts, cache_name="seephys_qwen3_32b_score.jsonl", max_tokens=16)
    for row in rows:
        if row["log"] == "Pending extract" and row["extract"]:
            out = str(scored.get(str(row["index"]), {}).get("judge_output", "")).strip()
            m = re.search(r"\b([01])\b", out)
            row["score"] = int(m.group(1)) if m else 0
            row["log"] = f"Judge output: {out}"
    judged_table = output_dir / f"{args.dataset}_judged_qwen3_32b.xlsx"
    pd.DataFrame(rows).to_excel(judged_table, index=False)
    score = eval_acc(str(judged_table))
    return _build_summary(
        output_dir=output_dir,
        dataset=args.dataset,
        model=args.model,
        rows=len(rows),
        scores=score,
        artifacts={"prediction_table": str(pred_table), "judged_table": str(judged_table)},
    )


def run_physics_local_judge(args: Any) -> dict[str, Any]:
    from vlmeval.dataset.utils.physic import PHYSIC_acc
    from vlmeval.dataset.utils.physics_eval_utils import extract_final_answer_allform

    output_dir = Path(args.output_dir)
    pred_table = output_dir / f"{args.dataset}_predictions.xlsx"
    data = load(str(pred_table))
    rows = []
    prompts = []
    for _, row in data.iterrows():
        row = row.copy()
        preds = extract_final_answer_allform(str(row.get("prediction", "")))
        flat = [str(x).strip() for x in preds if str(x).strip()]
        gt = str(row.get("answer", "")).strip()
        if gt and any(p == gt for p in flat):
            row["res"] = 1.0
            row["log"] = "Exact boxed match"
        elif flat:
            prompt = (
                "Compare the model answer to the standard answer for this physics problem. "
                "Return only True or False.\n\n"
                f"Question: {row.get('question', '')}\n"
                f"Standard answer: {gt}\n"
                f"Model answer: {flat[0]}\n"
                "Equivalent:"
            )
            prompts.append((str(row["index"]), prompt))
            row["res"] = 0.0
            row["log"] = "Pending local judge"
        else:
            row["res"] = 0.0
            row["log"] = "No boxed answer"
        rows.append(row.to_dict())
    judged = _run_local_text_judge(args, prompts=prompts, cache_name="physics_qwen3_32b_score.jsonl", max_tokens=16)
    for row in rows:
        if row["log"] == "Pending local judge":
            out = str(judged.get(str(row["index"]), {}).get("judge_output", "")).strip().lower()
            row["res"] = 1.0 if "true" in out or out.startswith("yes") else 0.0
            row["log"] = f"Judge output: {out}"
    judged_table = output_dir / f"{args.dataset}_judged_qwen3_32b.xlsx"
    pd.DataFrame(rows).to_excel(judged_table, index=False)
    score = PHYSIC_acc(str(judged_table))
    dump(score, str(get_intermediate_file_path(str(judged_table), "_score", "csv")))
    return _build_summary(
        output_dir=output_dir,
        dataset=args.dataset,
        model=args.model,
        rows=len(rows),
        scores=score,
        artifacts={"prediction_table": str(pred_table), "judged_table": str(judged_table)},
    )


def _parse_charxiv_judge(text: str) -> dict[str, Any]:
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            score = float(obj.get("score", 0.0))
            extracted = obj.get("extracted_answer", obj.get("extract_answer", ""))
            return {"score": score, "extract_answer": extracted}
    except Exception:
        pass
    score_match = re.search(r'"?score"?\s*[:=]\s*([01](?:\.\d+)?)', text, flags=re.I)
    if score_match:
        score = float(score_match.group(1))
    elif re.search(r"\b(correct|yes|true)\b", text, flags=re.I):
        score = 1.0
    else:
        score = 0.0
    extracted_match = re.search(r'"?(?:extracted_answer|extract_answer)"?\s*[:=]\s*"?([^"\n}]+)', text, flags=re.I)
    extracted = extracted_match.group(1).strip() if extracted_match else ""
    return {"score": score, "extract_answer": extracted}

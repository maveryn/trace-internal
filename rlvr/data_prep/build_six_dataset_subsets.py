#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd
from datasets import Dataset, Sequence
from datasets import Image as HFImage
from PIL import Image


MAX_DIFF_DEFAULT = 0.002  # 0.2 percentage points
SEED_MAX_DEFAULT = 50000
SUBSET_N_DEFAULT = 500

MODEL_QWEN = "Qwen2.5-VL-3B-Instruct"
MODEL_SPHINX = "Sphinx_Qwen25VL3B"


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    return str(value).strip()


def _strip_image_tokens(text: str) -> str:
    s = _as_text(text)
    if not s:
        return s
    s = s.replace("<image>", "")
    s = re.sub(r"<image\d+>", "", s)
    return s.strip()


def _open_image_file(path: Path) -> Image.Image:
    img = Image.open(path)
    img.load()
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img


def _decode_image_b64(value: str) -> Image.Image:
    text = _as_text(value)
    if not text:
        raise ValueError("empty image field")
    text = re.sub(r"^data:image/[^;]+;base64,", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", "", text)
    if len(text) % 4 != 0:
        text += "=" * (4 - (len(text) % 4))
    try:
        raw = base64.b64decode(text, validate=False)
    except Exception:
        raw = base64.urlsafe_b64decode(text)
    img = Image.open(BytesIO(raw))
    img.load()
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img


def _load_image_general(value: Any) -> Image.Image:
    text = _as_text(value)
    if not text:
        raise ValueError("empty image field")

    if len(text) <= 512 and ("/" in text or "\\" in text):
        try:
            maybe_path = Path(text).expanduser()
            if maybe_path.exists() and maybe_path.is_file():
                return _open_image_file(maybe_path)
        except OSError:
            pass
    return _decode_image_b64(text)


def _load_image_spatialeval(value: Any, image_root: Path) -> Image.Image:
    text = _as_text(value)
    if not text:
        raise ValueError("empty image field")

    if re.fullmatch(r"[A-Za-z0-9_.-]+", text):
        cand = image_root / f"{text}.jpg"
        if cand.exists():
            return _open_image_file(cand)

    if len(text) <= 255 and ("/" in text or "\\" in text or "." in text):
        try:
            maybe_path = Path(text).expanduser()
            if maybe_path.exists() and maybe_path.is_file():
                return _open_image_file(maybe_path)
        except OSError:
            pass

    return _decode_image_b64(text)


def _extract_options(row: pd.Series) -> dict[str, str]:
    options: dict[str, str] = {}
    for key in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        if key in row.index:
            val = _as_text(row.get(key))
            if val and val.lower() != "nan":
                options[key] = val
    return options


def _format_image_mcq_prompt(row: pd.Series) -> str:
    question = _strip_image_tokens(row.get("question"))
    hint = _as_text(row.get("hint"))
    options = _extract_options(row)

    prompt = ""
    if hint:
        prompt += f"Hint: {hint}\n"
    prompt += f"Question: {question}\n"
    if options:
        prompt += "Options:\n"
        for k, v in options.items():
            prompt += f"{k}. {v}\n"
        prompt += "Please select the correct answer from the options above. \n"
    return f"<image>{prompt}"


def _format_visnumbench_prompt(row: pd.Series) -> str:
    question = _strip_image_tokens(row.get("question"))
    options = _extract_options(row)
    hint_letters = "A, B, C, D, E" if "E" in options else "A, B, C, D"

    prompt = (
        f"Hint: Please answer the question and provide the correct option letter, e.g., {hint_letters}, at the end.\n"
        f"Question: {question}\n"
    )
    if options:
        prompt += "Choices:\n"
        for k, v in options.items():
            prompt += f"({k}) {v}\n"
    prompt += "Please select the correct answer from the options above."
    return f"<image>{prompt}"


def _format_mathvision_prompt(row: pd.Series) -> str:
    question = _strip_image_tokens(row.get("question"))
    return f"<image>{question}"


def _format_logicvista_prompt(row: pd.Series) -> str:
    question = _strip_image_tokens(row.get("question"))
    return f"<image>{question}"


def _normalize_answer(dataset_key: str, row: pd.Series) -> str:
    answer = _as_text(row.get("answer"))
    if dataset_key in {"spatialeval", "visnumbench", "vstarbench", "mmstar"}:
        return answer.upper()
    return answer


def _build_mathvision_hits(df: pd.DataFrame, vlmeval_root: Path) -> pd.Series:
    if str(vlmeval_root) not in sys.path:
        sys.path.append(str(vlmeval_root))
    from vlmeval.dataset.utils.mathv import post_check

    return pd.Series([1 if post_check(row.to_dict(), prefetch=False) else 0 for _, row in df.iterrows()])


def _coerce_hit_col(df: pd.DataFrame) -> pd.Series:
    if "hit" not in df.columns:
        raise ValueError("missing hit column")
    hit = pd.to_numeric(df["hit"], errors="coerce")
    if hit.notna().mean() >= 0.8:
        return hit.fillna(0).astype(float)
    m = {"true": 1.0, "false": 0.0, "True": 1.0, "False": 0.0}
    return df["hit"].map(m).fillna(0).astype(float)


def _select_subset(
    merged: pd.DataFrame,
    sample_n: int,
    max_diff: float,
    seed_max: int,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    total_n = len(merged)
    q_full = float(merged["q_hit"].mean())
    s_full = float(merged["s_hit"].mean())
    gap_full = s_full - q_full

    if total_n <= sample_n:
        chosen = merged.copy().reset_index(drop=True)
        q_hits = float(chosen["q_hit"].sum())
        s_hits = float(chosen["s_hit"].sum())
        q_acc = q_hits / total_n if total_n else 0.0
        s_acc = s_hits / total_n if total_n else 0.0
        meta = {
            "sample_count": int(total_n),
            "seed": "ALL",
            "within_tolerance": True,
            "max_diff": max_diff,
            "qwen_full_acc": q_full,
            "sphinx_full_acc": s_full,
            "gap_full": gap_full,
            "qwen_subset_acc": q_acc,
            "sphinx_subset_acc": s_acc,
            "gap_subset": s_acc - q_acc,
            "qwen_diff": abs(q_acc - q_full),
            "sphinx_diff": abs(s_acc - s_full),
            "gap_diff": abs((s_acc - q_acc) - gap_full),
            "max_diff_achieved": max(abs(q_acc - q_full), abs(s_acc - s_full)),
            "sum_diff_achieved": abs(q_acc - q_full) + abs(s_acc - s_full),
            "qwen_hit": float(q_hits),
            "sphinx_hit": float(s_hits),
            "seed_max": seed_max,
            "used_all": True,
        }
        return chosen, meta

    best_ok: tuple[float, float, float, int, float, float, int, int] | None = None
    best_any: tuple[float, float, float, int, float, float, int, int] | None = None
    for seed in range(seed_max):
        sample = merged.sample(n=sample_n, random_state=seed)
        q_hits = int(sample["q_hit"].sum())
        s_hits = int(sample["s_hit"].sum())
        q_acc = q_hits / sample_n
        s_acc = s_hits / sample_n
        q_diff = abs(q_acc - q_full)
        s_diff = abs(s_acc - s_full)
        gap_diff = abs((s_acc - q_acc) - gap_full)
        row = (gap_diff, max(q_diff, s_diff), q_diff + s_diff, seed, q_acc, s_acc, q_hits, s_hits)
        if best_any is None or row < best_any:
            best_any = row
        if q_diff <= max_diff and s_diff <= max_diff:
            if best_ok is None or row < best_ok:
                best_ok = row

    if best_any is None:
        raise RuntimeError("subset search failed: no candidate found")
    if best_ok is None:
        raise RuntimeError(
            f"no subset found within tolerance max_diff={max_diff} using {seed_max} seeds (sample_n={sample_n})"
        )

    (
        chosen_gap_diff,
        chosen_max_diff,
        chosen_sum_diff,
        chosen_seed,
        chosen_q_acc,
        chosen_s_acc,
        chosen_q_hits,
        chosen_s_hits,
    ) = best_ok
    chosen = merged.sample(n=sample_n, random_state=chosen_seed).reset_index(drop=True)
    meta = {
        "sample_count": sample_n,
        "seed": int(chosen_seed),
        "within_tolerance": True,
        "max_diff": max_diff,
        "qwen_full_acc": q_full,
        "sphinx_full_acc": s_full,
        "gap_full": gap_full,
        "qwen_subset_acc": chosen_q_acc,
        "sphinx_subset_acc": chosen_s_acc,
        "gap_subset": chosen_s_acc - chosen_q_acc,
        "qwen_diff": abs(chosen_q_acc - q_full),
        "sphinx_diff": abs(chosen_s_acc - s_full),
        "gap_diff": chosen_gap_diff,
        "max_diff_achieved": chosen_max_diff,
        "sum_diff_achieved": chosen_sum_diff,
        "qwen_hit": int(chosen_q_hits),
        "sphinx_hit": int(chosen_s_hits),
        "seed_max": seed_max,
        "used_all": False,
    }
    return chosen, meta


def _compute_strict_metrics(df: pd.DataFrame, strict_score_response) -> dict[str, float]:
    total = len(df)
    extracted = 0
    hit = 0.0
    for _, row in df.iterrows():
        score, is_extracted, _, _ = strict_score_response(str(row.get("prediction", "")), row.get("answer", ""))
        hit += float(score)
        if is_extracted:
            extracted += 1
    return {
        "total": float(total),
        "extracted": float(extracted),
        "hit": float(hit),
        "extraction_rate_pct": (100.0 * extracted / total) if total else 0.0,
        "acc_on_extracted_pct": (100.0 * hit / extracted) if extracted else 0.0,
    }


def _build_examples_text(dataset_to_parquet: dict[str, Path], out_file: Path) -> None:
    lines: list[str] = []
    sep = "#" * 80
    for ds_name, pq_path in dataset_to_parquet.items():
        df = pd.read_parquet(pq_path)
        n = len(df)
        rows = list(range(min(5, n)))
        lines.append(sep)
        lines.append(f"DATASET: {ds_name}")
        lines.append(f"PARQUET: {pq_path.name}")
        lines.append(f"ROWS: {n}")
        lines.append(sep)
        for i, ridx in enumerate(rows, start=1):
            prompt = _as_text(df.iloc[ridx]["problem"])
            answer = _as_text(df.iloc[ridx]["answer"])
            lines.append(f"--- EXAMPLE {i} (row_index={ridx}) ---")
            lines.append("PROMPT:")
            lines.append(prompt)
            lines.append("")
            lines.append("ANSWER:")
            lines.append(answer)
            lines.append("-" * 80)
            lines.append("")
        lines.append("")
    out_file.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build RLVR parquet subsets for SpatialEval/VisNumBench/VStarBench/"
            "MMStar/MathVision/LogicVista, and emit examples + metrics report."
        )
    )
    parser.add_argument("--subset-n", type=int, default=SUBSET_N_DEFAULT, help="Target subset size")
    parser.add_argument("--max-diff", type=float, default=MAX_DIFF_DEFAULT, help="Tolerance in [0,1] units")
    parser.add_argument("--seed-max", type=int, default=SEED_MAX_DEFAULT, help="Max random seeds to search")
    args = parser.parse_args()

    tess_root = Path(__file__).resolve().parents[1]
    mydata_dir = tess_root / "mydata"
    mydata_dir.mkdir(parents=True, exist_ok=True)
    vlmeval_root = Path.home() / "work" / "vlmeval"
    if str(tess_root) not in sys.path:
        sys.path.append(str(tess_root))
    from verl.utils.local_strict_eval import strict_score_response

    dataset_cfgs = [
        {
            "key": "spatialeval",
            "name": "SpatialEval",
            "source_tsv": Path.home() / "LMUData" / "SpatialEval.tsv",
            "image_mode": "spatialeval",
            "image_root": Path.home() / "LMUData" / "images" / "SpatialEval",
            "prompt_mode": "image_mcq",
            "out_parquet": mydata_dir / "spatialeval_test_500.parquet",
            "meta_json": mydata_dir / "spatialeval_test_500_subset_meta.json",
            "qwen_pred": Path.home()
            / "work"
            / "vlmeval"
            / "outputs"
            / MODEL_QWEN
            / f"{MODEL_QWEN}_SpatialEval.xlsx",
            "sphinx_pred": Path.home()
            / "work"
            / "vlmeval"
            / "outputs"
            / MODEL_SPHINX
            / f"{MODEL_SPHINX}_SpatialEval.xlsx",
            "qwen_gpt": Path.home()
            / "work"
            / "vlmeval"
            / "outputs"
            / MODEL_QWEN
            / "T20260228_G5a302e46"
            / f"{MODEL_QWEN}_SpatialEval_openai_result.xlsx",
            "sphinx_gpt": Path.home()
            / "work"
            / "vlmeval"
            / "outputs"
            / MODEL_SPHINX
            / "T20260228_G5a302e46"
            / f"{MODEL_SPHINX}_SpatialEval_openai_result.xlsx",
            "gpt_mode": "hit",
        },
        {
            "key": "visnumbench",
            "name": "VisNumBench",
            "source_tsv": Path.home() / "LMUData" / "VisNumBench.tsv",
            "image_mode": "base64",
            "prompt_mode": "visnumbench",
            "out_parquet": mydata_dir / "visnumbench_val_500.parquet",
            "meta_json": mydata_dir / "visnumbench_val_500_subset_meta.json",
            "qwen_pred": Path.home()
            / "work"
            / "vlmeval"
            / "outputs"
            / MODEL_QWEN
            / f"{MODEL_QWEN}_VisNumBench.xlsx",
            "sphinx_pred": Path.home()
            / "work"
            / "vlmeval"
            / "outputs"
            / MODEL_SPHINX
            / f"{MODEL_SPHINX}_VisNumBench.xlsx",
            "qwen_gpt": Path.home()
            / "work"
            / "vlmeval"
            / "outputs"
            / MODEL_QWEN
            / f"{MODEL_QWEN}_VisNumBench_openai_result.xlsx",
            "sphinx_gpt": Path.home()
            / "work"
            / "vlmeval"
            / "outputs"
            / MODEL_SPHINX
            / f"{MODEL_SPHINX}_VisNumBench_openai_result.xlsx",
            "gpt_mode": "hit",
        },
        {
            "key": "vstarbench",
            "name": "VStarBench",
            "source_tsv": Path.home() / "LMUData" / "VStarBench.tsv",
            "image_mode": "base64",
            "prompt_mode": "image_mcq",
            "out_parquet": mydata_dir / "vstarbench_test.parquet",
            "meta_json": mydata_dir / "vstarbench_test_subset_meta.json",
            "qwen_pred": Path.home()
            / "work"
            / "vlmeval"
            / "outputs"
            / MODEL_QWEN
            / f"{MODEL_QWEN}_VStarBench.xlsx",
            "sphinx_pred": Path.home()
            / "work"
            / "vlmeval"
            / "outputs"
            / MODEL_SPHINX
            / f"{MODEL_SPHINX}_VStarBench.xlsx",
            "qwen_gpt": Path.home()
            / "work"
            / "vlmeval"
            / "outputs"
            / MODEL_QWEN
            / f"{MODEL_QWEN}_VStarBench_openai_result.xlsx",
            "sphinx_gpt": Path.home()
            / "work"
            / "vlmeval"
            / "outputs"
            / MODEL_SPHINX
            / f"{MODEL_SPHINX}_VStarBench_openai_result.xlsx",
            "gpt_mode": "hit",
        },
        {
            "key": "mmstar",
            "name": "MMStar",
            "source_tsv": Path.home() / "LMUData" / "MMStar.tsv",
            "image_mode": "base64",
            "prompt_mode": "image_mcq",
            "out_parquet": mydata_dir / "mmstar_test_500.parquet",
            "meta_json": mydata_dir / "mmstar_test_500_subset_meta.json",
            "qwen_pred": Path.home()
            / "work"
            / "vlmeval"
            / "outputs"
            / MODEL_QWEN
            / f"{MODEL_QWEN}_MMStar.xlsx",
            "sphinx_pred": Path.home()
            / "work"
            / "vlmeval"
            / "outputs"
            / MODEL_SPHINX
            / f"{MODEL_SPHINX}_MMStar.xlsx",
            "qwen_gpt": Path.home()
            / "work"
            / "vlmeval"
            / "outputs"
            / MODEL_QWEN
            / "T20260228_G5a302e46"
            / f"{MODEL_QWEN}_MMStar_openai_result.xlsx",
            "sphinx_gpt": Path.home()
            / "work"
            / "vlmeval"
            / "outputs"
            / MODEL_SPHINX
            / "T20260228_G5a302e46"
            / f"{MODEL_SPHINX}_MMStar_openai_result.xlsx",
            "gpt_mode": "hit",
        },
        {
            "key": "mathvision",
            "name": "MathVision",
            "source_tsv": Path.home() / "LMUData" / "MathVision.tsv",
            "image_mode": "base64",
            "prompt_mode": "mathvision",
            "out_parquet": mydata_dir / "mathvision_test_500.parquet",
            "meta_json": mydata_dir / "mathvision_test_500_subset_meta.json",
            "qwen_pred": Path.home()
            / "work"
            / "vlmeval"
            / "outputs"
            / MODEL_QWEN
            / f"{MODEL_QWEN}_MathVision.xlsx",
            "sphinx_pred": Path.home()
            / "work"
            / "vlmeval"
            / "outputs"
            / MODEL_SPHINX
            / f"{MODEL_SPHINX}_MathVision.xlsx",
            "qwen_gpt": Path.home()
            / "work"
            / "vlmeval"
            / "outputs"
            / MODEL_QWEN
            / "T20260227_G5a302e46"
            / f"{MODEL_QWEN}_MathVision_gpt-4o-mini.xlsx",
            "sphinx_gpt": Path.home()
            / "work"
            / "vlmeval"
            / "outputs"
            / MODEL_SPHINX
            / "T20260228_G5a302e46"
            / f"{MODEL_SPHINX}_MathVision_gpt-4o-mini.xlsx",
            "gpt_mode": "mathvision",
        },
        {
            "key": "logicvista",
            "name": "LogicVista",
            "source_tsv": Path.home() / "LMUData" / "LogicVista.tsv",
            "image_mode": "base64",
            "prompt_mode": "logicvista",
            "out_parquet": mydata_dir / "logicvista_test.parquet",
            "meta_json": mydata_dir / "logicvista_test_subset_meta.json",
            "qwen_pred": Path.home()
            / "work"
            / "vlmeval"
            / "outputs"
            / MODEL_QWEN
            / f"{MODEL_QWEN}_LogicVista.xlsx",
            "sphinx_pred": Path.home()
            / "work"
            / "vlmeval"
            / "outputs"
            / MODEL_SPHINX
            / f"{MODEL_SPHINX}_LogicVista.xlsx",
            "qwen_gpt": Path.home()
            / "work"
            / "vlmeval"
            / "outputs"
            / MODEL_QWEN
            / f"{MODEL_QWEN}_LogicVista_gpt4o-mini.xlsx",
            "sphinx_gpt": Path.home()
            / "work"
            / "vlmeval"
            / "outputs"
            / MODEL_SPHINX
            / f"{MODEL_SPHINX}_LogicVista_gpt4o-mini.xlsx",
            "gpt_mode": "hit",
        },
    ]

    report_rows: list[dict[str, Any]] = []
    dataset_to_parquet: dict[str, Path] = {}

    for cfg in dataset_cfgs:
        name = cfg["name"]
        print(f"[{name}] loading source + eval files")
        src_df = pd.read_csv(cfg["source_tsv"], sep="\t")
        src_df["index"] = src_df["index"].astype(str)

        q_pred_df = pd.read_excel(cfg["qwen_pred"])
        s_pred_df = pd.read_excel(cfg["sphinx_pred"])
        q_pred_df["index"] = q_pred_df["index"].astype(str)
        s_pred_df["index"] = s_pred_df["index"].astype(str)

        q_gpt_df = pd.read_excel(cfg["qwen_gpt"])
        s_gpt_df = pd.read_excel(cfg["sphinx_gpt"])
        q_gpt_df["index"] = q_gpt_df["index"].astype(str)
        s_gpt_df["index"] = s_gpt_df["index"].astype(str)

        if cfg["gpt_mode"] == "mathvision":
            q_hit = _build_mathvision_hits(q_gpt_df, vlmeval_root)
            s_hit = _build_mathvision_hits(s_gpt_df, vlmeval_root)
        else:
            q_hit = _coerce_hit_col(q_gpt_df)
            s_hit = _coerce_hit_col(s_gpt_df)

        q_hits_df = pd.DataFrame({"index": q_gpt_df["index"], "q_hit": q_hit.astype(float)})
        s_hits_df = pd.DataFrame({"index": s_gpt_df["index"], "s_hit": s_hit.astype(float)})
        merged = q_hits_df.merge(s_hits_df, on="index", how="inner")

        selected, meta = _select_subset(
            merged=merged,
            sample_n=args.subset_n,
            max_diff=args.max_diff,
            seed_max=args.seed_max,
        )
        selected_indices = selected["index"].tolist()
        selected_set = set(selected_indices)

        lookup = src_df.set_index("index")
        subset_src = lookup.loc[selected_indices].reset_index()

        rows: list[dict[str, Any]] = []
        for _, row in subset_src.iterrows():
            if cfg["image_mode"] == "spatialeval":
                image = _load_image_spatialeval(row.get("image"), cfg["image_root"])
            else:
                image = _load_image_general(row.get("image"))

            if cfg["prompt_mode"] == "image_mcq":
                problem = _format_image_mcq_prompt(row)
            elif cfg["prompt_mode"] == "visnumbench":
                problem = _format_visnumbench_prompt(row)
            elif cfg["prompt_mode"] == "mathvision":
                problem = _format_mathvision_prompt(row)
            elif cfg["prompt_mode"] == "logicvista":
                problem = _format_logicvista_prompt(row)
            else:
                raise ValueError(f"Unsupported prompt_mode: {cfg['prompt_mode']}")

            answer = _normalize_answer(cfg["key"], row)
            rows.append({"images": [image], "problem": problem, "answer": answer})

        ds = Dataset.from_list(rows)
        ds = ds.cast_column("images", Sequence(HFImage()))
        ds.to_parquet(str(cfg["out_parquet"]))

        meta.update(
            {
                "dataset": name,
                "mode": "gpt_match_full",
                "source_tsv": str(cfg["source_tsv"]),
                "qwen_pred_file": str(cfg["qwen_pred"]),
                "sphinx_pred_file": str(cfg["sphinx_pred"]),
                "qwen_eval_file": str(cfg["qwen_gpt"]),
                "sphinx_eval_file": str(cfg["sphinx_gpt"]),
                "parquet_file": str(cfg["out_parquet"]),
            }
        )
        cfg["meta_json"].write_text(json.dumps(meta, ensure_ascii=True, indent=2), encoding="utf-8")
        dataset_to_parquet[name] = cfg["out_parquet"]

        # Report: GPT full/subset + Tess strict full/subset.
        q_full_df = q_pred_df[q_pred_df["index"].isin(merged["index"])].copy()
        s_full_df = s_pred_df[s_pred_df["index"].isin(merged["index"])].copy()
        q_sub_df = q_pred_df[q_pred_df["index"].isin(selected_set)].copy()
        s_sub_df = s_pred_df[s_pred_df["index"].isin(selected_set)].copy()

        q_strict_full = _compute_strict_metrics(q_full_df, strict_score_response)
        s_strict_full = _compute_strict_metrics(s_full_df, strict_score_response)
        q_strict_sub = _compute_strict_metrics(q_sub_df, strict_score_response)
        s_strict_sub = _compute_strict_metrics(s_sub_df, strict_score_response)

        gap_full_pp = 100.0 * (meta["sphinx_full_acc"] - meta["qwen_full_acc"])
        gap_subset_pp = 100.0 * (meta["sphinx_subset_acc"] - meta["qwen_subset_acc"])
        gap_diff_pp = abs(gap_subset_pp - gap_full_pp)

        for model_name, strict_full, strict_sub, full_acc, sub_acc, diff in [
            (
                MODEL_QWEN,
                q_strict_full,
                q_strict_sub,
                100.0 * meta["qwen_full_acc"],
                100.0 * meta["qwen_subset_acc"],
                100.0 * meta["qwen_diff"],
            ),
            (
                MODEL_SPHINX,
                s_strict_full,
                s_strict_sub,
                100.0 * meta["sphinx_full_acc"],
                100.0 * meta["sphinx_subset_acc"],
                100.0 * meta["sphinx_diff"],
            ),
        ]:
            report_rows.append(
                {
                    "dataset": name,
                    "model": model_name,
                    "full_n": int(len(merged)),
                    "subset_n": int(meta["sample_count"]),
                    "seed": meta["seed"],
                    "within_0.2pp": bool(meta["within_tolerance"]),
                    "vlmeval_full_acc_pct": full_acc,
                    "vlmeval_subset_acc_pct": sub_acc,
                    "vlmeval_diff_pp": diff,
                    "vlmeval_gap_full_pp": gap_full_pp,
                    "vlmeval_gap_subset_pp": gap_subset_pp,
                    "vlmeval_gap_diff_pp": gap_diff_pp,
                    "tess_full_total": int(strict_full["total"]),
                    "tess_full_extracted": int(strict_full["extracted"]),
                    "tess_full_extraction_rate_pct": strict_full["extraction_rate_pct"],
                    "tess_full_hit": strict_full["hit"],
                    "tess_full_acc_on_extracted_pct": strict_full["acc_on_extracted_pct"],
                    "tess_subset_total": int(strict_sub["total"]),
                    "tess_subset_extracted": int(strict_sub["extracted"]),
                    "tess_subset_extraction_rate_pct": strict_sub["extraction_rate_pct"],
                    "tess_subset_hit": strict_sub["hit"],
                    "tess_subset_acc_on_extracted_pct": strict_sub["acc_on_extracted_pct"],
                }
            )

        print(
            f"[{name}] wrote {len(rows)} rows -> {cfg['out_parquet'].name} | "
            f"qwen {100*meta['qwen_subset_acc']:.4f}% vs {100*meta['qwen_full_acc']:.4f}% | "
            f"sphinx {100*meta['sphinx_subset_acc']:.4f}% vs {100*meta['sphinx_full_acc']:.4f}%"
        )

    report_df = pd.DataFrame(report_rows)
    report_df = report_df.sort_values(["dataset", "model"], ignore_index=True)
    report_path = mydata_dir / "six_datasets_subset_performance_report.tsv"
    report_df.to_csv(report_path, sep="\t", index=False)
    print(f"[done] report: {report_path}")

    examples_path = mydata_dir / "six_datasets_prompt_answer_examples.txt"
    _build_examples_text(dataset_to_parquet, examples_path)
    print(f"[done] examples: {examples_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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


DEFAULT_SRC = Path.home() / "LMUData" / "MathVista_MINI.tsv"
DEFAULT_OUT_FILENAME = "mathvista_testmini_500.parquet"
DEFAULT_META_FILENAME = "mathvista_testmini_500_subset_meta.json"
DEFAULT_REPORT_FILENAME = "mathvista_subset_performance_report.tsv"
DEFAULT_EXAMPLES_FILENAME = "six_datasets_prompt_answer_examples.txt"
DEFAULT_SAMPLE_COUNT = 500
DEFAULT_MAX_DIFF = 0.002  # 0.2 percentage points
DEFAULT_SEED_MAX = 50000

MODEL_QWEN = "Qwen2.5-VL-3B-Instruct"
MODEL_SPHINX = "Sphinx_Qwen25VL3B"

DEFAULT_QWEN_PRED = (
    Path.home() / "work" / "vlmeval" / "outputs" / MODEL_QWEN / f"{MODEL_QWEN}_MathVista_MINI.xlsx"
)
DEFAULT_SPHINX_PRED = (
    Path.home() / "work" / "vlmeval" / "outputs" / MODEL_SPHINX / f"{MODEL_SPHINX}_MathVista_MINI.xlsx"
)
DEFAULT_QWEN_GPT_EVAL = (
    Path.home()
    / "work"
    / "vlmeval"
    / "outputs"
    / MODEL_QWEN
    / f"{MODEL_QWEN}_MathVista_MINI_gpt-4o-mini.xlsx"
)
DEFAULT_SPHINX_GPT_EVAL = (
    Path.home()
    / "work"
    / "vlmeval"
    / "outputs"
    / MODEL_SPHINX
    / f"{MODEL_SPHINX}_MathVista_MINI_gpt-4o-mini.xlsx"
)


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    return str(value).strip()


def _resolved_mathvista_answer(row: pd.Series | dict[str, Any]) -> str:
    qtype = _as_text(row.get("question_type", "")).lower()
    answer_option = _as_text(row.get("answer_option", "")).upper()
    # For MathVista MCQ, the prompt asks for option letters; use option-letter GT.
    if qtype == "multi_choice" and answer_option in {"A", "B", "C", "D", "E", "F", "G"}:
        return answer_option
    answer = _as_text(row.get("answer", ""))
    return answer


def _strip_image_tokens(text: str) -> str:
    s = _as_text(text)
    if not s:
        return s
    s = s.replace("<image>", "")
    s = re.sub(r"<image\\d+>", "", s)
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
    text = re.sub(r"\\s+", "", text)
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


def _load_image(value: Any) -> Image.Image:
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


def _build_mathv_hits(df: pd.DataFrame, vlmeval_root: Path) -> pd.Series:
    if str(vlmeval_root) not in sys.path:
        sys.path.append(str(vlmeval_root))
    from vlmeval.dataset.utils.mathv import post_check

    hits: list[int] = []
    for _, row in df.iterrows():
        line = row.to_dict()
        # mathv.post_check expects `choices` to be a string representation; for open-ended
        # rows, xlsx parsing often yields NaN(float), which breaks eval().
        choices = line.get("choices", "[]")
        if not isinstance(choices, str):
            line["choices"] = "[]"
        hit = 1 if post_check(line, prefetch=False) else 0
        hits.append(hit)
    return pd.Series(hits)


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


def _append_examples(parquet_path: Path, examples_path: Path) -> None:
    df = pd.read_parquet(parquet_path)
    n = len(df)
    rows = list(range(min(5, n)))
    sep = "#" * 80

    lines: list[str] = []
    lines.append("")
    lines.append(sep)
    lines.append("DATASET: MathVista_MINI")
    lines.append(f"PARQUET: {parquet_path.name}")
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

    with examples_path.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Convert MathVista_MINI to RLVR parquet with 500-subset selection that preserves full-set "
            "GPT-evaluated accuracies for Qwen/Sphinx within tolerance."
        )
    )
    parser.add_argument("--src", type=str, default=str(DEFAULT_SRC), help="Input MathVista_MINI TSV path")
    parser.add_argument("--out", type=str, default="", help="Output directory (default: rlvr/mydata)")
    parser.add_argument("--filename", type=str, default=DEFAULT_OUT_FILENAME, help="Output parquet filename")
    parser.add_argument("--meta-filename", type=str, default=DEFAULT_META_FILENAME, help="Metadata JSON filename")
    parser.add_argument("--report-filename", type=str, default=DEFAULT_REPORT_FILENAME, help="Report TSV filename")
    parser.add_argument(
        "--examples-filename",
        type=str,
        default=DEFAULT_EXAMPLES_FILENAME,
        help="Prompt/answer examples text file to append MathVista examples",
    )
    parser.add_argument("--sample-count", type=int, default=DEFAULT_SAMPLE_COUNT, help="Subset size")
    parser.add_argument("--max-diff", type=float, default=DEFAULT_MAX_DIFF, help="Tolerance in [0,1] units")
    parser.add_argument("--seed-max", type=int, default=DEFAULT_SEED_MAX, help="Max random seeds to search")
    parser.add_argument("--qwen-pred-file", type=str, default=str(DEFAULT_QWEN_PRED), help="Qwen predictions xlsx")
    parser.add_argument(
        "--sphinx-pred-file",
        type=str,
        default=str(DEFAULT_SPHINX_PRED),
        help="Sphinx predictions xlsx",
    )
    parser.add_argument(
        "--qwen-eval-file",
        type=str,
        default=str(DEFAULT_QWEN_GPT_EVAL),
        help="Qwen GPT-judged eval xlsx",
    )
    parser.add_argument(
        "--sphinx-eval-file",
        type=str,
        default=str(DEFAULT_SPHINX_GPT_EVAL),
        help="Sphinx GPT-judged eval xlsx",
    )
    args = parser.parse_args()

    src = Path(args.src).expanduser().resolve()
    qwen_pred = Path(args.qwen_pred_file).expanduser().resolve()
    sphinx_pred = Path(args.sphinx_pred_file).expanduser().resolve()
    qwen_eval = Path(args.qwen_eval_file).expanduser().resolve()
    sphinx_eval = Path(args.sphinx_eval_file).expanduser().resolve()
    for p, name in (
        (src, "source TSV"),
        (qwen_pred, "qwen predictions"),
        (sphinx_pred, "sphinx predictions"),
        (qwen_eval, "qwen eval"),
        (sphinx_eval, "sphinx eval"),
    ):
        if not p.exists():
            raise FileNotFoundError(f"{name} not found: {p}")

    root = Path(__file__).resolve().parents[1]
    out_dir = Path(args.out).expanduser().resolve() if args.out else (root / "mydata")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / args.filename
    meta_path = out_dir / args.meta_filename
    report_path = out_dir / args.report_filename
    examples_path = out_dir / args.examples_filename

    vlmeval_root = Path.home() / "work" / "vlmeval"

    src_df = pd.read_csv(src, sep="\t")
    src_df["index"] = src_df["index"].astype(str)
    q_pred_df = pd.read_excel(qwen_pred)
    s_pred_df = pd.read_excel(sphinx_pred)
    q_pred_df["index"] = q_pred_df["index"].astype(str)
    s_pred_df["index"] = s_pred_df["index"].astype(str)
    q_eval_df = pd.read_excel(qwen_eval)
    s_eval_df = pd.read_excel(sphinx_eval)
    q_eval_df["index"] = q_eval_df["index"].astype(str)
    s_eval_df["index"] = s_eval_df["index"].astype(str)

    q_hit = _build_mathv_hits(q_eval_df, vlmeval_root)
    s_hit = _build_mathv_hits(s_eval_df, vlmeval_root)
    q_hits_df = pd.DataFrame({"index": q_eval_df["index"], "q_hit": q_hit.astype(float)})
    s_hits_df = pd.DataFrame({"index": s_eval_df["index"], "s_hit": s_hit.astype(float)})
    merged = q_hits_df.merge(s_hits_df, on="index", how="inner")
    if len(merged) < args.sample_count:
        raise ValueError(f"not enough merged rows: {len(merged)} < sample_count={args.sample_count}")

    selected, meta = _select_subset(
        merged=merged,
        sample_n=args.sample_count,
        max_diff=args.max_diff,
        seed_max=args.seed_max,
    )
    selected_indices = selected["index"].tolist()
    selected_set = set(selected_indices)

    lookup = src_df.set_index("index")
    missing_idx = [idx for idx in selected_indices if idx not in lookup.index]
    if missing_idx:
        raise RuntimeError(f"{len(missing_idx)} selected indices missing in source TSV, e.g. {missing_idx[:5]}")
    subset_src = lookup.loc[selected_indices].reset_index()

    rows: list[dict[str, Any]] = []
    for i, row in subset_src.iterrows():
        answer = _resolved_mathvista_answer(row)
        if not answer:
            raise ValueError(f"empty answer at subset row {i}")
        image = _load_image(row.get("image"))
        problem = f"<image>{_strip_image_tokens(row.get('question'))}"
        rows.append({"images": [image], "problem": problem, "answer": answer})

    ds = Dataset.from_list(rows)
    ds = ds.cast_column("images", Sequence(HFImage()))
    ds.to_parquet(str(out_path))

    if str(root) not in sys.path:
        sys.path.append(str(root))
    from verl.utils.local_strict_eval import strict_score_response

    answer_lookup = src_df.set_index("index").apply(_resolved_mathvista_answer, axis=1).to_dict()
    q_full_df = q_pred_df[q_pred_df["index"].isin(merged["index"])].copy()
    s_full_df = s_pred_df[s_pred_df["index"].isin(merged["index"])].copy()
    q_sub_df = q_pred_df[q_pred_df["index"].isin(selected_set)].copy()
    s_sub_df = s_pred_df[s_pred_df["index"].isin(selected_set)].copy()
    q_full_df["answer"] = q_full_df["index"].map(answer_lookup)
    s_full_df["answer"] = s_full_df["index"].map(answer_lookup)
    q_sub_df["answer"] = q_sub_df["index"].map(answer_lookup)
    s_sub_df["answer"] = s_sub_df["index"].map(answer_lookup)

    q_strict_full = _compute_strict_metrics(q_full_df, strict_score_response)
    s_strict_full = _compute_strict_metrics(s_full_df, strict_score_response)
    q_strict_sub = _compute_strict_metrics(q_sub_df, strict_score_response)
    s_strict_sub = _compute_strict_metrics(s_sub_df, strict_score_response)

    meta.update(
        {
            "dataset": "MathVista_MINI",
            "mode": "gpt_match_full",
            "source_tsv": str(src),
            "qwen_pred_file": str(qwen_pred),
            "sphinx_pred_file": str(sphinx_pred),
            "qwen_eval_file": str(qwen_eval),
            "sphinx_eval_file": str(sphinx_eval),
            "parquet_file": str(out_path),
            "qwen_strict_full": q_strict_full,
            "qwen_strict_subset": q_strict_sub,
            "sphinx_strict_full": s_strict_full,
            "sphinx_strict_subset": s_strict_sub,
        }
    )
    meta_path.write_text(json.dumps(meta, ensure_ascii=True, indent=2), encoding="utf-8")

    report_rows = []
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
                "dataset": "MathVista_MINI",
                "model": model_name,
                "full_n": int(len(merged)),
                "subset_n": int(meta["sample_count"]),
                "seed": meta["seed"],
                "within_0.2pp": bool(meta["within_tolerance"]),
                "vlmeval_full_acc_pct": full_acc,
                "vlmeval_subset_acc_pct": sub_acc,
                "vlmeval_diff_pp": diff,
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
    pd.DataFrame(report_rows).to_csv(report_path, sep="\t", index=False)

    _append_examples(out_path, examples_path)

    print(f"[done] wrote {len(ds)} rows -> {out_path}")
    print(f"[done] wrote metadata -> {meta_path}")
    print(f"[done] wrote report -> {report_path}")
    print(f"[done] appended examples -> {examples_path}")
    print(
        "selected seed={seed} | qwen_subset={q:.4f}% ({qh}/{n}) vs full={qf:.4f}% | "
        "sphinx_subset={s:.4f}% ({sh}/{n}) vs full={sf:.4f}% | "
        "diffs=({qd:.4f}pp, {sd:.4f}pp) | gap_diff={gd:.4f}pp".format(
            seed=meta["seed"],
            q=100.0 * meta["qwen_subset_acc"],
            qh=meta["qwen_hit"],
            qf=100.0 * meta["qwen_full_acc"],
            s=100.0 * meta["sphinx_subset_acc"],
            sh=meta["sphinx_hit"],
            sf=100.0 * meta["sphinx_full_acc"],
            n=meta["sample_count"],
            qd=100.0 * meta["qwen_diff"],
            sd=100.0 * meta["sphinx_diff"],
            gd=100.0 * meta["gap_diff"],
        )
    )
    print(
        "rlvr subset strict | "
        f"{MODEL_QWEN}: extracted={int(q_strict_sub['extracted'])}/{int(q_strict_sub['total'])} "
        f"({q_strict_sub['extraction_rate_pct']:.2f}%), "
        f"acc_on_extracted={q_strict_sub['acc_on_extracted_pct']:.2f}% | "
        f"{MODEL_SPHINX}: extracted={int(s_strict_sub['extracted'])}/{int(s_strict_sub['total'])} "
        f"({s_strict_sub['extraction_rate_pct']:.2f}%), "
        f"acc_on_extracted={s_strict_sub['acc_on_extracted_pct']:.2f}%"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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


DEFAULT_SRC = Path.home() / "LMUData" / "MathVision.tsv"
DEFAULT_OUT_FILENAME = "mathvision_test_500.parquet"
DEFAULT_SAMPLE_COUNT = 500
DEFAULT_VLMEVAL_ROOT = Path.home() / "work" / "vlmeval"

DEFAULT_QWEN_GPT_EVAL = (
    Path.home()
    / "work"
    / "vlmeval"
    / "outputs"
    / "Qwen2.5-VL-3B-Instruct"
    / "T20260227_G5a302e46"
    / "Qwen2.5-VL-3B-Instruct_MathVision_gpt-4o-mini.xlsx"
)
DEFAULT_SPHINX_GPT_EVAL = (
    Path.home()
    / "work"
    / "vlmeval"
    / "outputs"
    / "Sphinx_Qwen25VL3B"
    / "T20260228_G5a302e46"
    / "Sphinx_Qwen25VL3B_MathVision_gpt-4o-mini.xlsx"
)


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    return str(value).strip()


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


def _format_problem(question: str) -> str:
    return f"<image>{question.strip()}"


def _build_hit_table(
    eval_file: Path,
    vlmeval_root: Path,
    model_tag: str,
) -> pd.DataFrame:
    if str(vlmeval_root) not in sys.path:
        sys.path.append(str(vlmeval_root))
    from vlmeval.dataset.utils.mathv import post_check

    df = pd.read_excel(eval_file)
    required = {"index", "answer", "res", "choices"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"{model_tag} eval file missing columns: {sorted(missing)}")

    hits: list[int] = []
    for _, row in df.iterrows():
        line = row.to_dict()
        hits.append(1 if post_check(line, prefetch=False) else 0)

    out = pd.DataFrame({"index": df["index"].astype(str), f"{model_tag}_hit": hits})
    return out


def _select_subset_by_gpt_match(
    src_df: pd.DataFrame,
    qwen_eval_file: Path,
    sphinx_eval_file: Path,
    vlmeval_root: Path,
    sample_count: int,
    max_diff: float,
    seed_max: int,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    q_hits = _build_hit_table(qwen_eval_file, vlmeval_root, "qwen")
    s_hits = _build_hit_table(sphinx_eval_file, vlmeval_root, "sphinx")

    merged = q_hits.merge(s_hits, on="index", how="inner")
    if len(merged) < sample_count:
        raise ValueError(f"not enough merged rows: {len(merged)} < {sample_count}")

    q_full = float(merged["qwen_hit"].mean())
    s_full = float(merged["sphinx_hit"].mean())
    gap_full = s_full - q_full

    best_ok: tuple[float, float, float, int, float, float, int, int] | None = None
    best_any: tuple[float, float, float, int, float, float, int, int] | None = None
    for seed in range(seed_max):
        sample = merged.sample(n=sample_count, random_state=seed)
        q_hit_count = int(sample["qwen_hit"].sum())
        s_hit_count = int(sample["sphinx_hit"].sum())
        q_acc = q_hit_count / sample_count
        s_acc = s_hit_count / sample_count
        q_diff = abs(q_acc - q_full)
        s_diff = abs(s_acc - s_full)
        gap_diff = abs((s_acc - q_acc) - gap_full)
        row = (gap_diff, max(q_diff, s_diff), q_diff + s_diff, seed, q_acc, s_acc, q_hit_count, s_hit_count)
        if best_any is None or row < best_any:
            best_any = row
        if q_diff <= max_diff and s_diff <= max_diff:
            if best_ok is None or row < best_ok:
                best_ok = row

    if best_any is None:
        raise RuntimeError("subset search failed: no candidate found")

    chosen = best_ok if best_ok is not None else best_any
    (
        chosen_gap_diff,
        chosen_max_diff,
        chosen_sum_diff,
        chosen_seed,
        chosen_q_acc,
        chosen_s_acc,
        chosen_q_hits,
        chosen_s_hits,
    ) = chosen

    chosen_subset = merged.sample(n=sample_count, random_state=chosen_seed).reset_index(drop=True)
    chosen_indices = chosen_subset["index"].astype(str).tolist()

    src = src_df.copy()
    src["index"] = src["index"].astype(str)
    lookup = src.set_index("index")
    missing_idx = [idx for idx in chosen_indices if idx not in lookup.index]
    if missing_idx:
        raise RuntimeError(f"{len(missing_idx)} selected indices missing in source TSV, e.g. {missing_idx[:5]}")
    subset = lookup.loc[chosen_indices].reset_index()

    meta = {
        "sample_count": sample_count,
        "seed": chosen_seed,
        "mode": "gpt_match_full_mathvision",
        "within_tolerance": bool(best_ok is not None),
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
        "qwen_hit": chosen_q_hits,
        "sphinx_hit": chosen_s_hits,
        "qwen_eval_file": str(qwen_eval_file),
        "sphinx_eval_file": str(sphinx_eval_file),
        "vlmeval_root": str(vlmeval_root),
        "seed_max": seed_max,
    }
    return subset, meta


def _build_rows(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i, row in df.iterrows():
        question = _as_text(row.get("question"))
        answer = _as_text(row.get("answer"))
        if not question:
            raise ValueError(f"empty question at row {i}")
        if not answer:
            raise ValueError(f"empty answer at row {i}")
        image = _load_image(row.get("image"))
        rows.append(
            {
                "images": [image],
                "problem": _format_problem(question),
                "answer": answer,
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert MathVision to RLVR parquet and select subset by matching GPT full-set accuracies."
    )
    parser.add_argument("--src", type=str, default=str(DEFAULT_SRC), help="Input MathVision TSV path")
    parser.add_argument("--out", type=str, default="", help="Output directory (default: rlvr/mydata)")
    parser.add_argument("--filename", type=str, default=DEFAULT_OUT_FILENAME, help="Output parquet filename")
    parser.add_argument("--sample-count", type=int, default=DEFAULT_SAMPLE_COUNT, help="Subset size")
    parser.add_argument(
        "--qwen-eval-file",
        type=str,
        default=str(DEFAULT_QWEN_GPT_EVAL),
        help="Qwen GPT-evaluated MathVision xlsx",
    )
    parser.add_argument(
        "--sphinx-eval-file",
        type=str,
        default=str(DEFAULT_SPHINX_GPT_EVAL),
        help="Sphinx GPT-evaluated MathVision xlsx",
    )
    parser.add_argument(
        "--vlmeval-root",
        type=str,
        default=str(DEFAULT_VLMEVAL_ROOT),
        help="Path to vlmeval repo for importing MathVision post_check logic",
    )
    parser.add_argument(
        "--max-diff",
        type=float,
        default=0.002,
        help="Max absolute accuracy difference from full-set, in [0,1] units (0.002 = 0.2pp)",
    )
    parser.add_argument("--seed-max", type=int, default=50000, help="Max seed search range [0, seed-max)")
    parser.add_argument(
        "--meta-filename",
        type=str,
        default="mathvision_test_500_subset_meta.json",
        help="Metadata JSON filename in output directory",
    )
    args = parser.parse_args()

    src = Path(args.src).expanduser().resolve()
    qwen_eval = Path(args.qwen_eval_file).expanduser().resolve()
    sphinx_eval = Path(args.sphinx_eval_file).expanduser().resolve()
    vlmeval_root = Path(args.vlmeval_root).expanduser().resolve()
    if not src.exists():
        raise FileNotFoundError(f"source TSV not found: {src}")
    if not qwen_eval.exists():
        raise FileNotFoundError(f"qwen eval file not found: {qwen_eval}")
    if not sphinx_eval.exists():
        raise FileNotFoundError(f"sphinx eval file not found: {sphinx_eval}")
    if not vlmeval_root.exists():
        raise FileNotFoundError(f"vlmeval root not found: {vlmeval_root}")

    root = Path(__file__).resolve().parents[1]
    out_dir = Path(args.out).expanduser().resolve() if args.out else (root / "mydata")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / args.filename
    meta_path = out_dir / args.meta_filename

    src_df = pd.read_csv(src, sep="\t")
    subset_df, meta = _select_subset_by_gpt_match(
        src_df=src_df,
        qwen_eval_file=qwen_eval,
        sphinx_eval_file=sphinx_eval,
        vlmeval_root=vlmeval_root,
        sample_count=args.sample_count,
        max_diff=args.max_diff,
        seed_max=args.seed_max,
    )

    rows = _build_rows(subset_df)
    ds = Dataset.from_list(rows)
    ds = ds.cast_column("images", Sequence(HFImage()))
    ds.to_parquet(str(out_path))

    meta["parquet_file"] = str(out_path)
    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=True, indent=2)

    print(f"[done] wrote {len(ds)} rows to {out_path}")
    print(f"[done] wrote metadata to {meta_path}")
    print(
        "selected seed={seed} | qwen_subset={q:.4f}% ({qh}/{n}) vs full={qf:.4f}% | "
        "sphinx_subset={s:.4f}% ({sh}/{n}) vs full={sf:.4f}% | "
        "diffs=({qd:.4f}pp, {sd:.4f}pp) | gap_diff={gd:.4f}pp | within_tol={ok}".format(
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
            ok=meta["within_tolerance"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

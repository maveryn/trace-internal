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


DEFAULT_SRC = Path.home() / "LMUData" / "Q-Bench1_VAL.tsv"
DEFAULT_OUT_FILENAME = "qbench1_val_500.parquet"
DEFAULT_SAMPLE_COUNT = 500

DEFAULT_QWEN_PRED = (
    Path.home()
    / "work"
    / "vlmeval"
    / "outputs"
    / "Qwen2.5-VL-3B-Instruct"
    / "Qwen2.5-VL-3B-Instruct_Q-Bench1_VAL.xlsx"
)
DEFAULT_SPHINX_PRED = (
    Path.home()
    / "work"
    / "vlmeval"
    / "outputs"
    / "Sphinx_Qwen25VL3B"
    / "Sphinx_Qwen25VL3B_Q-Bench1_VAL.xlsx"
)
DEFAULT_QWEN_GPT_EVAL = (
    Path.home()
    / "work"
    / "vlmeval"
    / "outputs"
    / "Qwen2.5-VL-3B-Instruct"
    / "Qwen2.5-VL-3B-Instruct_Q-Bench1_VAL_openai_result.xlsx"
)
DEFAULT_SPHINX_GPT_EVAL = (
    Path.home()
    / "work"
    / "vlmeval"
    / "outputs"
    / "Sphinx_Qwen25VL3B"
    / "Sphinx_Qwen25VL3B_Q-Bench1_VAL_openai_result.xlsx"
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

    # Optional local-path fallback.
    if len(text) <= 512 and ("/" in text or "\\" in text):
        try:
            maybe_path = Path(text).expanduser()
            if maybe_path.exists() and maybe_path.is_file():
                return _open_image_file(maybe_path)
        except OSError:
            pass

    return _decode_image_b64(text)


def _format_problem(question: str, options: dict[str, str], hint: str | None = None) -> str:
    # Match vlmeval ImageMCQDataset.build_prompt style.
    prompt = ""
    if hint:
        prompt += f"Hint: {hint}\n"
    prompt += f"Question: {question}\n"
    if options:
        prompt += "Options:\n"
        for key in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            if key in options and options[key]:
                prompt += f"{key}. {options[key]}\n"
        prompt += "Please select the correct answer from the options above. \n"
    return f"<image>{prompt}"


def _select_subset_by_strict_gap(
    qbench_df: pd.DataFrame,
    qwen_pred_file: Path,
    sphinx_pred_file: Path,
    sample_count: int,
    gap_low: float,
    gap_high: float,
    target_gap: float,
    seed_max: int,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.append(str(root))
    from verl.utils.local_strict_eval import strict_score_response

    qdf = pd.read_excel(qwen_pred_file)
    sdf = pd.read_excel(sphinx_pred_file)
    qdf["index"] = qdf["index"].astype(str)
    sdf["index"] = sdf["index"].astype(str)

    q_small = qdf[["index", "answer", "prediction"]].rename(columns={"prediction": "q_pred"})
    s_small = sdf[["index", "answer", "prediction"]].rename(columns={"prediction": "s_pred"})
    merged = q_small.merge(s_small, on=["index", "answer"], how="inner")
    if len(merged) < sample_count:
        raise ValueError(f"not enough merged rows: {len(merged)} < {sample_count}")

    scores = []
    for _, r in merged.iterrows():
        gt = _as_text(r["answer"]).upper()
        q_pred = _as_text(r.get("q_pred"))
        s_pred = _as_text(r.get("s_pred"))
        q_score, _, _, _ = strict_score_response(q_pred, gt)
        s_score, _, _, _ = strict_score_response(s_pred, gt)
        scores.append((float(q_score), float(s_score)))
    merged = merged.copy()
    merged["q_score"] = [x[0] for x in scores]
    merged["s_score"] = [x[1] for x in scores]

    best: tuple[int, float, float, float, int, int] | None = None
    for seed in range(seed_max):
        sample = merged.sample(n=sample_count, random_state=seed)
        q_hits = float(sample["q_score"].sum())
        s_hits = float(sample["s_score"].sum())
        q_acc = 100.0 * q_hits / sample_count
        s_acc = 100.0 * s_hits / sample_count
        gap = s_acc - q_acc
        if gap_low <= gap <= gap_high and s_acc > q_acc:
            row = (seed, gap, q_acc, s_acc, int(q_hits), int(s_hits))
            if best is None:
                best = row
            else:
                if abs(row[1] - target_gap) < abs(best[1] - target_gap) or (
                    abs(row[1] - target_gap) == abs(best[1] - target_gap) and row[0] < best[0]
                ):
                    best = row

    if best is None:
        raise RuntimeError(
            f"no seed found in [0, {seed_max}) with strict gap in [{gap_low}, {gap_high}] and sphinx>qwen"
        )

    chosen_seed, chosen_gap, chosen_q_acc, chosen_s_acc, chosen_q_hits, chosen_s_hits = best
    chosen = merged.sample(n=sample_count, random_state=chosen_seed).reset_index(drop=True)
    chosen_indices = chosen["index"].astype(str).tolist()

    src = qbench_df.copy()
    src["index"] = src["index"].astype(str)
    lookup = src.set_index("index")
    missing = [idx for idx in chosen_indices if idx not in lookup.index]
    if missing:
        raise RuntimeError(f"{len(missing)} selected indices missing in source TSV, e.g. {missing[:5]}")
    subset = lookup.loc[chosen_indices].reset_index()

    meta = {
        "sample_count": sample_count,
        "seed": chosen_seed,
        "gap_pct": chosen_gap,
        "qwen_acc_pct": chosen_q_acc,
        "sphinx_acc_pct": chosen_s_acc,
        "qwen_hit": chosen_q_hits,
        "sphinx_hit": chosen_s_hits,
        "qwen_pred_file": str(qwen_pred_file),
        "sphinx_pred_file": str(sphinx_pred_file),
        "gap_low_pct": gap_low,
        "gap_high_pct": gap_high,
        "target_gap_pct": target_gap,
    }
    return subset, meta


def _select_subset_by_gpt_match(
    qbench_df: pd.DataFrame,
    qwen_eval_file: Path,
    sphinx_eval_file: Path,
    sample_count: int,
    max_diff: float,
    seed_max: int,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    qdf = pd.read_excel(qwen_eval_file)
    sdf = pd.read_excel(sphinx_eval_file)
    for df, name in ((qdf, "qwen"), (sdf, "sphinx")):
        required = {"index", "hit"}
        missing = required.difference(df.columns)
        if missing:
            raise ValueError(f"{name} eval file missing columns: {sorted(missing)}")
    qdf["index"] = qdf["index"].astype(str)
    sdf["index"] = sdf["index"].astype(str)

    q_small = qdf[["index", "hit"]].rename(columns={"hit": "q_hit"})
    s_small = sdf[["index", "hit"]].rename(columns={"hit": "s_hit"})
    merged = q_small.merge(s_small, on="index", how="inner")
    if len(merged) < sample_count:
        raise ValueError(f"not enough merged rows: {len(merged)} < {sample_count}")

    merged["q_hit"] = pd.to_numeric(merged["q_hit"], errors="coerce").fillna(0).astype(float)
    merged["s_hit"] = pd.to_numeric(merged["s_hit"], errors="coerce").fillna(0).astype(float)

    q_full = float(merged["q_hit"].mean())
    s_full = float(merged["s_hit"].mean())
    gap_full = s_full - q_full

    best_ok: tuple[float, float, float, int, float, float, int, int] | None = None
    best_any: tuple[float, float, float, int, float, float, int, int] | None = None
    for seed in range(seed_max):
        sample = merged.sample(n=sample_count, random_state=seed)
        q_hits = int(sample["q_hit"].sum())
        s_hits = int(sample["s_hit"].sum())
        q_acc = q_hits / sample_count
        s_acc = s_hits / sample_count
        q_diff = abs(q_acc - q_full)
        s_diff = abs(s_acc - s_full)
        gap_diff = abs((s_acc - q_acc) - gap_full)
        # For valid subsets, prioritize preserving the cross-model gap first,
        # then keep both model accuracies close to full-set, then lower seed.
        row = (gap_diff, max(q_diff, s_diff), q_diff + s_diff, seed, q_acc, s_acc, q_hits, s_hits)
        if best_any is None or row < best_any:
            best_any = row
        if q_diff <= max_diff and s_diff <= max_diff:
            if best_ok is None or row < best_ok:
                best_ok = row

    if best_any is None:
        raise RuntimeError("subset search failed: no candidate found")

    chosen = best_ok if best_ok is not None else best_any
    chosen_gap_diff, chosen_max_diff, chosen_sum_diff, chosen_seed, chosen_q_acc, chosen_s_acc, chosen_q_hits, chosen_s_hits = chosen
    chosen_subset = merged.sample(n=sample_count, random_state=chosen_seed).reset_index(drop=True)
    chosen_indices = chosen_subset["index"].astype(str).tolist()

    src = qbench_df.copy()
    src["index"] = src["index"].astype(str)
    lookup = src.set_index("index")
    missing = [idx for idx in chosen_indices if idx not in lookup.index]
    if missing:
        raise RuntimeError(f"{len(missing)} selected indices missing in source TSV, e.g. {missing[:5]}")
    subset = lookup.loc[chosen_indices].reset_index()

    meta = {
        "sample_count": sample_count,
        "seed": chosen_seed,
        "mode": "gpt_match_full",
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
        "seed_max": seed_max,
    }
    return subset, meta


def _build_rows(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i, row in df.iterrows():
        question = _as_text(row.get("question"))
        hint = _as_text(row.get("hint")) if "hint" in df.columns else ""
        options = {
            key: _as_text(row.get(key))
            for key in ("A", "B", "C", "D", "E")
            if _as_text(row.get(key))
        }
        answer = _as_text(row.get("answer")).upper()
        if not answer:
            raise ValueError(f"empty answer at row {i}")
        image = _load_image(row.get("image"))
        rows.append(
            {
                "images": [image],
                "problem": _format_problem(question, options, hint=hint or None),
                "answer": answer,
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert Q-Bench1_VAL to RLVR parquet with configurable subset selection."
    )
    parser.add_argument("--src", type=str, default=str(DEFAULT_SRC), help="Input Q-Bench1_VAL TSV path")
    parser.add_argument("--out", type=str, default="", help="Output directory (default: rlvr/mydata)")
    parser.add_argument("--filename", type=str, default=DEFAULT_OUT_FILENAME, help="Output parquet filename")
    parser.add_argument("--sample-count", type=int, default=DEFAULT_SAMPLE_COUNT, help="Subset size")
    parser.add_argument(
        "--selection-mode",
        type=str,
        default="gpt_match_full",
        choices=["gpt_match_full", "strict_gap"],
        help="Subset selection objective",
    )
    parser.add_argument("--qwen-pred-file", type=str, default=str(DEFAULT_QWEN_PRED), help="Qwen prediction xlsx")
    parser.add_argument(
        "--sphinx-pred-file", type=str, default=str(DEFAULT_SPHINX_PRED), help="Sphinx prediction xlsx"
    )
    parser.add_argument(
        "--qwen-eval-file",
        type=str,
        default=str(DEFAULT_QWEN_GPT_EVAL),
        help="Qwen GPT-judged eval xlsx containing index/hit",
    )
    parser.add_argument(
        "--sphinx-eval-file",
        type=str,
        default=str(DEFAULT_SPHINX_GPT_EVAL),
        help="Sphinx GPT-judged eval xlsx containing index/hit",
    )
    parser.add_argument(
        "--max-diff",
        type=float,
        default=0.05,
        help="Max absolute accuracy difference from full-set, in [0,1] units (0.05 = 5pp)",
    )
    parser.add_argument("--gap-low", type=float, default=0.35, help="Lower bound for strict gap pct")
    parser.add_argument("--gap-high", type=float, default=0.45, help="Upper bound for strict gap pct")
    parser.add_argument("--target-gap", type=float, default=0.4, help="Preferred strict gap pct")
    parser.add_argument("--seed-max", type=int, default=50000, help="Max seed search range [0, seed-max)")
    parser.add_argument(
        "--meta-filename",
        type=str,
        default="qbench1_val_500_subset_meta.json",
        help="Metadata JSON filename in output directory",
    )
    args = parser.parse_args()

    src = Path(args.src).expanduser().resolve()
    qwen_pred = Path(args.qwen_pred_file).expanduser().resolve()
    sphinx_pred = Path(args.sphinx_pred_file).expanduser().resolve()
    qwen_eval = Path(args.qwen_eval_file).expanduser().resolve()
    sphinx_eval = Path(args.sphinx_eval_file).expanduser().resolve()
    if not src.exists():
        raise FileNotFoundError(f"source TSV not found: {src}")
    if args.selection_mode == "strict_gap":
        if not qwen_pred.exists():
            raise FileNotFoundError(f"qwen prediction file not found: {qwen_pred}")
        if not sphinx_pred.exists():
            raise FileNotFoundError(f"sphinx prediction file not found: {sphinx_pred}")
    else:
        if not qwen_eval.exists():
            raise FileNotFoundError(f"qwen eval file not found: {qwen_eval}")
        if not sphinx_eval.exists():
            raise FileNotFoundError(f"sphinx eval file not found: {sphinx_eval}")

    root = Path(__file__).resolve().parents[1]
    out_dir = Path(args.out).expanduser().resolve() if args.out else (root / "mydata")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / args.filename
    meta_path = out_dir / args.meta_filename

    qbench_df = pd.read_csv(src, sep="\t")
    if args.selection_mode == "strict_gap":
        subset_df, meta = _select_subset_by_strict_gap(
            qbench_df=qbench_df,
            qwen_pred_file=qwen_pred,
            sphinx_pred_file=sphinx_pred,
            sample_count=args.sample_count,
            gap_low=args.gap_low,
            gap_high=args.gap_high,
            target_gap=args.target_gap,
            seed_max=args.seed_max,
        )
    else:
        subset_df, meta = _select_subset_by_gpt_match(
            qbench_df=qbench_df,
            qwen_eval_file=qwen_eval,
            sphinx_eval_file=sphinx_eval,
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
    if args.selection_mode == "strict_gap":
        print(
            "selected seed={seed} | qwen_acc={q:.4f}% ({qh}/{n}) | sphinx_acc={s:.4f}% ({sh}/{n}) | gap={g:.4f}%".format(
                seed=meta["seed"],
                q=meta["qwen_acc_pct"],
                qh=meta["qwen_hit"],
                s=meta["sphinx_acc_pct"],
                sh=meta["sphinx_hit"],
                n=meta["sample_count"],
                g=meta["gap_pct"],
            )
        )
    else:
        print(
            "selected seed={seed} | qwen_subset={q:.4f}% ({qh}/{n}) vs full={qf:.4f}% | "
            "sphinx_subset={s:.4f}% ({sh}/{n}) vs full={sf:.4f}% | "
            "diffs=({qd:.4f}pp, {sd:.4f}pp) | within_tol={ok}".format(
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
                ok=meta["within_tolerance"],
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

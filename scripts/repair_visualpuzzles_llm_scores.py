#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_ROOT = REPO_ROOT / "results"
SHM_ROOT = Path("/dev/shm/trace_rlvr")

VISUALPUZZLES = "VisualPuzzles"
ANSWER_3B7B_SLUGS = {
    "3B Base": "qwen25vl3b-base",
    "3B Answer GRPO 500": "trace-qwen25vl3b-easyr1-all1000-answer-nokl-step500",
    "7B Base": "qwen25vl7b-base",
    "7B Answer GRPO 500": "trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500",
}

SELECTED25_SCORE_ROOTS = {
    42: SHM_ROOT
    / "trace_extra7_full_temp06_4096_20260713T103556Z_score"
    / "llm_extracted"
    / "trace_extra7_full_temp06_4096_20260713T103556Z_score_llm_extract"
    / "scores"
    / "visualpuzzles",
    43: SHM_ROOT
    / "trace_selected25_full_temp06_4096_seed43_44_answer_3b7b_20260714T065129Z_score"
    / "seed_43"
    / "llm_extracted"
    / "trace_selected25_full_temp06_4096_seed43_44_answer_3b7b_20260714T065129Z_seed43_score_llm_extract"
    / "scores"
    / "visualpuzzles",
    44: SHM_ROOT
    / "trace_selected25_full_temp06_4096_seed43_44_answer_3b7b_20260714T065129Z_score"
    / "seed_44"
    / "llm_extracted"
    / "trace_selected25_full_temp06_4096_seed43_44_answer_3b7b_20260714T065129Z_seed44_score_llm_extract"
    / "scores"
    / "visualpuzzles",
}

FINAL20_EXTERNAL = {
    "OpenMOSS Game-RL Qwen2.5-VL-7B (seed42)": (
        "game-rl-qwen25vl7b",
        SHM_ROOT
        / "trace_final20_temp06_seed42_game-rl-qwen25vl7b_20260714T162908Z_score"
        / "llm_extracted"
        / "trace_final20_temp06_seed42_game-rl-qwen25vl7b_20260714T162908Z_llm_extract"
        / "scores"
        / "visualpuzzles",
        RESULTS_ROOT / "trace_final20_temp06_seed42_game-rl-qwen25vl7b_20260714T162908Z_results.xlsx",
    ),
    "Sphinx Qwen2.5-VL-7B 500 (seed42)": (
        "sphinx-qwen7b-500",
        SHM_ROOT
        / "trace_final20_temp06_seed42_sphinx-qwen7b-500_20260714T172623Z_score"
        / "llm_extracted"
        / "trace_final20_temp06_seed42_sphinx-qwen7b-500_20260714T172623Z_llm_extract"
        / "scores"
        / "visualpuzzles",
        RESULTS_ROOT / "trace_final20_temp06_seed42_sphinx-qwen7b-500_20260714T172623Z_results.xlsx",
    ),
    "PCGRPO Qwen2.5-VL-7B Jigsaw CARE (seed42)": (
        "pcgrpo-qwen25vl7b-jigsaw-care",
        SHM_ROOT
        / "trace_final20_temp06_seed42_pcgrpo-qwen25vl7b-jigsaw-care_20260714T182351Z_score"
        / "llm_extracted"
        / "trace_final20_temp06_seed42_pcgrpo-qwen25vl7b-jigsaw-care_20260714T182351Z_llm_extract"
        / "scores"
        / "visualpuzzles",
        RESULTS_ROOT / "trace_final20_temp06_seed42_pcgrpo-qwen25vl7b-jigsaw-care_20260714T182351Z_results.xlsx",
    ),
    "Vero Qwen2.5-VL-7B (seed42)": (
        "vero-qwen25-7b",
        SHM_ROOT
        / "trace_final20_temp06_seed42_vero-qwen25-7b_20260714T192431Z_score"
        / "llm_extracted"
        / "trace_final20_temp06_seed42_vero-qwen25-7b_20260714T192431Z_llm_extract"
        / "scores"
        / "visualpuzzles",
        RESULTS_ROOT / "trace_final20_temp06_seed42_vero-qwen25-7b_20260714T192431Z_results.xlsx",
    ),
}

ANNOTATION_3B = {
    "column": "Qwen2.5-VL-3B Annotation GRPO 500 (seed42)",
    "slug": "trace-qwen25vl3b-rlvr-ann-additive-0p50-sectioned-step500",
    "root": SHM_ROOT
    / "trace_ann29_temp06_4096_20260713T193234Z_score"
    / "llm_extracted"
    / "trace_ann29_temp06_4096_20260713T193234Z_score_llm_extract"
    / "scores"
    / "visualpuzzles",
    "xlsx": RESULTS_ROOT / "trace_ann29_temp06_4096_results.xlsx",
}


def normalize_option(value: Any, letters: str = "ABCD") -> str:
    text = "" if value is None or (isinstance(value, float) and math.isnan(value)) else str(value)
    text = text.strip().upper().strip("()[]{}.:;\"'`* ")
    if text in letters or text == "Z":
        return text
    match = re.search(rf"\b([{re.escape(letters)}Z])\b", text)
    return match.group(1) if match else ""


def parse_json_answer(value: Any) -> str:
    raw = "" if value is None or (isinstance(value, float) and math.isnan(value)) else str(value).strip()
    if not raw:
        return ""
    for candidate in (raw,):
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict):
                return str(obj.get("answer", obj.get("extracted_answer", ""))).strip()
        except Exception:
            pass
    match = re.search(r"\{.*?\}", raw, flags=re.S)
    if match:
        try:
            obj = json.loads(match.group(0))
            if isinstance(obj, dict):
                return str(obj.get("answer", obj.get("extracted_answer", ""))).strip()
        except Exception:
            pass
    match = re.search(r'"?(?:answer|extracted_answer)"?\s*[:=]\s*"?([^"\n}]+)', raw, flags=re.I)
    if match:
        return match.group(1).strip()
    return raw.splitlines()[0].strip()


def judged_path(root: Path, slug: str) -> Path:
    return root / slug / "llm_extracted" / "llm_extracted_judged.xlsx"


def repair_judged_table(path: Path, *, dry_run: bool) -> tuple[float, int]:
    if not path.exists():
        raise FileNotFoundError(path)
    data = pd.read_excel(path)
    raw_answers = []
    for extracted_raw, judge_output in zip(data["extracted_raw"], data["judge_output"]):
        raw = extracted_raw
        if pd.isna(raw) or not str(raw).strip():
            raw = parse_json_answer(judge_output)
        raw_answers.append(raw)
    data["valid_letters"] = ["['A', 'B', 'C', 'D']"] * len(data)
    data["extracted_raw"] = raw_answers
    data["extracted"] = [normalize_option(value) for value in raw_answers]
    data["eval_gt"] = [normalize_option(value) for value in data["answer"]]
    old_pred = data["eval_pred"].fillna("").map(str)
    data["eval_pred"] = [normalize_option(value) for value in data["extracted"]]
    data["eval_score"] = [
        int(bool(pred) and pred == gt) for pred, gt in zip(data["eval_pred"], data["eval_gt"])
    ]
    fixed_invalid = sum(
        1
        for before, after in zip(old_pred, data["eval_pred"])
        if before.strip().upper() in {"", "NAN"} and after in "ABCD"
    )
    score = float(data["eval_score"].mean() * 100.0)
    if not dry_run:
        data.to_excel(path, index=False)
        scores_json = path.with_name("scores.json")
        if scores_json.exists():
            obj = json.loads(scores_json.read_text(encoding="utf-8"))
            obj["score"] = score
            scores = obj.setdefault("scores", {})
            scores["Overall"] = score
            obj["visualpuzzles_repair"] = {
                "valid_letters": "ABCD",
                "fixed_invalid_predictions": fixed_invalid,
                "note": "Re-scored cached Qwen3 extraction outputs; no generation or judge rerun.",
            }
            scores_json.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    return score, fixed_invalid


def write_excel(path: Path, sheets: dict[str, pd.DataFrame]) -> None:
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for sheet_name, data in sheets.items():
            data.to_excel(writer, sheet_name=sheet_name, index=False)


def dataframe_to_markdown(data: pd.DataFrame) -> str:
    return data.to_markdown(index=False, floatfmt=".2f")


def write_summary_md(path: Path, title: str, summary: pd.DataFrame, metadata: pd.DataFrame | None = None) -> None:
    lines = [
        f"# {title}",
        "",
        "VisualPuzzles repair note: cached Qwen3 extraction outputs are re-scored with the benchmark-wide A-D option contract; no generation or judge rerun was used.",
        "",
        dataframe_to_markdown(summary),
        "",
    ]
    if metadata is not None:
        lines.extend(["## Metadata", metadata.to_markdown(index=False), ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def write_final20_md(path: Path, sheets: dict[str, pd.DataFrame]) -> None:
    lines = [
        "# TRACE Final20 Temp0.6 3B/7B All Methods Results",
        "",
        "Deterministic repair notes:",
        "- ScreenSpot/TableVQABench cached predictions are re-parsed for final-answer wrappers and positional `pyautogui.click(x, y)` calls.",
        "- VisualPuzzles cached Qwen3 extraction outputs are re-scored with the benchmark-wide A-D option contract.",
        "- No generation or judge rerun was used for these repairs.",
        "",
        "## 3B",
        dataframe_to_markdown(sheets["3B"]),
        "",
        "## 7B",
        dataframe_to_markdown(sheets["7B"]),
        "",
    ]
    if "metadata" in sheets:
        lines.extend(["## Metadata", sheets["metadata"].to_markdown(index=False), ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def update_average_row(data: pd.DataFrame, columns: list[str]) -> None:
    mask = data["Benchmark"].astype(str).eq("Average")
    if not mask.any():
        return
    body = data[~mask]
    for column in columns:
        data.loc[mask, column] = body[column].astype(float).mean()
    data.loc[mask, "Rows"] = math.nan


def update_single_model_workbook(path: Path, slug: str, score: float) -> None:
    sheets = pd.read_excel(path, sheet_name=None)
    mask = sheets["summary"]["benchmark"].astype(str).eq(VISUALPUZZLES)
    value_col = next(col for col in sheets["summary"].columns if col == slug or col.endswith(slug))
    sheets["summary"].loc[mask, value_col] = score
    detail_mask = sheets["details"]["benchmark"].astype(str).eq(VISUALPUZZLES)
    sheets["details"].loc[detail_mask, "score"] = score
    write_excel(path, sheets)
    write_summary_md(path.with_suffix(".md"), f"{slug} TRACE Final20 Temp0.6 Results", sheets["summary"], sheets.get("metadata"))


def update_selected25(seed_scores: dict[tuple[int, str], float]) -> pd.DataFrame:
    seed42_path = RESULTS_ROOT / "qwen25vl3b_7b_answer_grpo_selected25_greedy_temp06.xlsx"
    sheets = pd.read_excel(seed42_path, sheet_name=None)
    temp = sheets["temp0.6"]
    mask = temp["Task"].astype(str).eq(VISUALPUZZLES)
    temp.loc[mask, "Qwen2.5 3B Base"] = seed_scores[(42, "3B Base")]
    temp.loc[mask, "Qwen2.5 3B Answer GRPO"] = seed_scores[(42, "3B Answer GRPO 500")]
    temp.loc[mask, "Qwen2.5 7B Base"] = seed_scores[(42, "7B Base")]
    temp.loc[mask, "Qwen2.5 7B Answer GRPO"] = seed_scores[(42, "7B Answer GRPO 500")]
    temp.loc[mask, "3B Delta"] = temp.loc[mask, "Qwen2.5 3B Answer GRPO"].values - temp.loc[mask, "Qwen2.5 3B Base"].values
    temp.loc[mask, "7B Delta"] = temp.loc[mask, "Qwen2.5 7B Answer GRPO"].values - temp.loc[mask, "Qwen2.5 7B Base"].values
    write_excel(seed42_path, sheets)

    for seed in (43, 44):
        path = RESULTS_ROOT / f"trace_selected25_full_temp06_seed{seed}_answer_3b7b_results.xlsx"
        sheets = pd.read_excel(path, sheet_name=None)
        summary = sheets["summary"]
        mask = summary["benchmark"].astype(str).eq(VISUALPUZZLES)
        summary.loc[mask, "Base"] = seed_scores[(seed, "3B Base")]
        summary.loc[mask, "Answer GRPO 500"] = seed_scores[(seed, "3B Answer GRPO 500")]
        summary.loc[mask, "7B Base"] = seed_scores[(seed, "7B Base")]
        summary.loc[mask, "7B Answer GRPO 500"] = seed_scores[(seed, "7B Answer GRPO 500")]

        m3 = sheets["3b_model"]["benchmark"].astype(str).eq(VISUALPUZZLES)
        sheets["3b_model"].loc[m3, "base_score"] = seed_scores[(seed, "3B Base")]
        sheets["3b_model"].loc[m3, "Answer GRPO 500_score"] = seed_scores[(seed, "3B Answer GRPO 500")]
        sheets["3b_model"].loc[m3, "Answer GRPO 500_delta"] = (
            sheets["3b_model"].loc[m3, "Answer GRPO 500_score"].values
            - sheets["3b_model"].loc[m3, "base_score"].values
        )
        m7 = sheets["7b_model"]["benchmark"].astype(str).eq(VISUALPUZZLES)
        sheets["7b_model"].loc[m7, "base_score"] = seed_scores[(seed, "7B Base")]
        sheets["7b_model"].loc[m7, "7B Answer GRPO 500_score"] = seed_scores[(seed, "7B Answer GRPO 500")]
        sheets["7b_model"].loc[m7, "7B Answer GRPO 500_delta"] = (
            sheets["7b_model"].loc[m7, "7B Answer GRPO 500_score"].values
            - sheets["7b_model"].loc[m7, "base_score"].values
        )
        for model_name, slug in ANSWER_3B7B_SLUGS.items():
            detail = sheets["details"]["benchmark"].astype(str).eq(VISUALPUZZLES) & sheets["details"]["model_slug"].astype(str).eq(slug)
            sheets["details"].loc[detail, "score"] = seed_scores[(seed, model_name)]
        write_excel(path, sheets)
        write_summary_md(path.with_suffix(".md"), f"TRACE Selected25 Full Temp0.6 Seed{seed} Answer 3B/7B Results", summary, sheets.get("metadata"))

    mean_path = RESULTS_ROOT / "qwen25vl3b_7b_answer_grpo_selected25_temp06_3seed_mean_std.xlsx"
    sheets = pd.read_excel(mean_path, sheet_name=None)
    seed_values = sheets["seed_values"]
    for seed in (42, 43, 44):
        mask = seed_values["seed"].eq(seed) & seed_values["Task"].astype(str).eq(VISUALPUZZLES)
        seed_values.loc[mask, "3B Base"] = seed_scores[(seed, "3B Base")]
        seed_values.loc[mask, "3B Answer GRPO 500"] = seed_scores[(seed, "3B Answer GRPO 500")]
        seed_values.loc[mask, "7B Base"] = seed_scores[(seed, "7B Base")]
        seed_values.loc[mask, "7B Answer GRPO 500"] = seed_scores[(seed, "7B Answer GRPO 500")]
        seed_values.loc[mask, "3B Delta"] = seed_values.loc[mask, "3B Answer GRPO 500"].values - seed_values.loc[mask, "3B Base"].values
        seed_values.loc[mask, "7B Delta"] = seed_values.loc[mask, "7B Answer GRPO 500"].values - seed_values.loc[mask, "7B Base"].values

    metric_cols = ["3B Base", "3B Answer GRPO 500", "3B Delta", "7B Base", "7B Answer GRPO 500", "7B Delta"]
    rows: list[dict[str, Any]] = []
    tasks = [task for task in sheets["mean_std"]["Task"].tolist() if task != "Average"]
    for task in tasks:
        group = seed_values[seed_values["Task"].astype(str).eq(str(task))]
        row: dict[str, Any] = {"Task": task, "n_seeds": int(len(group))}
        for metric in metric_cols:
            row[f"{metric} mean"] = round(float(group[metric].mean()), 2)
            row[f"{metric} std"] = round(float(group[metric].std(ddof=1)), 2)
        rows.append(row)
    mean_std = pd.DataFrame(rows)
    avg: dict[str, Any] = {"Task": "Average", "n_seeds": ""}
    for metric in metric_cols:
        avg[f"{metric} mean"] = round(float(mean_std[f"{metric} mean"].mean()), 2)
        avg[f"{metric} std"] = ""
    mean_std = pd.concat([mean_std, pd.DataFrame([avg])], ignore_index=True)
    sheets["mean_std"] = mean_std
    sheets["seed_values"] = seed_values
    metadata = sheets["metadata"]
    repair = {
        "item": "visualpuzzles_repair",
        "value": "Re-scored cached Qwen3 extraction outputs with VisualPuzzles A-D option contract.",
        "note": "No generation or judge rerun.",
    }
    if not metadata["item"].astype(str).eq(repair["item"]).any():
        metadata = pd.concat([metadata, pd.DataFrame([repair])], ignore_index=True)
    sheets["metadata"] = metadata
    write_excel(mean_path, sheets)
    lines = [
        "# Qwen2.5-VL 3B/7B Answer GRPO Selected25 Temp0.6 3-Seed Mean/Std",
        "",
        "MathVerse scoring note: local Qwen3-32B judge outputs of the form `Judgement: 1` are counted as correct.",
        "",
        "ScreenSpot/TableVQABench note: cached predictions are deterministically re-parsed for final-answer wrappers and positional `pyautogui.click(x, y)` calls; no generation or judge rerun was used.",
        "",
        "VisualPuzzles note: cached Qwen3 extraction outputs are re-scored with the benchmark-wide A-D option contract; no generation or judge rerun was used.",
        "",
        "## Mean / Std",
        dataframe_to_markdown(mean_std),
        "",
        "## Seed Values",
        dataframe_to_markdown(seed_values),
        "",
        "## Metadata",
        metadata.to_markdown(index=False),
        "",
    ]
    mean_path.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")
    return mean_std


def update_ann29(score: float) -> None:
    path = Path(ANNOTATION_3B["xlsx"])
    slug = str(ANNOTATION_3B["slug"])
    sheets = pd.read_excel(path, sheet_name=None)
    mask = sheets["summary"]["benchmark"].astype(str).eq(VISUALPUZZLES)
    sheets["summary"].loc[mask, slug] = score
    detail = sheets["details"]["benchmark"].astype(str).eq(VISUALPUZZLES)
    sheets["details"].loc[detail, "score"] = score
    write_excel(path, sheets)
    write_summary_md(path.with_suffix(".md"), "TRACE Ann29 Temp0.6 3B Annotation Results", sheets["summary"], sheets.get("metadata"))


def update_extra7(seed42_scores: dict[str, float]) -> None:
    path = RESULTS_ROOT / "trace_extra7_full_temp06_4096_results.xlsx"
    sheets = pd.read_excel(path, sheet_name=None)
    mask = sheets["summary"]["benchmark"].astype(str).eq(VISUALPUZZLES)
    sheets["summary"].loc[mask, "Base"] = seed42_scores["3B Base"]
    sheets["summary"].loc[mask, "trace-qwen25vl3b-easyr1-all1000-answer-nokl-step500"] = seed42_scores["3B Answer GRPO 500"]
    sheets["summary"].loc[mask, "qwen25vl7b-base"] = seed42_scores["7B Base"]
    sheets["summary"].loc[mask, "trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500"] = seed42_scores["7B Answer GRPO 500"]
    m3 = sheets["3b_model"]["benchmark"].astype(str).eq(VISUALPUZZLES)
    sheets["3b_model"].loc[m3, "base_score"] = seed42_scores["3B Base"]
    sheets["3b_model"].loc[m3, "trace-qwen25vl3b-easyr1-all1000-answer-nokl-step500_score"] = seed42_scores["3B Answer GRPO 500"]
    sheets["3b_model"].loc[m3, "trace-qwen25vl3b-easyr1-all1000-answer-nokl-step500_delta"] = seed42_scores["3B Answer GRPO 500"] - seed42_scores["3B Base"]
    m7 = sheets["7b_model"]["benchmark"].astype(str).eq(VISUALPUZZLES)
    sheets["7b_model"].loc[m7, "base_score"] = seed42_scores["7B Base"]
    sheets["7b_model"].loc[m7, "trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500_score"] = seed42_scores["7B Answer GRPO 500"]
    sheets["7b_model"].loc[m7, "trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500_delta"] = seed42_scores["7B Answer GRPO 500"] - seed42_scores["7B Base"]
    for model_name, slug in ANSWER_3B7B_SLUGS.items():
        detail = sheets["details"]["benchmark"].astype(str).eq(VISUALPUZZLES) & sheets["details"]["model_slug"].astype(str).eq(slug)
        sheets["details"].loc[detail, "score"] = seed42_scores[model_name]
    write_excel(path, sheets)
    write_summary_md(path.with_suffix(".md"), "TRACE Extra7 Full Temp0.6 Results", sheets["summary"], sheets.get("metadata"))


def update_final20(mean_std: pd.DataFrame, ann_score: float, external_scores: dict[str, float]) -> None:
    model_path = RESULTS_ROOT / "trace_final20_temp06_3b7b_model_results.xlsx"
    all_path = RESULTS_ROOT / "trace_final20_temp06_3b7b_all_methods_results.xlsx"
    model_sheets = pd.read_excel(model_path, sheet_name=None)
    all_sheets = pd.read_excel(all_path, sheet_name=None)
    row = mean_std[mean_std["Task"].astype(str).eq(VISUALPUZZLES)].iloc[0]
    for sheets in (model_sheets, all_sheets):
        m3 = sheets["3B"]["Benchmark"].astype(str).eq(VISUALPUZZLES)
        sheets["3B"].loc[m3, "Qwen2.5-VL-3B Base (3-seed avg)"] = row["3B Base mean"]
        sheets["3B"].loc[m3, "Qwen2.5-VL-3B Answer GRPO 500 (3-seed avg)"] = row["3B Answer GRPO 500 mean"]
        sheets["3B"].loc[m3, "Qwen2.5-VL-3B Annotation GRPO 500 (seed42)"] = round(ann_score, 2)
        m7 = sheets["7B"]["Benchmark"].astype(str).eq(VISUALPUZZLES)
        sheets["7B"].loc[m7, "Qwen2.5-VL-7B Base (3-seed avg)"] = row["7B Base mean"]
        sheets["7B"].loc[m7, "Qwen2.5-VL-7B Answer GRPO 500 (3-seed avg)"] = row["7B Answer GRPO 500 mean"]
        if sheets is all_sheets:
            for column, score in external_scores.items():
                sheets["7B"].loc[m7, column] = round(score, 2)
        update_average_row(
            sheets["3B"],
            [
                "Qwen2.5-VL-3B Base (3-seed avg)",
                "Qwen2.5-VL-3B Answer GRPO 500 (3-seed avg)",
                "Qwen2.5-VL-3B Annotation GRPO 500 (seed42)",
            ],
        )
        update_average_row(
            sheets["7B"],
            [col for col in sheets["7B"].columns if col not in {"Benchmark", "Rows"}],
        )
    if "metadata" in all_sheets:
        metadata = all_sheets["metadata"]
        row_meta = {
            "key": "visualpuzzles_repair",
            "value": "Re-scored cached Qwen3 extraction outputs with VisualPuzzles A-D option contract; no generation/judge rerun.",
        }
        if not metadata["key"].astype(str).eq(row_meta["key"]).any():
            metadata = pd.concat([metadata, pd.DataFrame([row_meta])], ignore_index=True)
        all_sheets["metadata"] = metadata
    write_excel(model_path, model_sheets)
    write_excel(all_path, all_sheets)
    write_final20_md(all_path.with_suffix(".md"), all_sheets)


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair VisualPuzzles cached LLM-extraction scores.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    seed_scores: dict[tuple[int, str], float] = {}
    for seed, root in SELECTED25_SCORE_ROOTS.items():
        for model_name, slug in ANSWER_3B7B_SLUGS.items():
            score, fixed = repair_judged_table(judged_path(root, slug), dry_run=args.dry_run)
            seed_scores[(seed, model_name)] = score
            print(f"[selected25] seed={seed} model={model_name} score={score:.4f} fixed_invalid={fixed}")

    external_scores: dict[str, float] = {}
    for column, (slug, root, _) in FINAL20_EXTERNAL.items():
        score, fixed = repair_judged_table(judged_path(root, slug), dry_run=args.dry_run)
        external_scores[column] = score
        print(f"[final20] model={column} score={score:.4f} fixed_invalid={fixed}")

    ann_score, ann_fixed = repair_judged_table(judged_path(Path(ANNOTATION_3B["root"]), str(ANNOTATION_3B["slug"])), dry_run=args.dry_run)
    print(f"[annotation] score={ann_score:.4f} fixed_invalid={ann_fixed}")

    if args.dry_run:
        return

    mean_std = update_selected25(seed_scores)
    update_extra7({name: seed_scores[(42, name)] for name in ANSWER_3B7B_SLUGS})
    for column, (slug, _, path) in FINAL20_EXTERNAL.items():
        update_single_model_workbook(path, slug, external_scores[column])
    update_ann29(ann_score)
    update_final20(mean_std, ann_score, external_scores)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
VLMEVAL_ROOT = REPO_ROOT / "external" / "VLMEvalKit"
if str(VLMEVAL_ROOT) not in sys.path:
    sys.path.insert(0, str(VLMEVAL_ROOT))

from vlmeval.dataset.utils.tablevqabench import (  # noqa: E402
    evaluate_fintabnet,
    evaluate_tabfact,
    evaluate_wtq,
)


SHM_ROOT = Path("/dev/shm/trace_rlvr")
RESULTS_ROOT = REPO_ROOT / "results"
IMAGE_ROOTS = [
    SHM_ROOT / "LMUData" / "images",
    Path.home() / "LMUData" / "images",
]

ANSWER_3B7B_SLUGS = {
    "3B Base": "qwen25vl3b-base",
    "3B Answer GRPO 500": "trace-qwen25vl3b-easyr1-all1000-answer-nokl-step500",
    "7B Base": "qwen25vl7b-base",
    "7B Answer GRPO 500": "trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500",
}

SELECTED25_SOURCES = {
    42: {
        "screenspot": SHM_ROOT / "trace_candidate24_full_temp06_4096_20260713T103556Z" / "runs" / "screenspot",
        "tablevqabench": SHM_ROOT / "trace_extra7_full_temp06_4096_20260713T103556Z" / "runs" / "tablevqabench",
    },
    43: {
        "screenspot": SHM_ROOT
        / "trace_selected25_full_temp06_4096_seed43_44_answer_3b7b_20260714T065129Z"
        / "seed_43"
        / "runs"
        / "screenspot",
        "tablevqabench": SHM_ROOT
        / "trace_selected25_full_temp06_4096_seed43_44_answer_3b7b_20260714T065129Z"
        / "seed_43"
        / "runs"
        / "tablevqabench",
    },
    44: {
        "screenspot": SHM_ROOT
        / "trace_selected25_full_temp06_4096_seed43_44_answer_3b7b_20260714T065129Z"
        / "seed_44"
        / "runs"
        / "screenspot",
        "tablevqabench": SHM_ROOT
        / "trace_selected25_full_temp06_4096_seed43_44_answer_3b7b_20260714T065129Z"
        / "seed_44"
        / "runs"
        / "tablevqabench",
    },
}

FINAL20_EXTERNAL = {
    "OpenMOSS Game-RL Qwen2.5-VL-7B (seed42)": (
        "game-rl-qwen25vl7b",
        SHM_ROOT / "trace_final20_temp06_seed42_game-rl-qwen25vl7b_20260714T162908Z" / "runs",
        RESULTS_ROOT / "trace_final20_temp06_seed42_game-rl-qwen25vl7b_20260714T162908Z_results.xlsx",
    ),
    "Sphinx Qwen2.5-VL-7B 500 (seed42)": (
        "sphinx-qwen7b-500",
        SHM_ROOT / "trace_final20_temp06_seed42_sphinx-qwen7b-500_20260714T172623Z" / "runs",
        RESULTS_ROOT / "trace_final20_temp06_seed42_sphinx-qwen7b-500_20260714T172623Z_results.xlsx",
    ),
    "PCGRPO Qwen2.5-VL-7B Jigsaw CARE (seed42)": (
        "pcgrpo-qwen25vl7b-jigsaw-care",
        SHM_ROOT / "trace_final20_temp06_seed42_pcgrpo-qwen25vl7b-jigsaw-care_20260714T182351Z" / "runs",
        RESULTS_ROOT / "trace_final20_temp06_seed42_pcgrpo-qwen25vl7b-jigsaw-care_20260714T182351Z_results.xlsx",
    ),
    "Vero Qwen2.5-VL-7B (seed42)": (
        "vero-qwen25-7b",
        SHM_ROOT / "trace_final20_temp06_seed42_vero-qwen25-7b_20260714T192431Z" / "runs",
        RESULTS_ROOT / "trace_final20_temp06_seed42_vero-qwen25-7b_20260714T192431Z_results.xlsx",
    ),
}

ANNOTATION_3B = {
    "slug": "trace-qwen25vl3b-rlvr-ann-additive-0p50-sectioned-step500",
    "runs": SHM_ROOT / "trace_ann29_temp06_4096_20260713T193234Z" / "runs",
    "xlsx": RESULTS_ROOT / "trace_ann29_temp06_4096_results.xlsx",
}


def clean_answer(text: str) -> str:
    text = re.sub(r"</?answer>", "", text, flags=re.I).strip()
    text = re.sub(r"^\s*[:：,\-]+\s*", "", text).strip()
    text = text.strip("` \n\t\r").strip("\"'")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) > 1 and len(lines[0]) <= 80:
        text = lines[0]
    return text.strip().strip("\"'")


def last_boxed(text: str) -> str | None:
    values: list[str] = []
    for match in re.finditer(r"\\boxed\s*\{", text):
        start = match.end()
        depth = 1
        pos = start
        while pos < len(text) and depth:
            if text[pos] == "{":
                depth += 1
            elif text[pos] == "}":
                depth -= 1
            pos += 1
        if depth == 0:
            values.append(text[start : pos - 1])
    return values[-1] if values else None


def extract_final_answer(value: Any) -> str:
    text = "" if pd.isna(value) else str(value).strip()
    if not text:
        return text
    tagged = list(re.finditer(r"<answer>\s*(.*?)\s*</answer>", text, flags=re.I | re.S))
    if tagged:
        return clean_answer(tagged[-1].group(1))
    boxed = last_boxed(text)
    if boxed is not None:
        return clean_answer(boxed)
    json_match = re.search(r"\{.*?\"answer\"\s*:\s*.*?\}", text, flags=re.S)
    if json_match:
        try:
            payload = json.loads(json_match.group(0))
            if "answer" in payload:
                return clean_answer(str(payload["answer"]))
        except Exception:
            pass
    return text


def tablevqabench_score(prediction_table: Path) -> float:
    data = pd.read_excel(prediction_table)
    data = data.copy()
    data["prediction"] = data["prediction"].map(extract_final_answer).fillna("__missing_prediction__").map(str)
    data["answer"] = data["answer"].fillna("__missing_answer__").map(str)

    scores: list[float] = []
    for split, group in data.groupby("split"):
        rows = group.to_dict("records")
        if split == "fintabnetqa":
            meta = evaluate_fintabnet(rows, ["accuracy"])
        elif split == "vtabfact":
            meta = evaluate_tabfact(rows, ["accuracy"])
        elif split in {"vwtq", "vwtq_syn"}:
            meta = evaluate_wtq(rows, ["accuracy"])
        else:
            continue
        scores.extend(float(value) for value in meta["average_scores"])
    if not scores:
        raise ValueError(f"No TableVQABench split scores in {prediction_table}")
    return sum(scores) / len(scores)


CLICK_CALL_RE = re.compile(r"pyautogui\.(?:click|moveTo)\s*\((.*?)\)", flags=re.I | re.S)
XY_RE = re.compile(r"(?<![A-Za-z])x\s*=\s*(-?\d+(?:\.\d+)?)\s*,\s*y\s*=\s*(-?\d+(?:\.\d+)?)", flags=re.I)
NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")


def extract_click_point(value: Any) -> tuple[float, float] | None:
    text = "" if pd.isna(value) else str(value)
    candidates: list[str] = []
    candidates.extend(match.group(1) for match in re.finditer(r"<answer>\s*(.*?)\s*</answer>", text, flags=re.I | re.S))
    boxed = last_boxed(text)
    if boxed is not None:
        candidates.append(boxed)
    candidates.append(text)

    for candidate in reversed(candidates):
        calls = list(CLICK_CALL_RE.finditer(candidate))
        if calls:
            args = calls[-1].group(1)
            xy = XY_RE.search(args)
            if xy:
                return float(xy.group(1)), float(xy.group(2))
            numbers = NUMBER_RE.findall(args)
            if len(numbers) >= 2:
                return float(numbers[0]), float(numbers[1])
        xy = XY_RE.search(candidate)
        if xy:
            return float(xy.group(1)), float(xy.group(2))
    return None


def image_size(sub_dataset: Any, image_path: Any) -> tuple[int, int]:
    rel = Path(str(sub_dataset)) / str(image_path)
    for root in IMAGE_ROOTS:
        path = root / rel
        if path.exists():
            with Image.open(path) as image:
                return image.size
    raise FileNotFoundError(rel)


def screenspot_score(prediction_table: Path) -> float:
    data = pd.read_excel(prediction_table)
    correct = 0
    for _, row in data.iterrows():
        bbox = row["bbox"] if isinstance(row["bbox"], list) else ast.literal_eval(str(row["bbox"]))
        x1, y1, width, height = [float(value) for value in bbox]
        x2 = x1 + width - 1
        y2 = y1 + height - 1
        image_width, image_height = image_size(row.get("SUB_DATASET", "ScreenSpot"), row["image_path"])
        box = (
            max(x1, 0) / image_width,
            max(y1, 0) / image_height,
            max(x2, 0) / image_width,
            max(y2, 0) / image_height,
        )
        point = extract_click_point(row["prediction"])
        if point is None:
            continue
        px, py = point
        if px > 1 or py > 1 or px < 0 or py < 0:
            px /= image_width
            py /= image_height
        if box[0] <= px <= box[2] and box[1] <= py <= box[3]:
            correct += 1
    return correct / len(data) * 100.0


def prediction_path(root: Path, slug: str, benchmark: str) -> Path:
    if benchmark == "ScreenSpot":
        return root / slug / "vlmevalkit_defaults_sample200" / "ScreenSpot_predictions.xlsx"
    if benchmark == "TableVQABench":
        return root / slug / "vlmevalkit_defaults" / "TableVQABench_predictions.xlsx"
    raise ValueError(benchmark)


def score_prediction(path: Path, benchmark: str) -> float:
    if not path.exists():
        raise FileNotFoundError(path)
    if benchmark == "ScreenSpot":
        return screenspot_score(path)
    if benchmark == "TableVQABench":
        return tablevqabench_score(path)
    raise ValueError(benchmark)


def round_score(value: float, digits: int = 2) -> float:
    return round(float(value), digits)


def recompute_selected25_scores() -> dict[tuple[int, str, str], float]:
    scores: dict[tuple[int, str, str], float] = {}
    for seed, roots in SELECTED25_SOURCES.items():
        for model_name, slug in ANSWER_3B7B_SLUGS.items():
            for benchmark in ("ScreenSpot", "TableVQABench"):
                key = "screenspot" if benchmark == "ScreenSpot" else "tablevqabench"
                scores[(seed, benchmark, model_name)] = score_prediction(
                    prediction_path(roots[key], slug, benchmark),
                    benchmark,
                )
    return scores


def recompute_final20_extra_scores() -> dict[tuple[str, str], float]:
    scores: dict[tuple[str, str], float] = {}
    ann_slug = str(ANNOTATION_3B["slug"])
    ann_runs = Path(ANNOTATION_3B["runs"])
    for benchmark in ("ScreenSpot", "TableVQABench"):
        scores[(benchmark, "Qwen2.5-VL-3B Annotation GRPO 500 (seed42)")] = score_prediction(
            prediction_path(ann_runs / benchmark.lower(), ann_slug, benchmark),
            benchmark,
        )
    for column, (slug, runs_root, _) in FINAL20_EXTERNAL.items():
        for benchmark in ("ScreenSpot", "TableVQABench"):
            scores[(benchmark, column)] = score_prediction(
                prediction_path(Path(runs_root) / benchmark.lower(), slug, benchmark),
                benchmark,
            )
    return scores


def update_average_row(df: pd.DataFrame, label_col: str, numeric_cols: list[str]) -> None:
    mask = df[label_col].astype(str).eq("Average")
    if not mask.any():
        return
    body = df[~mask]
    for col in numeric_cols:
        df.loc[mask, col] = body[col].dropna().astype(float).mean()
    if "Rows" in df.columns:
        df.loc[mask, "Rows"] = math.nan


def write_excel(path: Path, sheets: dict[str, pd.DataFrame]) -> None:
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=name, index=False)


def dataframe_to_markdown(frame: pd.DataFrame) -> str:
    return frame.to_markdown(index=False, floatfmt=".2f")


def write_selected25_mean_std_md(path: Path, mean_std: pd.DataFrame, seed_values: pd.DataFrame, metadata: pd.DataFrame) -> None:
    lines = [
        "# Qwen2.5-VL 3B/7B Answer GRPO Selected25 Temp0.6 3-Seed Mean/Std",
        "",
        "MathVerse scoring note: local Qwen3-32B judge outputs of the form `Judgement: 1` are counted as correct.",
        "",
        "ScreenSpot/TableVQABench note: cached predictions are deterministically re-parsed for final-answer wrappers and positional `pyautogui.click(x, y)` calls; no generation or judge rerun was used.",
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
    path.write_text("\n".join(lines), encoding="utf-8")


def write_summary_md(path: Path, title: str, summary: pd.DataFrame, metadata: pd.DataFrame | None = None) -> None:
    lines = [
        f"# {title}",
        "",
        "Deterministic repair note: ScreenSpot/TableVQABench cached predictions are re-parsed for final-answer wrappers and positional `pyautogui.click(x, y)` calls; no generation or judge rerun was used.",
        "",
        dataframe_to_markdown(summary),
        "",
    ]
    if metadata is not None:
        lines.extend(["## Metadata", metadata.to_markdown(index=False), ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def write_final20_all_methods_md(path: Path, sheets: dict[str, pd.DataFrame]) -> None:
    lines = [
        "# TRACE Final20 Temp0.6 3B/7B All Methods Results",
        "",
        "Deterministic repair note: ScreenSpot/TableVQABench cached predictions are re-parsed for final-answer wrappers and positional `pyautogui.click(x, y)` calls; no generation or judge rerun was used.",
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


def update_selected25_workbooks(selected_scores: dict[tuple[int, str, str], float]) -> None:
    seed42_path = RESULTS_ROOT / "qwen25vl3b_7b_answer_grpo_selected25_greedy_temp06.xlsx"
    sheets = pd.read_excel(seed42_path, sheet_name=None)
    temp = sheets["temp0.6"]
    for benchmark in ("ScreenSpot", "TableVQABench"):
        mask = temp["Task"].astype(str).eq(benchmark)
        temp.loc[mask, "Qwen2.5 3B Base"] = round_score(selected_scores[(42, benchmark, "3B Base")], 4)
        temp.loc[mask, "Qwen2.5 3B Answer GRPO"] = round_score(selected_scores[(42, benchmark, "3B Answer GRPO 500")], 4)
        temp.loc[mask, "Qwen2.5 7B Base"] = round_score(selected_scores[(42, benchmark, "7B Base")], 4)
        temp.loc[mask, "Qwen2.5 7B Answer GRPO"] = round_score(selected_scores[(42, benchmark, "7B Answer GRPO 500")], 4)
        temp.loc[mask, "3B Delta"] = temp.loc[mask, "Qwen2.5 3B Answer GRPO"].values - temp.loc[mask, "Qwen2.5 3B Base"].values
        temp.loc[mask, "7B Delta"] = temp.loc[mask, "Qwen2.5 7B Answer GRPO"].values - temp.loc[mask, "Qwen2.5 7B Base"].values
    write_excel(seed42_path, sheets)

    for seed in (43, 44):
        path = RESULTS_ROOT / f"trace_selected25_full_temp06_seed{seed}_answer_3b7b_results.xlsx"
        sheets = pd.read_excel(path, sheet_name=None)
        for benchmark in ("ScreenSpot", "TableVQABench"):
            mask = sheets["summary"]["benchmark"].astype(str).eq(benchmark)
            sheets["summary"].loc[mask, "Base"] = selected_scores[(seed, benchmark, "3B Base")]
            sheets["summary"].loc[mask, "Answer GRPO 500"] = selected_scores[(seed, benchmark, "3B Answer GRPO 500")]
            sheets["summary"].loc[mask, "7B Base"] = selected_scores[(seed, benchmark, "7B Base")]
            sheets["summary"].loc[mask, "7B Answer GRPO 500"] = selected_scores[(seed, benchmark, "7B Answer GRPO 500")]

            mask3 = sheets["3b_model"]["benchmark"].astype(str).eq(benchmark)
            sheets["3b_model"].loc[mask3, "base_score"] = selected_scores[(seed, benchmark, "3B Base")]
            sheets["3b_model"].loc[mask3, "Answer GRPO 500_score"] = selected_scores[(seed, benchmark, "3B Answer GRPO 500")]
            sheets["3b_model"].loc[mask3, "Answer GRPO 500_delta"] = (
                sheets["3b_model"].loc[mask3, "Answer GRPO 500_score"].values
                - sheets["3b_model"].loc[mask3, "base_score"].values
            )

            mask7 = sheets["7b_model"]["benchmark"].astype(str).eq(benchmark)
            sheets["7b_model"].loc[mask7, "base_score"] = selected_scores[(seed, benchmark, "7B Base")]
            sheets["7b_model"].loc[mask7, "7B Answer GRPO 500_score"] = selected_scores[(seed, benchmark, "7B Answer GRPO 500")]
            sheets["7b_model"].loc[mask7, "7B Answer GRPO 500_delta"] = (
                sheets["7b_model"].loc[mask7, "7B Answer GRPO 500_score"].values
                - sheets["7b_model"].loc[mask7, "base_score"].values
            )

            for model_name, slug in ANSWER_3B7B_SLUGS.items():
                detail_mask = sheets["details"]["benchmark"].astype(str).eq(benchmark) & sheets["details"]["model_slug"].astype(str).eq(slug)
                sheets["details"].loc[detail_mask, "score"] = selected_scores[(seed, benchmark, model_name)]
        write_excel(path, sheets)
        write_summary_md(
            path.with_suffix(".md"),
            f"TRACE Selected25 Full Temp0.6 Seed{seed} Answer 3B/7B Results",
            sheets["summary"],
            sheets.get("metadata"),
        )


def update_mean_std_workbook(selected_scores: dict[tuple[int, str, str], float]) -> pd.DataFrame:
    path = RESULTS_ROOT / "qwen25vl3b_7b_answer_grpo_selected25_temp06_3seed_mean_std.xlsx"
    sheets = pd.read_excel(path, sheet_name=None)
    seed_values = sheets["seed_values"]
    for seed in (42, 43, 44):
        for benchmark in ("ScreenSpot", "TableVQABench"):
            mask = seed_values["seed"].eq(seed) & seed_values["Task"].astype(str).eq(benchmark)
            seed_values.loc[mask, "3B Base"] = round_score(selected_scores[(seed, benchmark, "3B Base")], 4)
            seed_values.loc[mask, "3B Answer GRPO 500"] = round_score(selected_scores[(seed, benchmark, "3B Answer GRPO 500")], 4)
            seed_values.loc[mask, "7B Base"] = round_score(selected_scores[(seed, benchmark, "7B Base")], 4)
            seed_values.loc[mask, "7B Answer GRPO 500"] = round_score(selected_scores[(seed, benchmark, "7B Answer GRPO 500")], 4)
            seed_values.loc[mask, "3B Delta"] = seed_values.loc[mask, "3B Answer GRPO 500"].values - seed_values.loc[mask, "3B Base"].values
            seed_values.loc[mask, "7B Delta"] = seed_values.loc[mask, "7B Answer GRPO 500"].values - seed_values.loc[mask, "7B Base"].values

    metric_cols = ["3B Base", "3B Answer GRPO 500", "3B Delta", "7B Base", "7B Answer GRPO 500", "7B Delta"]
    rows: list[dict[str, Any]] = []
    tasks = [task for task in sheets["mean_std"]["Task"].tolist() if task != "Average"]
    for task in tasks:
        group = seed_values[seed_values["Task"].astype(str).eq(str(task))]
        row: dict[str, Any] = {"Task": task, "n_seeds": int(len(group))}
        for metric in metric_cols:
            row[f"{metric} mean"] = round_score(group[metric].astype(float).mean(), 2)
            row[f"{metric} std"] = round_score(group[metric].astype(float).std(ddof=1), 2)
        rows.append(row)
    mean_std = pd.DataFrame(rows)
    avg_row: dict[str, Any] = {"Task": "Average", "n_seeds": ""}
    for metric in metric_cols:
        avg_row[f"{metric} mean"] = round_score(mean_std[f"{metric} mean"].astype(float).mean(), 2)
        avg_row[f"{metric} std"] = ""
    mean_std = pd.concat([mean_std, pd.DataFrame([avg_row])], ignore_index=True)
    sheets["mean_std"] = mean_std
    sheets["seed_values"] = seed_values

    metadata = sheets["metadata"]
    repair = {
        "item": "screenspot_table_repair",
        "value": "ScreenSpot positional clicks and TableVQABench final-answer wrappers re-parsed from cached predictions.",
        "note": "No generation or judge rerun.",
    }
    if not metadata["item"].astype(str).eq(repair["item"]).any():
        metadata = pd.concat([metadata, pd.DataFrame([repair])], ignore_index=True)
    sheets["metadata"] = metadata
    write_excel(path, sheets)
    write_selected25_mean_std_md(path.with_suffix(".md"), mean_std, seed_values, metadata)
    return mean_std


def update_single_model_result(path: Path, slug: str, scores: dict[tuple[str, str], float]) -> None:
    sheets = pd.read_excel(path, sheet_name=None)
    for benchmark in ("ScreenSpot", "TableVQABench"):
        score = scores[(benchmark, slug)]
        summary_mask = sheets["summary"]["benchmark"].astype(str).eq(benchmark)
        value_col = next(col for col in sheets["summary"].columns if col == slug or col.endswith(slug))
        sheets["summary"].loc[summary_mask, value_col] = score
        if "details" in sheets:
            detail_mask = sheets["details"]["benchmark"].astype(str).eq(benchmark)
            sheets["details"].loc[detail_mask, "score"] = score
    write_excel(path, sheets)
    write_summary_md(path.with_suffix(".md"), f"{slug} TRACE Final20 Temp0.6 Results", sheets["summary"], sheets.get("metadata"))


def update_annotation_result(extra_scores: dict[tuple[str, str], float]) -> None:
    slug = str(ANNOTATION_3B["slug"])
    path = Path(ANNOTATION_3B["xlsx"])
    sheets = pd.read_excel(path, sheet_name=None)
    for benchmark in ("ScreenSpot", "TableVQABench"):
        score = extra_scores[(benchmark, "Qwen2.5-VL-3B Annotation GRPO 500 (seed42)")]
        for sheet_name in ("summary", "details"):
            frame = sheets[sheet_name]
            mask = frame["benchmark"].astype(str).eq(benchmark)
            if sheet_name == "summary":
                frame.loc[mask, slug] = score
            else:
                frame.loc[mask, "score"] = score
    write_excel(path, sheets)
    write_summary_md(path.with_suffix(".md"), "TRACE Ann29 Temp0.6 3B Annotation Results", sheets["summary"], sheets.get("metadata"))


def update_final20_workbooks(mean_std: pd.DataFrame, extra_scores: dict[tuple[str, str], float]) -> None:
    model_path = RESULTS_ROOT / "trace_final20_temp06_3b7b_model_results.xlsx"
    all_path = RESULTS_ROOT / "trace_final20_temp06_3b7b_all_methods_results.xlsx"

    model_sheets = pd.read_excel(model_path, sheet_name=None)
    all_sheets = pd.read_excel(all_path, sheet_name=None)
    for benchmark in ("ScreenSpot", "TableVQABench"):
        mean_row = mean_std[mean_std["Task"].astype(str).eq(benchmark)].iloc[0]
        values = {
            "Qwen2.5-VL-3B Base (3-seed avg)": mean_row["3B Base mean"],
            "Qwen2.5-VL-3B Answer GRPO 500 (3-seed avg)": mean_row["3B Answer GRPO 500 mean"],
            "Qwen2.5-VL-7B Base (3-seed avg)": mean_row["7B Base mean"],
            "Qwen2.5-VL-7B Answer GRPO 500 (3-seed avg)": mean_row["7B Answer GRPO 500 mean"],
            "Qwen2.5-VL-3B Annotation GRPO 500 (seed42)": round_score(
                extra_scores[(benchmark, "Qwen2.5-VL-3B Annotation GRPO 500 (seed42)")],
                2,
            ),
        }
        for sheet_name, sheets in (("3B", model_sheets), ("3B", all_sheets)):
            frame = sheets[sheet_name]
            mask = frame["Benchmark"].astype(str).eq(benchmark)
            for col in (
                "Qwen2.5-VL-3B Base (3-seed avg)",
                "Qwen2.5-VL-3B Answer GRPO 500 (3-seed avg)",
                "Qwen2.5-VL-3B Annotation GRPO 500 (seed42)",
            ):
                frame.loc[mask, col] = values[col]
        for sheet_name, sheets in (("7B", model_sheets), ("7B", all_sheets)):
            frame = sheets[sheet_name]
            mask = frame["Benchmark"].astype(str).eq(benchmark)
            for col in (
                "Qwen2.5-VL-7B Base (3-seed avg)",
                "Qwen2.5-VL-7B Answer GRPO 500 (3-seed avg)",
            ):
                frame.loc[mask, col] = values[col]
            if sheets is all_sheets:
                for col in FINAL20_EXTERNAL:
                    frame.loc[mask, col] = round_score(extra_scores[(benchmark, col)], 2)

    for sheets in (model_sheets, all_sheets):
        update_average_row(
            sheets["3B"],
            "Benchmark",
            [
                "Qwen2.5-VL-3B Base (3-seed avg)",
                "Qwen2.5-VL-3B Answer GRPO 500 (3-seed avg)",
                "Qwen2.5-VL-3B Annotation GRPO 500 (seed42)",
            ],
        )
        update_average_row(
            sheets["7B"],
            "Benchmark",
            [col for col in sheets["7B"].columns if col not in {"Benchmark", "Rows"}],
        )

    if "metadata" in all_sheets:
        metadata = all_sheets["metadata"]
        row = {"key": "screenspot_table_repair", "value": "Re-parsed cached predictions for ScreenSpot positional clicks and TableVQABench final-answer wrappers; no generation/judge rerun."}
        if not metadata["key"].astype(str).eq(row["key"]).any():
            metadata = pd.concat([metadata, pd.DataFrame([row])], ignore_index=True)
        all_sheets["metadata"] = metadata

    write_excel(model_path, model_sheets)
    write_excel(all_path, all_sheets)
    write_final20_all_methods_md(all_path.with_suffix(".md"), all_sheets)


def update_external_source_workbooks(extra_scores: dict[tuple[str, str], float]) -> None:
    for column, (slug, _, path) in FINAL20_EXTERNAL.items():
        model_col = slug
        update_single_model_result(path, model_col, {(benchmark, model_col): extra_scores[(benchmark, column)] for benchmark in ("ScreenSpot", "TableVQABench")})
    update_annotation_result(extra_scores)


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair deterministic ScreenSpot/TableVQABench result parsing from cached predictions.")
    parser.add_argument("--dry-run", action="store_true", help="Print recomputed scores without writing result workbooks.")
    args = parser.parse_args()

    selected_scores = recompute_selected25_scores()
    extra_scores = recompute_final20_extra_scores()
    print("[selected25 corrections]")
    for key, value in sorted(selected_scores.items()):
        print(f"{key}: {value:.4f}")
    print("[final20 extra corrections]")
    for key, value in sorted(extra_scores.items()):
        print(f"{key}: {value:.4f}")

    if args.dry_run:
        return

    update_selected25_workbooks(selected_scores)
    mean_std = update_mean_std_workbook(selected_scores)
    update_external_source_workbooks(extra_scores)
    update_final20_workbooks(mean_std, extra_scores)


if __name__ == "__main__":
    main()

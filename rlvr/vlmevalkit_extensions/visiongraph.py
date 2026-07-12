from __future__ import annotations

import json
import os
import os.path as osp
import re
import shutil
import subprocess
import urllib.request
from pathlib import Path
from typing import Any

import pandas as pd

from vlmeval.smp import LMUDataRoot, dump, get_intermediate_file_path, load
from .image_base import ImageBaseDataset


class VisionGraphQ3(ImageBaseDataset):
    """VisionGraph Q3-only graph reasoning benchmark.

    The official VisionGraph JSON stores three questions per image:
    node count, edge recognition, and the graph-theory reasoning question.
    This adapter exposes only the third question as a single-turn VQA item.
    Q1/Q2 answers are retained as verifier metadata for deterministic scoring.
    """

    TYPE = "VQA"
    DATASET_URL = {
        "VisionGraph_Q3": "",
        "VisionGraph_Q3_CoT": "",
    }
    DATASET_MD5 = {}

    HF_REPO = "MrSunshy/VisionGraph_hf"
    GITHUB_JSON_ROOT = "https://raw.githubusercontent.com/HITsz-TMG/VisionGraph/main/Dataset"
    TASKS = (
        "Connectivity",
        "Cycle",
        "TopologicalSort",
        "ShortestPath",
        "MaximumFlow",
        "BipartiteGraphMatching",
        "HamlitonPath",
        "GNN",
    )

    PROMPT_DEMANDS = {
        "Connectivity": (
            "If there is a path, conclude with 'Yes, there is a path between the queried nodes. "
            "The path is ...'. If no path exists, conclude with 'No, there is no path between the queried nodes.'."
        ),
        "Cycle": (
            "If there is a cycle, conclude with 'Yes, there is a cycle in the graph. The cycle is ...'. "
            "If no cycle exists, conclude with 'No, there is no cycle in the graph.'."
        ),
        "TopologicalSort": "Give a valid ordering of all nodes.",
        "ShortestPath": "Conclude with the shortest path and its total weight.",
        "MaximumFlow": "Conclude with the maximum flow value.",
        "BipartiteGraphMatching": "Give the applicant-to-job assignment and the number of matched applicants.",
        "HamiltonPath": (
            "If there is a Hamilton path, conclude with 'Yes, there is a path in the graph. The path is ...'. "
            "If no path exists, conclude with 'No, there is no path in the graph.'."
        ),
        "GNN": "Give each node embedding after one graph convolution layer.",
    }

    @classmethod
    def _task_key(cls, task: str) -> str:
        return "HamiltonPath" if task == "HamlitonPath" else task

    @classmethod
    def _dataset_source_root(cls, cache_root: Path) -> Path:
        env_root = os.environ.get("VISIONGRAPH_ROOT")
        if env_root:
            return Path(env_root).expanduser().resolve()
        return cache_root / "VisionGraph_Q3_source"

    @classmethod
    def _download_json(cls, task: str, source_root: Path) -> Path:
        json_path = source_root / "Dataset" / task / "test.json"
        if json_path.exists():
            return json_path

        json_path.parent.mkdir(parents=True, exist_ok=True)
        url = f"{cls.GITHUB_JSON_ROOT}/{task}/test.json"
        urllib.request.urlretrieve(url, json_path)
        return json_path

    @classmethod
    def _extract_archive(cls, archive_path: Path, source_root: Path) -> None:
        source_root.mkdir(parents=True, exist_ok=True)
        extractors = (
            ("7z", ["7z", "x", "-y", f"-o{source_root}", str(archive_path)]),
            ("7zz", ["7zz", "x", "-y", f"-o{source_root}", str(archive_path)]),
            ("unrar", ["unrar", "x", "-o+", str(archive_path), str(source_root)]),
        )
        for executable, cmd in extractors:
            if shutil.which(executable):
                subprocess.run(cmd, check=True)
                return

        raise RuntimeError(
            "VisionGraph image archives are .rar files, but no extractor was found. "
            "Install `7z`/`7zz`/`unrar`, or set VISIONGRAPH_ROOT to a pre-extracted "
            "VisionGraph checkout containing Dataset/<task>/test/*.png."
        )

    @classmethod
    def _ensure_task_images(cls, task: str, source_root: Path) -> None:
        if list(source_root.glob(f"**/{task}/test/*.png")):
            return
        if os.environ.get("VISIONGRAPH_ALLOW_MISSING_IMAGES"):
            return

        from huggingface_hub import hf_hub_download

        archive_path = hf_hub_download(
            repo_id=cls.HF_REPO,
            repo_type="dataset",
            filename=f"{task}.rar",
            local_dir=str(source_root / "archives"),
        )
        cls._extract_archive(Path(archive_path), source_root)

    @classmethod
    def _resolve_image_path(cls, source_root: Path, image_ref: str, task: str) -> Path:
        image_rel = image_ref.lstrip("/")
        basename = osp.basename(image_rel)
        candidates = (
            source_root / image_rel,
            source_root / image_rel.removeprefix("Dataset/"),
            source_root / "Dataset" / task / "test" / basename,
            source_root / task / "test" / basename,
        )
        for candidate in candidates:
            if candidate.exists():
                return candidate.resolve()

        matches = list(source_root.glob(f"**/{basename}"))
        if matches:
            return matches[0].resolve()

        if os.environ.get("VISIONGRAPH_ALLOW_MISSING_IMAGES"):
            return (source_root / "Dataset" / task / "test" / basename).resolve()

        raise FileNotFoundError(
            f"Could not find VisionGraph image {image_ref}. "
            "Set VISIONGRAPH_ROOT to a pre-extracted VisionGraph dataset, or install "
            "7z/unrar so the adapter can extract the HF .rar archives."
        )

    def load_data(self, dataset):
        root = Path(LMUDataRoot())
        data_path = root / f"{dataset}.tsv"
        if data_path.exists() and not os.environ.get("TRACE_FORCE_REBUILD_LOCAL_VLMEVAL"):
            return load(str(data_path))

        source_root = self._dataset_source_root(root)
        rows = []
        for task in self.TASKS:
            json_path = self._download_json(task, source_root)
            self._ensure_task_images(task, source_root)
            with open(json_path, "r", encoding="utf-8") as f:
                items = json.load(f)
            task_key = self._task_key(task)
            for item in items:
                conversations = item["conversations"]
                image_path = self._resolve_image_path(source_root, item["image"], task)
                rows.append(
                    {
                        "index": f"{task}_{item['id']}",
                        "source_id": str(item["id"]),
                        "task": task_key,
                        "difficulty": str(item.get("difficulty", "")),
                        "question": _clean_question(conversations[4]["value"]),
                        "answer": str(conversations[5]["value"]).strip(),
                        "node_answer": str(conversations[1]["value"]).strip(),
                        "edge_answer": str(conversations[3]["value"]).strip(),
                        "image_path": str(image_path),
                    }
                )

        frame = pd.DataFrame(rows)
        dump(frame, str(data_path))
        return frame

    def build_prompt(self, line):
        if isinstance(line, int):
            line = self.data.iloc[line]
        msgs = super().build_prompt(line)
        assert msgs[-1]["type"] == "text"
        task = str(line["task"])
        demand = self.PROMPT_DEMANDS.get(task, "")
        cot = "\nLet's think step by step." if self.dataset_name.endswith("_CoT") else ""
        if demand:
            msgs[-1]["value"] = f"{str(msgs[-1]['value']).strip()}{cot}\n{demand}"
        elif cot:
            msgs[-1]["value"] = f"{str(msgs[-1]['value']).strip()}{cot}"
        return msgs

    def evaluate(self, eval_file, **judge_kwargs):
        del judge_kwargs
        data = load(eval_file)
        scores = []
        parsed_preds = []
        parsed_gts = []
        errors = []

        for _, row in data.iterrows():
            score, parsed_pred, parsed_gt, error = _score_row(row)
            scores.append(float(score))
            parsed_preds.append(parsed_pred)
            parsed_gts.append(parsed_gt)
            errors.append(error)

        data["eval_score"] = scores
        data["eval_pred"] = parsed_preds
        data["eval_gt"] = parsed_gts
        data["eval_error"] = errors
        dump(data, get_intermediate_file_path(eval_file, "_results"))

        rows = []
        for task in sorted(data["task"].unique()):
            mask = data["task"] == task
            sub_scores = [scores[i] for i, flag in enumerate(mask) if flag]
            rows.append(_result_row(task, sub_scores))
        task_scores = [row["acc"] for row in rows]
        rows.append(
            {
                "split": "Macro Avg",
                "tot": len(rows),
                "hit": sum(task_scores),
                "acc": sum(task_scores) / len(task_scores) if task_scores else 0.0,
            }
        )
        rows.append(_result_row("Micro Avg", scores))
        result = pd.DataFrame(rows)
        dump(result, get_intermediate_file_path(eval_file, "_acc", "csv"))
        return result


def _result_row(name: str, scores: list[float]) -> dict[str, Any]:
    return {
        "split": name,
        "tot": len(scores),
        "hit": sum(scores),
        "acc": sum(scores) / len(scores) * 100 if scores else 0.0,
    }


def _clean_question(text: Any) -> str:
    text = str(text or "").replace("<image>", "").strip()
    return re.sub(r"\s+", " ", text)


def _last_boxed(text: str) -> str | None:
    start = 0
    last = None
    while True:
        idx = text.find("\\boxed{", start)
        if idx < 0:
            return last
        i = idx + len("\\boxed{")
        depth = 1
        j = i
        while j < len(text) and depth:
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
            j += 1
        if depth == 0:
            last = text[i:j - 1].strip()
            start = j
        else:
            return last


def _extract_final_text(text: Any) -> str:
    text = str(text or "").strip()
    boxed = _last_boxed(text)
    if boxed:
        return boxed
    answer_tag = re.search(r"<answer>(.*?)</answer>", text, flags=re.I | re.S)
    if answer_tag:
        return answer_tag.group(1).strip()
    matches = list(re.finditer(r"\b(?:final answer|answer|conclusion)\b\s*[:：]?\s*(.+)", text, flags=re.I | re.S))
    if matches:
        return matches[-1].group(1).strip()
    return text


def _ints(text: Any) -> list[int]:
    return [int(x) for x in re.findall(r"-?\d+", str(text or ""))]


def _positive_ints(text: Any) -> list[int]:
    return [int(x) for x in re.findall(r"\d+", str(text or ""))]


def _parse_tuple_numbers(text: Any) -> list[tuple[int, ...]]:
    tuples = []
    for match in re.finditer(r"\((.*?)\)|<(.*?)>", str(text or "")):
        body = match.group(1) if match.group(1) is not None else match.group(2)
        nums = _ints(body)
        if nums:
            tuples.append(tuple(nums))
    return tuples


def _parse_yes_no(text: Any) -> str | None:
    final = _extract_final_text(text).lower()
    if re.search(r"\b(no|not|none|cannot|can't)\b", final):
        return "no"
    if re.search(r"\b(yes|exists?|exist|connected|reachable|there is)\b", final):
        return "yes"
    return None


def _extract_weight(text: Any) -> int | None:
    final = _extract_final_text(text)
    matches = re.findall(r"(?:total\s+)?weight(?:\s+of|\s+is|=|:)?\s*(-?\d+)", final, flags=re.I)
    if matches:
        return int(matches[-1])
    matches = re.findall(r"(?:maximum\s+flow|flow)(?:\s+from.*?\s+is|\s+is|=|:)?\s*(-?\d+)", final, flags=re.I)
    if matches:
        return int(matches[-1])
    nums = _ints(final)
    return nums[-1] if nums else None


def _extract_sequence_after_marker(text: Any, markers: tuple[str, ...]) -> list[int]:
    final = _extract_final_text(text)
    search = final.lower()
    cut = final
    best_idx = -1
    best_marker = ""
    for marker in markers:
        idx = search.rfind(marker)
        if idx > best_idx:
            best_idx = idx
            best_marker = marker
    if best_idx >= 0:
        cut = final[best_idx + len(best_marker):]
    if " with " in cut.lower():
        cut = re.split(r"\bwith\b", cut, flags=re.I)[0]
    if "." in cut:
        cut = cut.split(".")[0]
    return _ints(cut)


def _undirected_weighted_edges(edge_answer: Any) -> dict[frozenset[int], int]:
    edges = {}
    for tup in _parse_tuple_numbers(edge_answer):
        if len(tup) >= 3:
            edges[frozenset((tup[0], tup[1]))] = tup[2]
    return edges


def _unweighted_edges(edge_answer: Any, directed: bool = False) -> set[Any]:
    edges = set()
    for tup in _parse_tuple_numbers(edge_answer):
        if len(tup) >= 2:
            edges.add((tup[0], tup[1]) if directed else frozenset((tup[0], tup[1])))
    return edges


def _score_row(row: pd.Series) -> tuple[bool, Any, Any, str]:
    task = str(row.get("task", ""))
    pred = row.get("prediction", "")
    answer = row.get("answer", "")
    try:
        if task in {"Connectivity", "Cycle"}:
            pred_yn = _parse_yes_no(pred)
            gt_yn = _parse_yes_no(answer)
            return pred_yn is not None and pred_yn == gt_yn, pred_yn, gt_yn, ""
        if task == "TopologicalSort":
            return _score_topological_sort(row, pred)
        if task == "ShortestPath":
            return _score_shortest_path(row, pred)
        if task == "MaximumFlow":
            pred_flow = _extract_weight(pred)
            gt_flow = _extract_weight(answer)
            return pred_flow is not None and pred_flow == gt_flow, pred_flow, gt_flow, ""
        if task == "BipartiteGraphMatching":
            return _score_bipartite(row, pred)
        if task == "HamiltonPath":
            return _score_hamilton(row, pred)
        if task == "GNN":
            pred_emb = _parse_embeddings(pred)
            gt_emb = _parse_embeddings(answer)
            return bool(pred_emb) and pred_emb == gt_emb, pred_emb, gt_emb, ""
        return False, "", "", f"unsupported task {task}"
    except Exception as exc:
        return False, "", "", f"{type(exc).__name__}: {exc}"


def _score_topological_sort(row: pd.Series, pred: Any) -> tuple[bool, Any, Any, str]:
    directed_edges = _unweighted_edges(row.get("edge_answer", ""), directed=True)
    pred_order = _positive_ints(_extract_final_text(pred))
    gt_order = _positive_ints(row.get("answer", ""))
    if not pred_order or len(pred_order) != len(set(pred_order)):
        return False, pred_order, gt_order, ""
    if gt_order and set(pred_order) != set(gt_order):
        return False, pred_order, gt_order, ""
    pos = {node: idx for idx, node in enumerate(pred_order)}
    ok = all(u in pos and v in pos and pos[u] < pos[v] for u, v in directed_edges)
    return ok, pred_order, gt_order, ""


def _score_shortest_path(row: pd.Series, pred: Any) -> tuple[bool, Any, Any, str]:
    edge_weights = _undirected_weighted_edges(row.get("edge_answer", ""))
    gt_weight = _extract_weight(row.get("answer", ""))
    gt_path = _extract_sequence_after_marker(row.get("answer", ""), (" is ", ":", "path"))
    pred_weight = _extract_weight(pred)
    pred_path = _extract_sequence_after_marker(pred, (" is ", ":", "path"))
    if len(pred_path) < 2 or gt_weight is None:
        return False, {"path": pred_path, "weight": pred_weight}, {"path": gt_path, "weight": gt_weight}, ""
    total = 0
    for a, b in zip(pred_path, pred_path[1:]):
        key = frozenset((a, b))
        if key not in edge_weights:
            return False, {"path": pred_path, "weight": pred_weight}, {"path": gt_path, "weight": gt_weight}, ""
        total += edge_weights[key]
    ok = total == gt_weight and (pred_weight is None or pred_weight == gt_weight)
    return ok, {"path": pred_path, "weight": pred_weight, "path_weight": total}, {"path": gt_path, "weight": gt_weight}, ""


def _score_hamilton(row: pd.Series, pred: Any) -> tuple[bool, Any, Any, str]:
    gt_yn = _parse_yes_no(row.get("answer", ""))
    pred_yn = _parse_yes_no(pred)
    if gt_yn == "no":
        return pred_yn == "no", pred_yn, gt_yn, ""
    if pred_yn == "no":
        return False, pred_yn, gt_yn, ""

    edges = _unweighted_edges(row.get("edge_answer", ""))
    gt_path = _extract_sequence_after_marker(row.get("answer", ""), ("path is", "can be", ":", "path"))
    pred_path = _extract_sequence_after_marker(pred, ("path is", "can be", ":", "path"))
    expected_nodes = set(gt_path) if gt_path else set().union(*[set(edge) for edge in edges])
    if not pred_path or len(pred_path) != len(set(pred_path)):
        return False, pred_path, gt_path, ""
    if expected_nodes and set(pred_path) != expected_nodes:
        return False, pred_path, gt_path, ""
    ok = all(frozenset((a, b)) in edges for a, b in zip(pred_path, pred_path[1:]))
    return ok, pred_path, gt_path, ""


def _score_bipartite(row: pd.Series, pred: Any) -> tuple[bool, Any, Any, str]:
    pred_text = _extract_final_text(pred)
    expected_text = str(row.get("answer", ""))
    expected_count_match = re.search(r"(\d+)\s+applicants?\s+can", expected_text, flags=re.I)
    expected_count = int(expected_count_match.group(1)) if expected_count_match else None
    pred_count_match = re.search(r"(\d+)\s+applicants?\s+can", pred_text, flags=re.I)
    pred_count = int(pred_count_match.group(1)) if pred_count_match else None
    matches = [
        (int(a), int(b))
        for a, b in re.findall(r"(?:applicant|appl)\s*(\d+)\D{0,20}(?:job)\s*(\d+)", pred_text, flags=re.I)
    ]
    if pred_count is None:
        pred_count = len(matches)
    valid_edges = {
        (int(a), int(b))
        for a, b in re.findall(r"\(\s*Appl(\d+)\s*,\s*Job(\d+)\s*\)", str(row.get("edge_answer", "")))
    }
    job_labels = {b for _, b in valid_edges}
    node_counts = _positive_ints(row.get("node_answer", ""))
    applicant_offset = (
        node_counts[0] - len(job_labels)
        if node_counts and job_labels
        else max((a for a, _ in valid_edges), default=-1) + 1
    )
    unique = len(matches) == len(set(a for a, _ in matches)) == len(set(b for _, b in matches))
    edge_ok = True
    for applicant, job in matches:
        local_job = job - applicant_offset
        if (applicant, job) not in valid_edges and (applicant, local_job) not in valid_edges:
            edge_ok = False
            break
    count_ok = expected_count is not None and pred_count == expected_count and len(matches) == expected_count
    parsed_pred = {"matches": matches, "count": pred_count, "edge_valid": edge_ok}
    return count_ok and unique, parsed_pred, {"count": expected_count}, ""


def _parse_embeddings(text: Any) -> dict[int, tuple[int, ...]]:
    final = _extract_final_text(text)
    out = {}
    for node, values in re.findall(r"node\s*(\d+)\s*:\s*\[([^\]]+)\]", final, flags=re.I):
        out[int(node)] = tuple(_ints(values))
    return out

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
VLMEVAL_ROOT = REPO_ROOT / "external" / "VLMEvalKit"
if str(VLMEVAL_ROOT) not in sys.path:
    sys.path.insert(0, str(VLMEVAL_ROOT))


import vlmeval.dataset.trace_local_vqa as trace_local_vqa  # noqa: E402
from vlmeval.dataset.evochart import EvoChart, score_prediction  # noqa: E402
from vlmeval.dataset.trace_local_vqa import CountQA, GameQALite  # noqa: E402


def test_evochart_aliases_are_registered() -> None:
    assert set(EvoChart.supported_datasets()) == {
        "EvoChart",
        "EvoChart_boxed",
        "EvoChart_Qwen25_ZS",
        "EvoChart_Qwen3_ZS",
        "EvoChart_reasoning",
    }


def test_evochart_qwen3_prompt_suffix() -> None:
    dataset = object.__new__(EvoChart)
    dataset.dataset_name = "EvoChart_Qwen3_ZS"
    dataset.meta_only = True
    row = pd.Series(
        {
            "index": "0",
            "question": "What is the value of December?",
            "image_path": "/tmp/fake.png",
        }
    )

    prompt = dataset.build_prompt(row)

    assert prompt[-1]["value"].endswith("Answer the question using a single word or phrase.")


def test_evochart_boxed_prompt_suffix() -> None:
    row = pd.Series(
        {
            "index": "0",
            "question": "What is the value of December?",
            "image_path": "/tmp/fake.png",
        }
    )

    for dataset_name in ("EvoChart", "EvoChart_boxed"):
        dataset = object.__new__(EvoChart)
        dataset.dataset_name = dataset_name
        dataset.meta_only = True
        prompt = dataset.build_prompt(row)

        assert prompt[-1]["value"].endswith("Put the final answer inside \\boxed{}.")


def test_countqa_boxed_prompt_does_not_change_gameqa_lite() -> None:
    row = pd.Series(
        {
            "index": "0",
            "question": "How many objects are visible?",
            "image_path": "/tmp/fake.png",
        }
    )

    countqa = object.__new__(CountQA)
    countqa.dataset_name = "CountQA"
    countqa.meta_only = True
    countqa_prompt = countqa.build_prompt(row)

    gameqa = object.__new__(GameQALite)
    gameqa.dataset_name = "Game-QA-Lite"
    gameqa.meta_only = True
    gameqa_prompt = gameqa.build_prompt(row)

    assert countqa_prompt[-1]["value"].endswith("Put the final answer inside \\boxed{}.")
    assert "Put only" not in countqa_prompt[-1]["value"]
    assert gameqa_prompt[-1]["value"].endswith("Put only the final answer inside \\boxed{}.")


def test_countqa_cached_answers_preserve_fresh_string_representation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_path = tmp_path / "CountQA.tsv"
    data_path.touch()
    cached = pd.DataFrame(
        {
            "index": ["0_0", "0_1", "0_2"],
            "answer": pd.Series([1, " 2 ", pd.NA], dtype=object),
        }
    )
    monkeypatch.setattr(trace_local_vqa, "LMUDataRoot", lambda: str(tmp_path))
    monkeypatch.setattr(
        trace_local_vqa,
        "_load_cached_with_images",
        lambda path: cached if path == data_path else None,
    )

    dataset = object.__new__(CountQA)
    loaded = dataset.load_data("CountQA")

    assert loaded is not cached
    assert loaded["answer"].tolist() == ["1", "2", ""]
    assert cached["answer"].iloc[:2].tolist() == [1, " 2 "]
    assert pd.isna(cached["answer"].iloc[2])


def test_evochart_scoring_matches_published_strict_and_flex_contract() -> None:
    assert score_prediction("<answer>32</answer>", "32", True) == 1.0
    assert score_prediction("The answer is 33", "32", True) == 0.0
    assert score_prediction(r"\boxed{38%}", "38", True) == 1.0
    assert score_prediction(r"\boxed{1.5 billion}", "1.5", True) == 1.0
    assert score_prediction(r"\boxed{Q4 2022}", "4", True) == 0.0
    assert score_prediction("31", "32", False) == 1.0
    assert score_prediction("28", "32", False) == 0.0
    assert score_prediction("0.38", "38", False) == 0.0
    assert score_prediction("0", "0", False) == 1.0
    assert score_prediction("0.04", "0", False) == 0.0
    assert score_prediction("Rep/Lean Rep", "Rep/Lean Rep", False) == 1.0
    assert score_prediction("rep/lean rep", "Rep/Lean Rep", False) == 1.0


def test_evochart_evaluate_outputs_overall_and_breakdowns(tmp_path: Path) -> None:
    pred_file = tmp_path / "EvoChart_Qwen3_ZS_predictions.xlsx"
    pd.DataFrame(
        [
            {
                "index": "0",
                "prediction": "<answer>32</answer>",
                "answer": "32",
                "is_clear": True,
                "chart_type": "linechart",
                "attribute": "Direct Retrieval",
            },
            {
                "index": "1",
                "prediction": "31",
                "answer": "32",
                "is_clear": False,
                "chart_type": "linechart",
                "attribute": "Direct Retrieval",
            },
        ]
    ).to_excel(pred_file, index=False)

    dataset = object.__new__(EvoChart)
    result = dataset.evaluate(str(pred_file))

    overall = result[result["split"] == "Overall"].iloc[0]
    assert overall["tot"] == 2
    assert overall["acc"] == 100.0
    assert (tmp_path / "EvoChart_Qwen3_ZS_predictions_results.xlsx").exists()
    assert (tmp_path / "EvoChart_Qwen3_ZS_predictions_acc.csv").exists()

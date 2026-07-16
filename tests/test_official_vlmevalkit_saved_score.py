from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts import run_official_vlmevalkit_saved_score as runner


class _FakeOfficialDataset:
    dataset_name = "OfficialAlias"

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def evaluate(self, eval_file: str, **judge_kwargs: object) -> pd.DataFrame:
        self.calls.append((eval_file, judge_kwargs))
        Path(eval_file).with_name("OfficialAlias_predictions_acc.csv").write_text(
            "split,acc\nOverall,62.5\n",
            encoding="utf-8",
        )
        return pd.DataFrame([{"split": "Overall", "acc": 62.5}])

    @classmethod
    def report_primary_metric(cls, metrics: dict[str, object]) -> dict[str, object]:
        return {"Overall Accuracy": metrics["split=Overall|acc"]}


class OfficialVLMEvalSavedScoreTest(unittest.TestCase):
    def test_chartqapro_adapter_extracts_model_wrappers_and_preserves_fallback(self) -> None:
        raw_predictions = [
            "reasoning\nThe Answer Is: **42**.",
            "reasoning\n<answer>North America</answer>",
            (
                "reasoning\nThe answer is 17 for an intermediate result.\n"
                "<answer>The final chart value is \\boxed{42}.</answer>"
            ),
            "reasoning only; no supported final answer",
        ]
        with tempfile.TemporaryDirectory() as temporary:
            prediction = Path(temporary) / "ChartQAPro_CoT_predictions.xlsx"
            pd.DataFrame({"prediction": raw_predictions}).to_excel(prediction, index=False)

            receipt = runner._adapt_chartqapro_prediction(prediction, pd.read_excel)
            adapted = pd.read_excel(prediction)

            self.assertEqual(
                adapted["prediction"].tolist(),
                ["42", "North America", "42", raw_predictions[-1]],
            )
            self.assertEqual(adapted["raw_prediction"].tolist(), raw_predictions)
            self.assertEqual(receipt["changed_rows"], 3)
            self.assertEqual(receipt["unresolved_rows"], 1)

    def test_phyx_option_adapter_normalizes_saved_responses(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            prediction = Path(temporary) / "PhyX_mini_MC_predictions.xlsx"
            pd.DataFrame(
                [
                    {"prediction": "A"},
                    {"prediction": "reasoning\n\\boxed{B}"},
                    {"prediction": "The final answer is C."},
                    {"prediction": "no final option"},
                ]
            ).to_excel(prediction, index=False)

            receipt = runner._adapt_phyx_option_prediction(prediction, pd.read_excel)
            adapted = pd.read_excel(prediction)

            self.assertEqual(
                adapted["prediction"].tolist(),
                ["Answer: A", "Answer: B", "Answer: C", "UNRESOLVED"],
            )
            self.assertEqual(receipt["contract"], runner.PHYX_OPTION_ADAPTER_CONTRACT)
            self.assertEqual(receipt["resolved_rows"], 3)
            self.assertEqual(receipt["unresolved_rows"], 1)

    def test_treebench_adapter_uses_only_one_final_boxed_answer(self) -> None:
        raw_predictions = [
            "<answer>The image contains several labels. Final: \\boxed{C}.</answer>",
            "<answer>B</answer>",
            "<answer>First \\boxed{A}, then prose.</answer>",
            "<answer>\\boxed{A}</answer><answer>\\boxed{B}</answer>",
        ]
        with tempfile.TemporaryDirectory() as temporary:
            prediction = Path(temporary) / "TreeBench_predictions.xlsx"
            pd.DataFrame({"prediction": raw_predictions}).to_excel(prediction, index=False)

            receipt = runner._adapt_treebench_prediction(prediction, pd.read_excel)
            adapted = pd.read_excel(prediction)

            self.assertEqual(
                adapted["prediction"].tolist(),
                ["C", *raw_predictions[1:]],
            )
            self.assertEqual(adapted["raw_prediction"].tolist(), raw_predictions)
            self.assertEqual(receipt["contract"], runner.TREEBENCH_OPTION_ADAPTER_CONTRACT)
            self.assertEqual(receipt["changed_rows"], 1)

    def test_delegates_evaluation_and_emits_provenance(self) -> None:
        dataset = _FakeOfficialDataset()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prediction = root / "saved.xlsx"
            pd.DataFrame(
                [
                    {"index": 1, "prediction": "A", "answer": "A"},
                    {"index": 2, "prediction": "B", "answer": "C"},
                ]
            ).to_excel(prediction, index=False)
            output_dir = root / "score"

            summary = runner.run_saved_score(
                benchmark_key="fake",
                dataset_alias="OfficialAlias",
                prediction_xlsx=prediction,
                output_dir=output_dir,
                model="model/path",
                model_slug="model-slug",
                run_name="official",
                dataset_kwargs={"split": "test"},
                judge_kwargs={"model": "judge", "nproc": 3},
                primary_metric=None,
                primary_value_scale="auto",
                vlmeval_root=runner.DEFAULT_VLMEVAL_ROOT,
                dataset_builder=lambda alias, **kwargs: dataset,
                table_loader=pd.read_excel,
                flatten_metrics=lambda result: {"split=Overall|acc": result.iloc[0]["acc"]},
            )

            staged = output_dir / "OfficialAlias_predictions.xlsx"
            self.assertEqual(dataset.calls, [(str(staged), {"model": "judge", "nproc": 3})])
            self.assertEqual(summary["rows"], 2)
            self.assertEqual(summary["score"], 62.5)
            self.assertEqual(summary["primary_metric"]["key"], "Overall Accuracy")
            self.assertIn(str(output_dir / "OfficialAlias_predictions_acc.csv"), summary["artifacts"]["official_outputs"])
            persisted = json.loads((output_dir / "scores.json").read_text(encoding="utf-8"))
            self.assertEqual(
                persisted["provenance"]["vlmevalkit_commit"],
                "a8b12bf1c3737a33fc1de967c202f9c592b22e86",
            )
            class _FakeWeMath:
                dataset_name = "WeMath_COT"

                @classmethod
                def report_primary_metric(cls, metrics: dict[str, object]) -> dict[str, object]:
                    return {}

            score, metric = runner._primary_score(
                _FakeWeMath(),
                pd.DataFrame([{"Score (Strict)": "46.76%"}]),
                lambda _: {},
                "Score (Strict)",
                "percent",
            )
            self.assertEqual(score, 46.76)
            self.assertEqual(metric["raw_display"], "46.76%")
            self.assertEqual(
                runner._redact({"max_tokens": 256, "api_key": "secret"}),
                {"max_tokens": 256, "api_key": "<redacted>"},
            )


if __name__ == "__main__":
    unittest.main()

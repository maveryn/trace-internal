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
    def test_official_copy_drops_only_queue_identity_columns(self) -> None:
        hash_like_request = "194e088947465066b916808afc8c3ad82814f55231c1dc210af8907dead6e2b1"
        dataset = _FakeOfficialDataset()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prediction = root / "saved.xlsx"
            source = pd.DataFrame(
                [
                    {
                        "index": 7,
                        "prediction": "A",
                        "answer": "A",
                        "source_ordinal": 3,
                        "request_hash": hash_like_request,
                        "source_row_hash": "f" * 64,
                        "custom_provenance": "keep-me",
                    }
                ]
            )
            source.to_excel(prediction, index=False)
            source_sha256 = runner._sha256(prediction)

            def guarded_loader(path: str) -> pd.DataFrame:
                columns = runner._xlsx_header(Path(path))
                remaining = set(columns) & set(runner.QUEUE_ONLY_PREDICTION_COLUMNS)
                if remaining:
                    raise AssertionError(f"queue columns reached table loader: {sorted(remaining)}")
                return pd.read_excel(path)

            summary = runner.run_saved_score(
                benchmark_key="fake",
                dataset_alias="OfficialAlias",
                prediction_xlsx=prediction,
                output_dir=root / "score",
                model="model/path",
                model_slug="model-slug",
                run_name="official",
                dataset_kwargs={},
                judge_kwargs={},
                primary_metric=None,
                primary_value_scale="auto",
                vlmeval_root=runner.DEFAULT_VLMEVAL_ROOT,
                dataset_builder=lambda _alias, **_kwargs: dataset,
                table_loader=guarded_loader,
                flatten_metrics=lambda result: {"split=Overall|acc": result.iloc[0]["acc"]},
            )

            evaluated = pd.read_excel(dataset.calls[0][0])
            self.assertEqual(
                evaluated.columns.tolist(),
                ["index", "prediction", "answer", "source_ordinal", "custom_provenance"],
            )
            self.assertEqual(evaluated.loc[0, "prediction"], "A")
            self.assertEqual(evaluated.loc[0, "answer"], "A")
            self.assertEqual(evaluated.loc[0, "custom_provenance"], "keep-me")
            self.assertEqual(runner._xlsx_header(prediction), source.columns.tolist())
            from openpyxl import load_workbook

            workbook = load_workbook(prediction, read_only=True, data_only=False)
            try:
                self.assertEqual(workbook.active["E2"].value, hash_like_request)
            finally:
                workbook.close()
            self.assertEqual(runner._sha256(prediction), source_sha256)
            self.assertEqual(
                summary["provenance"]["evaluator_input_filter"]["removed_columns"],
                ["request_hash", "source_row_hash"],
            )
            self.assertEqual(summary["provenance"]["source_prediction_sha256"], source_sha256)

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

    def test_screenspot_concat_adapts_json_and_uses_sample_weighted_overall(self) -> None:
        class _FakeScreenSpotConcat:
            dataset_name = "ScreenSpot_Pro"

            def __init__(self) -> None:
                self.data = pd.DataFrame(
                    {
                        "index": [0, 1, 2, 3],
                        "SUB_DATASET": ["Development", "Office", "Office", "Office"],
                        "image_path": ["dev.png", "office-1.png", "office-2.png", "office-3.png"],
                    }
                )

            def evaluate(self, eval_file: str, **_kwargs: object) -> dict[str, float | int]:
                adapted = pd.read_excel(eval_file)
                self.predictions = adapted["prediction"].tolist()
                self.image_paths = adapted["image_path"].tolist()
                return {
                    "Development:Overall_Accuracy": 50.0,
                    "Development:text:cnt": 1,
                    "Office:Overall_Accuracy": 100.0,
                    "Office:text:cnt": 3,
                }

        dataset = _FakeScreenSpotConcat()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prediction = root / "saved.xlsx"
            pd.DataFrame(
                {
                    "index": [0, 1, 2, 3],
                    "SUB_DATASET": ["Development", "Office", "Office", "Office"],
                    "prediction": ['```json\n[{"point_2d": [12, 34]}]\n```'] * 4,
                }
            ).to_excel(prediction, index=False)

            summary = runner.run_saved_score(
                benchmark_key="screenspotpro",
                dataset_alias="ScreenSpot_Pro",
                prediction_xlsx=prediction,
                output_dir=root / "score",
                model="model/path",
                model_slug="model-slug",
                run_name="official",
                dataset_kwargs={},
                judge_kwargs={},
                primary_metric=None,
                primary_value_scale="auto",
                vlmeval_root=runner.DEFAULT_VLMEVAL_ROOT,
                dataset_builder=lambda _alias, **_kwargs: dataset,
                table_loader=pd.read_excel,
                flatten_metrics=lambda _result: {},
            )

            self.assertEqual(dataset.predictions, ["pyautogui.click(x=12, y=34)"] * 4)
            self.assertEqual(
                dataset.image_paths,
                ["dev.png", "office-1.png", "office-2.png", "office-3.png"],
            )
            self.assertEqual(summary["score"], 87.5)
            self.assertEqual(summary["primary_metric"]["pooled_rows"], 4)
            self.assertEqual(
                summary["provenance"]["prediction_adapter"]["resolved_rows"],
                4,
            )
            self.assertEqual(
                summary["provenance"]["prediction_adapter"]["media_restore"],
                {
                    "contract": runner.SCREENSPOT_MEDIA_RESTORE_CONTRACT,
                    "source": "dataset.data",
                    "matched_by": "unique_string_index",
                    "restored_rows": 4,
                    "validated_sub_dataset": True,
                },
            )
            self.assertIn("Development:Overall_Accuracy", summary["scores"])

    def test_screenspot_concat_rejects_mismatched_compact_subset(self) -> None:
        class _FakeScreenSpotConcat:
            data = pd.DataFrame(
                {
                    "index": [0],
                    "SUB_DATASET": ["Development"],
                    "image_path": ["dev.png"],
                }
            )

        with tempfile.TemporaryDirectory() as temporary:
            prediction = Path(temporary) / "ScreenSpot_Pro_predictions.xlsx"
            pd.DataFrame(
                {
                    "index": [0],
                    "SUB_DATASET": ["Office"],
                    "prediction": ['[{"point_2d": [12, 34]}]'],
                }
            ).to_excel(prediction, index=False)

            with self.assertRaisesRegex(ValueError, "SUB_DATASET disagrees"):
                runner._adapt_screenspot_prediction(
                    prediction,
                    pd.read_excel,
                    _FakeScreenSpotConcat(),
                )


if __name__ == "__main__":
    unittest.main()

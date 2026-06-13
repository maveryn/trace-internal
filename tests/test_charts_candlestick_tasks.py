"""Contract smoke tests for candlestick/OHLC chart tasks."""

from __future__ import annotations

from trace.tasks import TASK_REGISTRY


CANDLESTICK_TASKS = {
    "task_charts__candlestick__range_extremum_label": {
        "largest_body_range_label",
        "largest_wick_range_label",
        "smallest_body_range_label",
        "smallest_wick_range_label",
    },
    "task_charts__candlestick__counterfactual_close_value": {
        "close_after_body_decrease_value",
        "close_after_body_increase_value",
    },
}
WICK_RANGE_QUERY_IDS = {"largest_wick_range_label", "smallest_wick_range_label"}
BODY_RANGE_QUERY_IDS = {"largest_body_range_label", "smallest_body_range_label"}
COUNTERFACTUAL_QUERY_IDS = {"close_after_body_decrease_value", "close_after_body_increase_value"}


def _candles_by_id(output):
    return {
        str(candle["candle_id"]): dict(candle)
        for candle in output.trace_payload["execution_trace"]["candles"]
    }


def _bbox_center(box):
    return [
        round((float(box[0]) + float(box[2])) / 2.0, 3),
        round((float(box[1]) + float(box[3])) / 2.0, 3),
    ]


def test_candlestick_tasks_registered() -> None:
    assert set(CANDLESTICK_TASKS).issubset(set(TASK_REGISTRY))


def test_candlestick_tasks_generate_default_query_outputs() -> None:
    for seed_index, (task_id, allowed_query_ids) in enumerate(sorted(CANDLESTICK_TASKS.items())):
        task = TASK_REGISTRY[task_id]()
        output = task.generate(
            700_000 + seed_index,
            params={},
            max_attempts=100,
        )
        assert output.scene_id == "candlestick"
        assert output.query_id in allowed_query_ids
        assert output.trace_payload["query_spec"]["params"]["query_id"] == output.query_id
        assert len(output.annotation_gt.value) == 1
        if output.query_id in BODY_RANGE_QUERY_IDS | WICK_RANGE_QUERY_IDS:
            assert output.annotation_gt.type == "point_set"
            assert output.trace_payload["projected_annotation"]["type"] == "point_set"
            assert output.trace_payload["projected_annotation"]["point_set"] == output.annotation_gt.value
            assert output.trace_payload["projected_annotation"]["pixel_point_set"] == output.annotation_gt.value
        else:
            assert output.annotation_gt.type == "bbox_set"
            assert output.trace_payload["projected_annotation"]["type"] == "bbox_set"
            assert output.trace_payload["projected_annotation"]["bbox_set"] == output.annotation_gt.value
        assert output.trace_payload["render_map"]["body_bboxes_px"]


def test_candlestick_tasks_generate_each_query_branch_and_answer_contract() -> None:
    seed_index = 0
    for task_id, allowed_query_ids in sorted(CANDLESTICK_TASKS.items()):
        task = TASK_REGISTRY[task_id]()
        for query_id in sorted(allowed_query_ids):
            output = task.generate(
                701_000 + seed_index,
                params={"query_id": query_id},
                max_attempts=100,
            )
            assert output.scene_id == "candlestick"
            assert output.query_id == query_id
            execution = output.trace_payload["execution_trace"]
            candles = _candles_by_id(output)
            assert len(output.annotation_gt.value) == 1

            if query_id in WICK_RANGE_QUERY_IDS:
                extremum = str(execution["extremum"])
                ranked = sorted(candles.values(), key=lambda candle: int(candle["wick_range"]))
                target = ranked[-1] if extremum == "largest" else ranked[0]
                assert output.answer_gt.type == "string"
                assert output.answer_gt.value == str(target["label"])
                assert execution["annotation_roles"] == ["answer_wick"]
                assert output.annotation_gt.type == "point_set"
                assert output.annotation_gt.value == [
                    _bbox_center(output.trace_payload["render_map"]["wick_bboxes_px"][str(target["candle_id"])])
                ]
                assert output.trace_payload["projected_annotation"]["type"] == "point_set"
                assert output.trace_payload["projected_annotation"]["point_set"] == output.annotation_gt.value
            elif query_id in BODY_RANGE_QUERY_IDS:
                extremum = str(execution["extremum"])
                ranked = sorted(candles.values(), key=lambda candle: int(candle["body_size"]))
                target = ranked[-1] if extremum == "largest" else ranked[0]
                assert output.answer_gt.type == "string"
                assert output.answer_gt.value == str(target["label"])
                assert execution["annotation_roles"] == ["answer_body"]
                assert output.annotation_gt.type == "point_set"
                assert output.annotation_gt.value == [
                    _bbox_center(output.trace_payload["render_map"]["body_bboxes_px"][str(target["candle_id"])])
                ]
                assert output.trace_payload["projected_annotation"]["type"] == "point_set"
                assert output.trace_payload["projected_annotation"]["point_set"] == output.annotation_gt.value
            elif query_id in COUNTERFACTUAL_QUERY_IDS:
                target = candles[str(execution["target_candle_id"])]
                new_body = int(execution["new_body_size"])
                if str(target["direction"]) == "up":
                    expected = int(target["open"]) + new_body
                else:
                    expected = int(target["open"]) - new_body
                assert output.answer_gt.type == "integer"
                assert output.answer_gt.value == expected
                assert execution["annotation_roles"] == ["target_body"]
                assert output.annotation_gt.type == "bbox_set"
                assert output.annotation_gt.value == [
                    output.trace_payload["render_map"]["body_bboxes_px"][str(target["candle_id"])]
                ]
            else:
                raise AssertionError(f"unsupported candlestick query id: {query_id}")

            seed_index += 1

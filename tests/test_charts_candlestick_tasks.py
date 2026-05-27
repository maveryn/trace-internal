"""Contract smoke tests for candlestick/OHLC chart tasks."""

from __future__ import annotations

from trace.tasks import TASK_REGISTRY


CANDLESTICK_TASKS = {
    "task_charts__candlestick__range_extremum_label": {
        "body_range_extremum_label",
        "wick_range_extremum_label",
    },
    "task_charts__candlestick__counterfactual_close_value": {"close_after_body_change_value"},
}


def _candles_by_id(output):
    return {
        str(candle["candle_id"]): dict(candle)
        for candle in output.trace_payload["execution_trace"]["candles"]
    }


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
        assert output.query_variant == "default"
        assert output.scene_id == "candlestick"
        assert output.query_id in allowed_query_ids
        assert output.trace_payload["query_spec"]["params"]["query_id"] == output.query_id
        assert output.evidence_gt.type == "bbox_set"
        assert output.evidence_gt.value
        assert output.trace_payload["render_map"]["body_bboxes_px"]


def test_candlestick_tasks_generate_each_query_branch_and_answer_contract() -> None:
    seed_index = 0
    for task_id, allowed_query_ids in sorted(CANDLESTICK_TASKS.items()):
        task = TASK_REGISTRY[task_id]()
        for query_id in sorted(allowed_query_ids):
            output = task.generate(
                701_000 + seed_index,
                params={"query_variant": query_id},
                max_attempts=100,
            )
            assert output.query_variant == "default"
            assert output.scene_id == "candlestick"
            assert output.query_id == query_id
            execution = output.trace_payload["execution_trace"]
            candles = _candles_by_id(output)

            if query_id == "wick_range_extremum_label":
                extremum = str(execution["extremum"])
                ranked = sorted(candles.values(), key=lambda candle: int(candle["wick_range"]))
                target = ranked[-1] if extremum == "largest" else ranked[0]
                assert output.answer_gt.type == "string"
                assert output.answer_gt.value == str(target["label"])
            elif query_id == "body_range_extremum_label":
                extremum = str(execution["extremum"])
                ranked = sorted(candles.values(), key=lambda candle: int(candle["body_size"]))
                target = ranked[-1] if extremum == "largest" else ranked[0]
                assert output.answer_gt.type == "string"
                assert output.answer_gt.value == str(target["label"])
            elif query_id == "close_after_body_change_value":
                target = candles[str(execution["target_candle_id"])]
                new_body = int(execution["new_body_size"])
                if str(target["direction"]) == "up":
                    expected = int(target["open"]) + new_body
                else:
                    expected = int(target["open"]) - new_body
                assert output.answer_gt.type == "integer"
                assert output.answer_gt.value == expected

            seed_index += 1

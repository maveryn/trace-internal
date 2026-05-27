"""Behavior tests for chart composition tasks."""

from __future__ import annotations

import json

import pytest

from trace.core.task_group_config import get_task_group_defaults
from trace.tasks import TASK_REGISTRY
from trace.tasks.charts.composition.small_multiples_aggregate_value import (
    ChartsCompositionSmallMultiplesAggregateValueTask,
    SUPPORTED_QUERY_IDS as SMALL_MULTIPLES_QUERY_IDS,
)
from trace.tasks.charts.composition.share_arithmetic_value import (
    ChartsCompositionShareArithmeticValueTask,
    SUPPORTED_SCENE_VARIANTS as SHARE_ARITHMETIC_SCENE_VARIANTS,
    SUPPORTED_QUERY_IDS as SHARE_ARITHMETIC_QUERY_IDS,
)
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def _panel_by_label(trace: dict) -> dict[str, dict]:
    return {str(panel["panel_label"]): panel for panel in trace["panels"]}


def _expected_answer(trace: dict) -> int:
    panels = list(trace["panels"])
    variant = str(trace["query_id"])
    if variant == "top_k_by_segment_then_sum_other_segment_count":
        ranked = sorted(
            panels,
            key=lambda panel: int(panel["shares_by_segment"][str(trace["rank_segment"])]),
            reverse=True,
        )
        selected = ranked[: int(trace["top_k"])]
        return int(sum(int(panel["counts_by_segment"][str(trace["target_segment"])]) for panel in selected))
    if variant == "conditioned_panel_sum_from_percent":
        selected = [
            panel
            for panel in panels
            if int(panel["shares_by_segment"][str(trace["condition_segment"])]) > int(trace["threshold"])
        ]
        return int(sum(int(panel["counts_by_segment"][str(trace["target_segment"])]) for panel in selected))
    if variant == "average_top_k_minus_average_bottom_k":
        ranked = sorted(
            panels,
            key=lambda panel: int(panel["shares_by_segment"][str(trace["rank_segment"])]),
            reverse=True,
        )
        top = ranked[: int(trace["top_k"])]
        bottom = ranked[-int(trace["bottom_k"]) :]
        top_avg = sum(int(panel["shares_by_segment"][str(trace["target_segment"])]) for panel in top) // len(top)
        bottom_avg = sum(int(panel["shares_by_segment"][str(trace["target_segment"])]) for panel in bottom) // len(bottom)
        return int(top_avg - bottom_avg)
    if variant == "composition_shift_l1_distance":
        by_label = _panel_by_label(trace)
        start_panel = by_label[str(trace["start_panel"])]
        end_panel = by_label[str(trace["end_panel"])]
        return int(
            sum(
                abs(
                    int(end_panel["shares_by_segment"][str(segment)])
                    - int(start_panel["shares_by_segment"][str(segment)])
                )
                for segment in trace["segment_labels"]
            )
        )
    raise AssertionError(f"unsupported variant: {variant}")


def _assert_normalized_complexity(out: object) -> None:
    complexity = out.complexity.to_dict()
    assert 0.0 <= float(complexity["complexity_score"]) <= 1.0
    assert set(complexity["complexity_components"].keys()) == {
        "reasoning_load",
        "scene_variant_load",
        "visual_scan",
    }
    assert all(0.0 <= float(value) <= 1.0 for value in complexity["complexity_components"].values())


def test_chart_composition_task_overrides_do_not_inherit_sibling_variants() -> None:
    cfg = get_task_group_defaults("charts", "composition")
    small_generation, _, _ = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="charts_composition_small_multiples_aggregate_value_base",
    )
    share_generation, _, _ = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="charts_composition_share_arithmetic_value_base",
    )

    assert sorted(small_generation["query_id_weights"].keys()) == sorted(SMALL_MULTIPLES_QUERY_IDS)
    assert sorted(small_generation["scene_variant_weights"].keys()) == [
        "small_multiple_donut",
        "small_multiple_pie",
    ]
    assert sorted(share_generation["query_id_weights"].keys()) == sorted(SHARE_ARITHMETIC_QUERY_IDS)
    assert sorted(share_generation["scene_variant_weights"].keys()) == sorted(SHARE_ARITHMETIC_SCENE_VARIANTS)


@pytest.mark.parametrize(
    ("query_id", "scene_variant"),
    [
        ("top_k_by_segment_then_sum_other_segment_count", "small_multiple_pie"),
        ("conditioned_panel_sum_from_percent", "small_multiple_donut"),
        ("average_top_k_minus_average_bottom_k", "small_multiple_pie"),
        ("composition_shift_l1_distance", "small_multiple_donut"),
    ],
)
def test_chart_composition_variants_match_contract(query_id: str, scene_variant: str) -> None:
    task = ChartsCompositionSmallMultiplesAggregateValueTask()
    out = task.generate(
        30000 + SMALL_MULTIPLES_QUERY_IDS.index(query_id),
        params={"query_id": query_id, "scene_variant": scene_variant},
        max_attempts=10,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]

    assert out.query_id == query_id
    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "point_set"
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert str(execution["scene_variant"]) == str(scene_variant)
    assert str(render["scene_variant"]) == str(scene_variant)
    assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
    assert len(execution["panels"]) == int(execution["panel_count"])
    assert len(execution["segment_labels"]) == int(execution["segment_count"])
    assert all(sum(int(value) for value in panel["shares_by_segment"].values()) == 100 for panel in execution["panels"])
    assert all(int(panel["total"]) % 100 == 0 for panel in execution["panels"])
    assert int(out.answer_gt.value) == int(execution["answer_value"])
    assert int(out.answer_gt.value) == _expected_answer(execution)
    assert "integer_list" not in trace["projected_evidence"]
    assert trace["projected_evidence"]["point_set"] == list(out.evidence_gt.value)
    assert trace["projected_evidence"]["pixel_point_set"] == list(out.evidence_gt.value)
    assert len(out.evidence_gt.value) == len(execution["evidence_keys"])
    assert len(trace["projected_evidence"]["bbox_set"]) == len(execution["evidence_keys"])
    for x_coord, y_coord in out.evidence_gt.value:
        assert 0 <= float(x_coord) <= int(render["canvas_width"])
        assert 0 <= float(y_coord) <= int(render["canvas_height"])
    assert all(
        8.0 <= float(bbox[2]) - float(bbox[0]) <= 42.0 and 8.0 <= float(bbox[3]) - float(bbox[1]) <= 28.0
        for bbox in trace["projected_evidence"]["bbox_set"]
    )
    assert len(trace["scene_ir"]["entities"]) == int(execution["panel_count"]) * int(execution["segment_count"])
    assert str(trace["query_spec"]["query_id"]) == str(query_id)
    _assert_normalized_complexity(out)


def test_chart_composition_balances_variants_and_scenes() -> None:
    task = ChartsCompositionSmallMultiplesAggregateValueTask()
    variants = []
    scenes = []
    for index in range(32):
        out = task.generate(30100 + index, params={}, max_attempts=10)
        variants.append(str(out.query_id))
        scenes.append(str(out.trace_payload["execution_trace"]["scene_variant"]))
    assert {variant: variants.count(variant) for variant in set(variants)} == {
        "top_k_by_segment_then_sum_other_segment_count": 8,
        "conditioned_panel_sum_from_percent": 8,
        "average_top_k_minus_average_bottom_k": 8,
        "composition_shift_l1_distance": 8,
    }
    assert {scene: scenes.count(scene) for scene in set(scenes)} == {
        "small_multiple_pie": 16,
        "small_multiple_donut": 16,
    }


def test_chart_composition_decouples_count_axes_from_variant_axes() -> None:
    task = ChartsCompositionSmallMultiplesAggregateValueTask()
    by_variant: dict[str, set[int]] = {}
    by_scene: dict[str, set[int]] = {}
    for index in range(96):
        out = task.generate(30500 + index, params={}, max_attempts=10)
        trace = out.trace_payload["execution_trace"]
        by_variant.setdefault(str(out.query_id), set()).add(int(trace["panel_count"]))
        by_scene.setdefault(str(trace["scene_variant"]), set()).add(int(trace["segment_count"]))

    assert set(by_variant) == set(SMALL_MULTIPLES_QUERY_IDS)
    assert all(values == {4, 5, 6, 7, 8, 9} for values in by_variant.values())
    assert by_scene == {
        "small_multiple_pie": {5, 6, 7},
        "small_multiple_donut": {5, 6, 7},
    }


def test_chart_composition_prompt_examples_match_selected_variant() -> None:
    task = ChartsCompositionSmallMultiplesAggregateValueTask()
    expected = {
        "top_k_by_segment_then_sum_other_segment_count": {"evidence": [[260, 280], [520, 300]], "answer": 780},
        "conditioned_panel_sum_from_percent": {
            "evidence": [[240, 290], [480, 310], [720, 330]],
            "answer": 720,
        },
        "average_top_k_minus_average_bottom_k": {
            "evidence": [[240, 260], [480, 280], [720, 360], [960, 380]],
            "answer": 20,
        },
        "composition_shift_l1_distance": {
            "evidence": [
                [240, 250],
                [240, 310],
                [240, 370],
                [240, 430],
                [620, 250],
                [620, 310],
                [620, 370],
                [620, 430],
            ],
            "answer": 28,
        },
    }
    for index, query_id in enumerate(expected, start=30200):
        out = task.generate(index, params={"query_id": query_id}, max_attempts=10)
        answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected[query_id]
        assert answer_only == {"answer": expected[query_id]["answer"]}


def test_chart_composition_rejects_non_small_multiple_scene_variants() -> None:
    task = ChartsCompositionSmallMultiplesAggregateValueTask()
    for scene_variant in ("bar", "pie", "donut", "stacked_bar", "line"):
        with pytest.raises(ValueError):
            task.generate(
                30300,
                params={
                    "query_id": "top_k_by_segment_then_sum_other_segment_count",
                    "scene_variant": scene_variant,
                },
                max_attempts=10,
            )


def test_chart_composition_task_is_registered_and_deterministic() -> None:
    assert "task_charts__small_multiple__aggregate_value" in TASK_REGISTRY
    assert "task_charts__small_multiple__difference_value" in TASK_REGISTRY
    task = ChartsCompositionSmallMultiplesAggregateValueTask()
    params = {
        "query_id": "composition_shift_l1_distance",
        "scene_variant": "small_multiple_donut",
    }
    out_a = task.generate(30400, params=params, max_attempts=10)
    out_b = task.generate(30400, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def _expected_share_arithmetic_answer(trace: dict) -> int:
    values_by_label = {str(label): int(value) for label, value in trace["category_values"].items()}
    variant = str(trace["query_id"])
    if variant == "ranked_position_set_sum":
        return int(sum(values_by_label[str(label)] for label in trace["category_list"]))
    if variant == "conditional_share_sum":
        lower = int(trace["lower_reference_value"])
        upper = int(trace["upper_reference_value"])
        selected = [
            str(category["label"])
            for category in trace["categories"]
            if str(category["label"]) not in {str(trace["lower_reference_category"]), str(trace["upper_reference_category"])}
            and lower < int(category["value"]) < upper
        ]
        assert selected == [str(label) for label in trace["category_list"]]
        return int(sum(values_by_label[str(label)] for label in selected))
    if variant == "contiguous_chart_order_sum":
        labels = [str(label) for label in trace["chart_order_labels"]]
        start = labels.index(str(trace["start_category"]))
        step = 1 if str(trace["chart_order_direction"]) == "clockwise" else -1
        selected_indices = [(int(start) + (int(step) * offset)) % len(labels) for offset in range(int(trace["span_count"]))]
        end = selected_indices[-1]
        assert start == int(trace["start_index"])
        assert end == int(trace["end_index"])
        assert selected_indices == [int(index) for index in trace["selected_indices"]]
        return int(sum(values_by_label[str(labels[index])] for index in selected_indices))
    if variant in {
        "rank_conditioned_transfer_gap",
        "threshold_conditioned_transfer_gap",
        "chart_order_adjacent_transfer_gap",
    }:
        if variant == "rank_conditioned_transfer_gap":
            ranked_largest = [
                str(category["label"])
                for category in sorted(trace["categories"], key=lambda category: (-int(category["value"]), str(category["label"])))
            ]
            ranked_smallest = [
                str(category["label"])
                for category in sorted(trace["categories"], key=lambda category: (int(category["value"]), str(category["label"])))
            ]
            assert ranked_largest[int(trace["source_rank"]) - 1] == str(trace["source_category"])
            assert ranked_smallest[int(trace["target_rank"]) - 1] == str(trace["target_category"])
        elif variant == "threshold_conditioned_transfer_gap":
            source_candidates = [
                category
                for category in trace["categories"]
                if int(category["value"]) < int(trace["source_threshold"])
            ]
            target_candidates = [
                category
                for category in trace["categories"]
                if int(category["value"]) > int(trace["target_threshold"])
            ]
            source = max(source_candidates, key=lambda category: (int(category["value"]), str(category["label"])))
            target = min(target_candidates, key=lambda category: (int(category["value"]), str(category["label"])))
            assert str(source["label"]) == str(trace["source_category"])
            assert str(target["label"]) == str(trace["target_category"])
        elif variant == "chart_order_adjacent_transfer_gap":
            labels = [str(label) for label in trace["chart_order_labels"]]
            source_step = 1 if str(trace["source_order_direction"]) == "clockwise" else -1
            source_index = labels.index(str(trace["source_category"]))
            assert int(trace["source_index"]) == int(source_index)
            assert int(trace["target_index"]) == (int(source_index) + int(source_step)) % len(labels)
            assert labels[int(trace["target_index"])] == str(trace["target_category"])
        source_new = int(values_by_label[str(trace["source_category"])]) - int(trace["transfer_delta"])
        target_new = int(values_by_label[str(trace["target_category"])]) + int(trace["transfer_delta"])
        assert int(trace["source_new_value"]) == int(source_new)
        assert int(trace["target_new_value"]) == int(target_new)
        return int(abs(int(target_new) - int(source_new)))
    if variant == "selected_share_to_count":
        ranked_largest = [
            str(category["label"])
            for category in sorted(trace["categories"], key=lambda category: (-int(category["value"]), str(category["label"])))
        ]
        assert [ranked_largest[int(position) - 1] for position in trace["rank_positions"]] == [
            str(label) for label in trace["category_list"]
        ]
        selected_share = int(sum(values_by_label[str(label)] for label in trace["category_list"]))
        assert int(trace["selected_share_value"]) == int(selected_share)
        return int(int(trace["total_count"]) * int(selected_share) // 100)
    if variant == "excluded_share_to_remaining_count":
        lower = int(trace["lower_reference_value"])
        upper = int(trace["upper_reference_value"])
        excluded = [
            str(category["label"])
            for category in trace["categories"]
            if str(category["label"]) not in {str(trace["lower_reference_category"]), str(trace["upper_reference_category"])}
            and lower < int(category["value"]) < upper
        ]
        assert excluded == [str(label) for label in trace["category_list"]]
        selected_share = int(sum(values_by_label[str(label)] for label in excluded))
        remaining_share = int(100 - int(selected_share))
        assert int(trace["selected_share_value"]) == int(selected_share)
        assert int(trace["remaining_share_value"]) == int(remaining_share)
        return int(int(trace["total_count"]) * int(remaining_share) // 100)
    if variant == "chart_order_share_to_count":
        labels = [str(label) for label in trace["chart_order_labels"]]
        start = labels.index(str(trace["start_category"]))
        step = 1 if str(trace["chart_order_direction"]) == "clockwise" else -1
        selected_indices = [(int(start) + (int(step) * offset)) % len(labels) for offset in range(int(trace["span_count"]))]
        assert selected_indices == [int(index) for index in trace["selected_indices"]]
        selected_share = int(sum(values_by_label[str(labels[index])] for index in selected_indices))
        assert int(trace["selected_share_value"]) == int(selected_share)
        return int(int(trace["total_count"]) * int(selected_share) // 100)
    if variant == "chart_order_remaining_count":
        labels = [str(label) for label in trace["chart_order_labels"]]
        start = labels.index(str(trace["start_category"]))
        step = 1 if str(trace["chart_order_direction"]) == "clockwise" else -1
        selected_indices = [(int(start) + (int(step) * offset)) % len(labels) for offset in range(int(trace["span_count"]))]
        assert selected_indices == [int(index) for index in trace["selected_indices"]]
        selected_share = int(sum(values_by_label[str(labels[index])] for index in selected_indices))
        remaining_share = int(100 - int(selected_share))
        assert int(trace["selected_share_value"]) == int(selected_share)
        assert int(trace["remaining_share_value"]) == int(remaining_share)
        return int(int(trace["total_count"]) * int(remaining_share) // 100)
    if variant == "sector_share_to_angle":
        labels = [str(label) for label in trace["chart_order_labels"]]
        start = labels.index(str(trace["start_category"]))
        step = 1 if str(trace["chart_order_direction"]) == "clockwise" else -1
        selected_indices = [(int(start) + (int(step) * offset)) % len(labels) for offset in range(int(trace["span_count"]))]
        assert selected_indices == [int(index) for index in trace["selected_indices"]]
        assert [labels[index] for index in selected_indices] == [str(label) for label in trace["category_list"]]
        selected_share = int(sum(values_by_label[str(labels[index])] for index in selected_indices))
        assert int(trace["selected_share_value"]) == int(selected_share)
        assert int(selected_share) % 5 == 0
        return int(int(selected_share) * 360 // 100)
    if variant == "positional_segment_share_sum":
        labels = [str(label) for label in trace["chart_order_labels"]]
        selected_indices = [int(index) for index in trace["selected_indices"]]
        assert [labels[index] for index in selected_indices] == [str(label) for label in trace["category_list"]]
        if str(trace["position_relation"]) == "anchor_offset_sum":
            anchor_index = labels.index(str(trace["anchor_category"]))
            step = 1 if str(trace["chart_order_direction"]) == "clockwise" else -1
            assert selected_indices == [
                (int(anchor_index) + (int(step) * int(offset))) % len(labels)
                for offset in trace["selected_offsets"]
            ]
        elif str(trace["position_relation"]) == "opposite_neighbor_sum":
            anchor_index = labels.index(str(trace["anchor_category"]))
            opposite_index = (int(anchor_index) + (len(labels) // 2)) % len(labels)
            step = 1 if str(trace["chart_order_direction"]) == "clockwise" else -1
            assert selected_indices == [int(opposite_index), (int(opposite_index) + int(step)) % len(labels)]
        else:
            raise AssertionError(f"unsupported positional relation: {trace['position_relation']}")
        return int(sum(values_by_label[str(label)] for label in trace["category_list"]))
    if variant == "ranked_group_share_gap":
        ranked_largest = [
            str(category["label"])
            for category in sorted(trace["categories"], key=lambda category: (-int(category["value"]), str(category["label"])))
        ]
        ranked_smallest = [
            str(category["label"])
            for category in sorted(trace["categories"], key=lambda category: (int(category["value"]), str(category["label"])))
        ]
        group_size = int(trace["group_size"])
        assert ranked_largest[:group_size] == [str(label) for label in trace["largest_group_labels"]]
        assert ranked_smallest[:group_size] == [str(label) for label in trace["smallest_group_labels"]]
        largest_share = int(sum(values_by_label[str(label)] for label in trace["largest_group_labels"]))
        smallest_share = int(sum(values_by_label[str(label)] for label in trace["smallest_group_labels"]))
        assert int(trace["largest_group_share"]) == int(largest_share)
        assert int(trace["smallest_group_share"]) == int(smallest_share)
        return int(largest_share - smallest_share)
    if variant == "known_part_to_group_count":
        known_category = str(trace["known_count_category"])
        inferred_total = int(trace["known_count_value"]) * 100 // int(values_by_label[known_category])
        assert int(trace["inferred_total_count"]) == int(inferred_total)
        ranked_largest = [
            str(category["label"])
            for category in sorted(trace["categories"], key=lambda category: (-int(category["value"]), str(category["label"])))
        ]
        assert [ranked_largest[int(position) - 1] for position in trace["rank_positions"]] == [
            str(label) for label in trace["category_list"]
        ]
        selected_share = int(sum(values_by_label[str(label)] for label in trace["category_list"]))
        assert int(trace["selected_share_value"]) == int(selected_share)
        return int(inferred_total * selected_share // 100)
    if variant == "cumulative_share_threshold_count":
        ranked_largest = [
            str(category["label"])
            for category in sorted(trace["categories"], key=lambda category: (-int(category["value"]), str(category["label"])))
        ]
        answer_count = int(trace["cumulative_answer_count"])
        assert ranked_largest[:answer_count] == [str(label) for label in trace["category_list"]]
        selected_share = int(sum(values_by_label[str(label)] for label in trace["category_list"]))
        previous_share = selected_share - int(values_by_label[str(trace["category_list"][-1])])
        assert int(trace["selected_share_value"]) == int(selected_share)
        assert int(trace["previous_cumulative_share"]) == int(previous_share)
        assert int(previous_share) < int(trace["threshold_value"]) <= int(selected_share)
        return int(answer_count)
    raise AssertionError(f"unsupported share-arithmetic variant: {variant}")


@pytest.mark.parametrize("query_id", SHARE_ARITHMETIC_QUERY_IDS)
@pytest.mark.parametrize("scene_variant", SHARE_ARITHMETIC_SCENE_VARIANTS)
def test_chart_composition_share_arithmetic_variants_match_contract(query_id: str, scene_variant: str) -> None:
    task = ChartsCompositionShareArithmeticValueTask()
    circular_only_variants = {
        "contiguous_chart_order_sum",
        "positional_segment_share_sum",
        "chart_order_share_to_count",
        "chart_order_remaining_count",
        "sector_share_to_angle",
        "chart_order_adjacent_transfer_gap",
    }
    transfer_variants = {
        "chart_order_adjacent_transfer_gap",
    }
    part_whole_variants = {
        "chart_order_share_to_count",
        "chart_order_remaining_count",
        "sector_share_to_angle",
    }
    if query_id in circular_only_variants and scene_variant not in {"pie", "donut"}:
        with pytest.raises(ValueError):
            task.generate(
                41000 + (SHARE_ARITHMETIC_QUERY_IDS.index(query_id) * 10) + SHARE_ARITHMETIC_SCENE_VARIANTS.index(scene_variant),
                params={"query_id": query_id, "scene_variant": scene_variant},
                max_attempts=10,
            )
        return
    out = task.generate(
        41000 + (SHARE_ARITHMETIC_QUERY_IDS.index(query_id) * 10) + SHARE_ARITHMETIC_SCENE_VARIANTS.index(scene_variant),
        params={"query_id": query_id, "scene_variant": scene_variant},
        max_attempts=10,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]

    assert out.query_id == query_id
    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "bbox_set"
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert str(execution["scene_variant"]) == str(scene_variant)
    assert str(render["scene_variant"]) == str(scene_variant)
    assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
    assert int(execution["category_count"]) == len(execution["categories"])
    if query_id == "contiguous_chart_order_sum":
        assert 4 <= int(execution["category_count"]) <= 8
        assert int(execution["span_count"]) < int(execution["category_count"])
    elif query_id in transfer_variants:
        assert 4 <= int(execution["category_count"]) <= 8
    elif query_id in part_whole_variants:
        assert 4 <= int(execution["category_count"]) <= 8
        assert int(execution["span_count"]) < int(execution["category_count"])
        if query_id == "sector_share_to_angle":
            assert int(execution["sector_angle_degrees"]) != 360
    elif query_id == "positional_segment_share_sum":
        assert int(execution["category_count"]) in {4, 6, 8}
    else:
        assert 16 <= int(execution["category_count"]) <= 24
    assert sum(int(category["value"]) for category in execution["categories"]) == 100
    assert execution["table_order_labels"] == sorted(execution["chart_order_labels"])
    assert int(out.answer_gt.value) == int(execution["answer_value"])
    assert int(out.answer_gt.value) == _expected_share_arithmetic_answer(execution)
    assert trace["projected_evidence"]["bbox_set"] == list(out.evidence_gt.value)
    assert len(out.evidence_gt.value) == len(execution["evidence_labels"])
    assert len(execution["evidence_values"]) == len(execution["evidence_labels"])
    for label, bbox in zip(execution["evidence_labels"], out.evidence_gt.value):
        assert 0 <= float(bbox[0]) < float(bbox[2]) <= int(render["canvas_width"])
        assert 0 <= float(bbox[1]) < float(bbox[3]) <= int(render["canvas_height"])
        is_special_evidence = str(label).startswith("__")
        min_width = 120.0 if is_special_evidence else 300.0
        assert float(bbox[2]) - float(bbox[0]) >= float(min_width)
        min_row_height = 12.0 if is_special_evidence else 18.0
        max_row_height = (
            64.0
            if query_id
            in {
                "contiguous_chart_order_sum",
                "chart_order_adjacent_transfer_gap",
                "chart_order_share_to_count",
                "chart_order_remaining_count",
                "sector_share_to_angle",
                "positional_segment_share_sum",
            }
            else 55.0
        )
        assert float(min_row_height) <= float(bbox[3]) - float(bbox[1]) <= float(max_row_height)
    assert len(trace["scene_ir"]["entities"]) >= int(execution["category_count"]) * 2
    assert str(trace["query_spec"]["query_id"]) == str(query_id)
    _assert_normalized_complexity(out)


def test_chart_composition_share_arithmetic_balances_variants_and_scenes() -> None:
    task = ChartsCompositionShareArithmeticValueTask()
    variants = []
    scenes = []
    for index in range(72):
        out = task.generate(41100 + index, params={}, max_attempts=10)
        variants.append(str(out.query_id))
        scenes.append(str(out.trace_payload["execution_trace"]["scene_variant"]))
    assert {variant: variants.count(variant) for variant in set(variants)} == {
        "contiguous_chart_order_sum": 12,
        "positional_segment_share_sum": 12,
        "chart_order_share_to_count": 12,
        "chart_order_remaining_count": 12,
        "sector_share_to_angle": 12,
        "chart_order_adjacent_transfer_gap": 12,
    }
    assert set(scenes) == {"pie", "donut"}
    for restricted_variant in set(SHARE_ARITHMETIC_QUERY_IDS):
        restricted_scenes = [
            scene
            for index, scene in enumerate(scenes)
            if str(variants[index]) == str(restricted_variant)
        ]
        assert set(restricted_scenes) == {"pie", "donut"}


def test_chart_composition_share_arithmetic_decouples_category_count_from_variant_axes() -> None:
    task = ChartsCompositionShareArithmeticValueTask()
    by_variant: dict[str, set[int]] = {}
    by_scene: dict[str, set[int]] = {}
    for index in range(280):
        out = task.generate(41200 + index, params={}, max_attempts=10)
        trace = out.trace_payload["execution_trace"]
        by_variant.setdefault(str(out.query_id), set()).add(int(trace["category_count"]))
        by_scene.setdefault(str(trace["scene_variant"]), set()).add(int(trace["category_count"]))

    assert set(by_variant) == set(SHARE_ARITHMETIC_QUERY_IDS)
    assert by_variant["contiguous_chart_order_sum"] == set(range(4, 9))
    assert by_variant["positional_segment_share_sum"] == {4, 6, 8}
    for variant in {
        "chart_order_share_to_count",
        "chart_order_remaining_count",
        "sector_share_to_angle",
        "chart_order_adjacent_transfer_gap",
    }:
        assert by_variant[variant] == set(range(4, 9))
    assert set(by_scene) == {"pie", "donut"}
    assert by_scene["pie"].intersection(set(range(4, 9)))
    assert by_scene["donut"].intersection(set(range(4, 9)))


def test_chart_composition_share_arithmetic_prompt_examples_match_selected_variant() -> None:
    task = ChartsCompositionShareArithmeticValueTask()
    expected = {
        "contiguous_chart_order_sum": {
            "evidence": [[790, 180, 1220, 210], [790, 270, 1220, 300], [790, 360, 1220, 390], [790, 510, 1220, 540]],
            "answer": 42,
        },
        "positional_segment_share_sum": {
            "evidence": [[790, 150, 1220, 180], [790, 270, 1220, 300], [790, 450, 1220, 480]],
            "answer": 31,
        },
        "chart_order_share_to_count": {
            "evidence": [[42, 72, 210, 96], [790, 180, 1220, 210], [790, 270, 1220, 300], [790, 360, 1220, 390]],
            "answer": 600,
        },
        "chart_order_remaining_count": {
            "evidence": [[42, 72, 210, 96], [790, 180, 1220, 210], [790, 270, 1220, 300], [790, 360, 1220, 390]],
            "answer": 900,
        },
        "sector_share_to_angle": {
            "evidence": [[790, 180, 1220, 210], [790, 270, 1220, 300], [790, 360, 1220, 390]],
            "answer": 108,
        },
        "chart_order_adjacent_transfer_gap": {
            "evidence": [[790, 180, 1220, 210], [790, 390, 1220, 420]],
            "answer": 13,
        },
    }
    for index, query_id in enumerate(expected, start=41300):
        out = task.generate(index, params={"query_id": query_id}, max_attempts=10)
        answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected[query_id]
        assert answer_only == {"answer": expected[query_id]["answer"]}


def test_chart_composition_share_arithmetic_rejects_unsupported_scene_variant() -> None:
    task = ChartsCompositionShareArithmeticValueTask()
    with pytest.raises(ValueError):
        task.generate(
            41400,
            params={
                "query_id": "contiguous_chart_order_sum",
                "scene_variant": "small_multiple_pie",
            },
            max_attempts=10,
        )


def test_chart_composition_share_arithmetic_task_is_registered_and_deterministic() -> None:
    assert "task_charts__part_whole__ordered_segment_value" in TASK_REGISTRY
    assert "task_charts__part_whole__adjacent_transfer_gap_value" in TASK_REGISTRY
    task = ChartsCompositionShareArithmeticValueTask()
    params = {
        "query_id": "chart_order_remaining_count",
        "scene_variant": "donut",
    }
    out_a = task.generate(41500, params=params, max_attempts=10)
    out_b = task.generate(41500, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()

"""Behavior tests for chart flow/Sankey tasks."""

from __future__ import annotations

from collections import Counter

import pytest

from tests.helpers import assert_counter_support_within, extract_prompt_json_example
from trace.core.seed import hash64
from trace.tasks.charts.flow.sankey_path_value import (
    SUPPORTED_SCENE_VARIANTS,
    SUPPORTED_QUERY_IDS,
    ChartsFlowSankeyPathValueTask,
)
from trace.tasks.charts.flow.radial_sankey import (
    DOMINANT_ENDPOINT_QUERY_IDS,
    SUPPORTED_QUERY_IDS as RADIAL_SUPPORTED_QUERY_IDS,
    TRANSFER_TOTAL_QUERY_IDS,
    ChartsFlowRadialSankeyTask,
)


def _assert_bbox_inside_canvas(bbox: list[float], *, width: int, height: int) -> None:
    assert len(bbox) == 4
    x0, y0, x1, y1 = [float(value) for value in bbox]
    assert 0 <= x0 < x1 <= width
    assert 0 <= y0 < y1 <= height


def _bboxes_overlap(a: list[float], b: list[float], *, gap: float = 0.0) -> bool:
    ax0, ay0, ax1, ay1 = [float(value) for value in a]
    bx0, by0, bx1, by1 = [float(value) for value in b]
    return not (
        ax1 + float(gap) <= bx0
        or bx1 + float(gap) <= ax0
        or ay1 + float(gap) <= by0
        or by1 + float(gap) <= ay0
    )


def _expected_answer(execution: dict) -> int:
    variant = str(execution["query_id"])
    details = [dict(path) for path in execution["query_path_details"]]
    if variant == "source_to_target_total_flow":
        return sum(min(int(path["first_value"]), int(path["second_value"])) for path in details)
    if variant == "path_bottleneck_value":
        assert len(details) == 1
        path = details[0]
        return min(int(path["first_value"]), int(path["second_value"]))
    if variant == "path_flow_difference":
        assert len(details) == 1
        path = details[0]
        return abs(int(path["first_value"]) - int(path["second_value"]))
    if variant == "source_outgoing_total_flow":
        return sum(int(path["first_value"]) for path in details)
    if variant == "target_incoming_total_flow":
        return sum(int(path["second_value"]) for path in details)
    raise AssertionError(f"unsupported variant: {variant}")


def _expected_radial_answer(execution: dict) -> int | str:
    variant = str(execution["query_id"])
    details = [dict(link) for link in execution["query_link_details"]]
    if variant in TRANSFER_TOTAL_QUERY_IDS:
        return sum(int(link["value"]) for link in details)
    if variant == "largest_target_for_source":
        ordered = sorted(details, key=lambda link: (-int(link["value"]), str(link["target_label"]), str(link["link_id"])))
        return str(ordered[0]["target_label"])
    if variant == "largest_source_for_target":
        ordered = sorted(details, key=lambda link: (-int(link["value"]), str(link["source_label"]), str(link["link_id"])))
        return str(ordered[0]["source_label"])
    if variant == "second_largest_target_for_source":
        ordered = sorted(details, key=lambda link: (-int(link["value"]), str(link["target_label"]), str(link["link_id"])))
        return str(ordered[1]["target_label"])
    raise AssertionError(f"unsupported radial variant: {variant}")


@pytest.mark.parametrize("query_id", SUPPORTED_QUERY_IDS)
def test_chart_flow_sankey_variants_match_contract(query_id: str) -> None:
    task = ChartsFlowSankeyPathValueTask()
    out = task.generate(
        69100 + SUPPORTED_QUERY_IDS.index(query_id),
        params={"query_id": query_id, "scene_variant": "three_column_sankey"},
        max_attempts=10,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]
    render_map = trace["render_map"]

    assert out.query_id == query_id
    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "bbox_set"
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert str(execution["scene_variant"]) == "three_column_sankey"
    expected_question_format = "sankey_node_side_total_value" if query_id.endswith("_total_flow") and query_id != "source_to_target_total_flow" else "sankey_path_value"
    assert str(execution["question_format"]) == expected_question_format
    assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
    assert 2 <= int(execution["source_count"]) <= 3
    assert 2 <= int(execution["middle_count"]) <= 3
    assert 2 <= int(execution["target_count"]) <= 3
    assert 3 <= int(execution["path_count"]) <= 4
    assert len(execution["paths"]) == int(execution["path_count"])
    for side_counts in execution["path_side_counts"].values():
        assert max(int(value) for value in side_counts.values()) <= int(execution["max_paths_per_node_side"])
    assert len(render_map["segment_label_bboxes_px"]) == 2 * int(execution["path_count"])
    segment_label_bboxes = [
        [float(value) for value in bbox]
        for bbox in render_map["segment_label_bboxes_px"].values()
    ]
    for bbox in segment_label_bboxes:
        _assert_bbox_inside_canvas(
            bbox,
            width=int(render["canvas_width"]),
            height=int(render["canvas_height"]),
        )
    for left_index, left_bbox in enumerate(segment_label_bboxes):
        for right_bbox in segment_label_bboxes[left_index + 1 :]:
            assert not _bboxes_overlap(left_bbox, right_bbox, gap=1.0)

    expected_answer = _expected_answer(execution)
    assert int(out.answer_gt.value) == int(expected_answer)
    assert int(execution["answer_value"]) == int(expected_answer)
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value

    evidence_segment_ids = [str(segment_id) for segment_id in execution["evidence_segment_ids"]]
    expected_bboxes = [render_map["segment_label_bboxes_px"][segment_id] for segment_id in evidence_segment_ids]
    assert out.evidence_gt.value == expected_bboxes
    assert trace["projected_evidence"]["segment_ids"] == evidence_segment_ids
    for bbox in out.evidence_gt.value:
        _assert_bbox_inside_canvas(
            [float(value) for value in bbox],
            width=int(render["canvas_width"]),
            height=int(render["canvas_height"]),
        )

    paths_by_id = {str(key): dict(value) for key, value in execution["paths_by_id"].items()}
    for path_id in execution["query_path_ids"]:
        assert str(path_id) in paths_by_id
    if query_id == "source_to_target_total_flow":
        assert len(execution["query_path_ids"]) >= 2
        labels = {(str(path["source_label"]), str(path["target_label"])) for path in execution["query_path_details"]}
        assert len(labels) == 1
        assert len(evidence_segment_ids) == 2 * len(execution["query_path_ids"])
    elif query_id == "source_outgoing_total_flow":
        assert 2 <= len(execution["query_path_ids"]) <= 3
        labels = {str(path["source_label"]) for path in execution["query_path_details"]}
        assert len(labels) == 1
        assert len(evidence_segment_ids) == len(execution["query_path_ids"])
        assert all(str(segment_id).endswith(":source_middle") for segment_id in evidence_segment_ids)
        assert int(execution["node_side_total"]) == sum(int(path["first_value"]) for path in execution["query_path_details"])
    elif query_id == "target_incoming_total_flow":
        assert 2 <= len(execution["query_path_ids"]) <= 3
        labels = {str(path["target_label"]) for path in execution["query_path_details"]}
        assert len(labels) == 1
        assert len(evidence_segment_ids) == len(execution["query_path_ids"])
        assert all(str(segment_id).endswith(":middle_target") for segment_id in evidence_segment_ids)
        assert int(execution["node_side_total"]) == sum(int(path["second_value"]) for path in execution["query_path_details"])
    else:
        assert len(execution["query_path_ids"]) == 1
        assert len(evidence_segment_ids) == 2

    complexity = out.complexity.to_dict()
    assert 0.0 <= float(complexity["complexity_score"]) <= 1.0
    assert set(complexity["complexity_components"].keys()) == {
        "reasoning_load",
        "scene_variant_load",
        "visual_scan",
    }
    assert all(0.0 <= float(value) <= 1.0 for value in complexity["complexity_components"].values())


def test_chart_flow_sankey_prompt_examples_match_contract() -> None:
    task = ChartsFlowSankeyPathValueTask()
    expected = {
        "source_to_target_total_flow": 27,
        "path_bottleneck_value": 12,
        "path_flow_difference": 9,
        "source_outgoing_total_flow": 31,
        "target_incoming_total_flow": 34,
    }

    for index, (query_id, answer) in enumerate(expected.items(), start=69200):
        out = task.generate(index, params={"query_id": query_id}, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence["answer"] == answer
        assert answer_only == {"answer": answer}
        assert isinstance(answer_and_evidence["evidence"], list)


def test_chart_flow_sankey_balanced_sampling_covers_variants() -> None:
    task = ChartsFlowSankeyPathValueTask()
    variants: Counter[str] = Counter()
    source_counts: Counter[int] = Counter()
    middle_counts: Counter[int] = Counter()
    target_counts: Counter[int] = Counter()
    path_counts: Counter[int] = Counter()

    for index in range(50):
        out = task.generate(hash64(69300, "charts_flow", index), params={}, max_attempts=10)
        execution = out.trace_payload["execution_trace"]
        variants[str(execution["query_id"])] += 1
        source_counts[int(execution["source_count"])] += 1
        middle_counts[int(execution["middle_count"])] += 1
        target_counts[int(execution["target_count"])] += 1
        path_counts[int(execution["path_count"])] += 1

    assert_counter_support_within(
        variants,
        SUPPORTED_QUERY_IDS,
        expected_per_key=10,
        tolerance=4,
    )
    assert set(source_counts.keys()).issubset({2, 3})
    assert set(middle_counts.keys()).issubset({2, 3})
    assert set(target_counts.keys()).issubset({2, 3})
    assert set(path_counts.keys()).issubset({3, 4})


def test_chart_flow_sankey_is_deterministic() -> None:
    task = ChartsFlowSankeyPathValueTask()
    params = {"query_id": "path_flow_difference", "scene_variant": SUPPORTED_SCENE_VARIANTS[0]}
    out_a = task.generate(69400, params=params, max_attempts=10)
    out_b = task.generate(69400, params=params, max_attempts=10)

    assert out_a.answer_gt == out_b.answer_gt
    assert out_a.evidence_gt == out_b.evidence_gt
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


@pytest.mark.parametrize("query_id", RADIAL_SUPPORTED_QUERY_IDS)
def test_chart_flow_radial_sankey_variants_match_contract(query_id: str) -> None:
    task = ChartsFlowRadialSankeyTask()
    out = task.generate(
        69500 + RADIAL_SUPPORTED_QUERY_IDS.index(query_id),
        params={"query_id": query_id, "scene_variant": "radial_chord_sankey"},
        max_attempts=10,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]
    render_map = trace["render_map"]

    assert out.query_id == query_id
    expected_type = "integer" if query_id in TRANSFER_TOTAL_QUERY_IDS else "string"
    assert out.answer_gt.type == expected_type
    assert out.evidence_gt.type == "bbox_set"
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert str(execution["scene_variant"]) == "radial_chord_sankey"
    expected_question_format = (
        "radial_sankey_transfer_total_value"
        if query_id in TRANSFER_TOTAL_QUERY_IDS
        else "radial_sankey_dominant_endpoint_label"
    )
    assert str(execution["question_format"]) == expected_question_format
    assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
    assert 4 <= int(execution["source_count"]) <= 5
    assert 4 <= int(execution["target_count"]) <= 5
    assert 7 <= int(execution["link_count"]) <= 9
    assert len(execution["links"]) == int(execution["link_count"])
    for side_counts in execution["link_side_counts"].values():
        assert max(int(value) for value in side_counts.values()) <= int(execution["max_links_per_node_side"])

    assert len(render_map["link_label_bboxes_px"]) == int(execution["link_count"])
    link_label_bboxes = [
        [float(value) for value in bbox]
        for bbox in render_map["link_label_bboxes_px"].values()
    ]
    for bbox in link_label_bboxes:
        _assert_bbox_inside_canvas(
            bbox,
            width=int(render["canvas_width"]),
            height=int(render["canvas_height"]),
        )
    for left_index, left_bbox in enumerate(link_label_bboxes):
        for right_bbox in link_label_bboxes[left_index + 1 :]:
            assert not _bboxes_overlap(left_bbox, right_bbox, gap=1.0)

    expected_answer = _expected_radial_answer(execution)
    assert out.answer_gt.value == expected_answer
    assert execution["answer_value"] == expected_answer
    assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value

    evidence_link_ids = [str(link_id) for link_id in execution["evidence_link_ids"]]
    evidence_node_ids = [str(node_id) for node_id in execution["evidence_node_ids"]]
    expected_bboxes = [render_map["link_label_bboxes_px"][link_id] for link_id in evidence_link_ids]
    expected_bboxes += [render_map["node_label_bboxes_px"][node_id] for node_id in evidence_node_ids]
    assert out.evidence_gt.value == expected_bboxes

    if query_id == "source_to_targets_total":
        assert 2 <= len(execution["query_link_ids"]) <= 3
        assert len({str(link["source_label"]) for link in execution["query_link_details"]}) == 1
        assert len(evidence_node_ids) == 0
    elif query_id == "sources_to_target_total":
        assert 2 <= len(execution["query_link_ids"]) <= 3
        assert len({str(link["target_label"]) for link in execution["query_link_details"]}) == 1
        assert len(evidence_node_ids) == 0
    else:
        assert len(execution["query_link_ids"]) >= 2
        assert len(evidence_node_ids) == 1
        values = [int(link["value"]) for link in execution["query_link_details"]]
        assert len(set(values)) == len(values)
        if query_id == "second_largest_target_for_source":
            assert len(execution["query_link_ids"]) >= 3

    complexity = out.complexity.to_dict()
    assert 0.0 <= float(complexity["complexity_score"]) <= 1.0
    assert set(complexity["complexity_components"].keys()) == {
        "reasoning_load",
        "scene_variant_load",
        "visual_scan",
    }


def test_chart_flow_radial_sankey_prompt_examples_match_contract() -> None:
    task = ChartsFlowRadialSankeyTask()
    expected = {
        "source_to_targets_total": 47,
        "sources_to_target_total": 39,
        "largest_target_for_source": "Y",
        "largest_source_for_target": "B",
        "second_largest_target_for_source": "X",
    }

    for index, (query_id, answer) in enumerate(expected.items(), start=69600):
        out = task.generate(index, params={"query_id": query_id}, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence["answer"] == answer
        assert answer_only == {"answer": answer}
        assert isinstance(answer_and_evidence["evidence"], list)


def test_chart_flow_radial_sankey_balanced_sampling_covers_variants() -> None:
    task = ChartsFlowRadialSankeyTask()
    variants: Counter[str] = Counter()
    for index in range(50):
        out = task.generate(hash64(69700, "charts_radial_flow", index), params={}, max_attempts=10)
        execution = out.trace_payload["execution_trace"]
        variants[str(execution["query_id"])] += 1

    assert_counter_support_within(
        variants,
        RADIAL_SUPPORTED_QUERY_IDS,
        expected_per_key=10,
        tolerance=5,
    )


def test_chart_flow_radial_sankey_is_deterministic() -> None:
    task = ChartsFlowRadialSankeyTask()
    params = {"query_id": "largest_source_for_target", "scene_variant": "radial_chord_sankey"}
    out_a = task.generate(69800, params=params, max_attempts=10)
    out_b = task.generate(69800, params=params, max_attempts=10)

    assert out_a.answer_gt == out_b.answer_gt
    assert out_a.evidence_gt == out_b.evidence_gt
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()

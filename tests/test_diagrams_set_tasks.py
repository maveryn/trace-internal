"""Behavior tests for diagrams set-diagram tasks."""

from __future__ import annotations

from collections import Counter
from itertools import combinations

from trace.core.seed import hash64
from trace.tasks.diagrams.set_diagram.region_sum_value import DiagramsSetRegionSumValueTask
from trace.tasks.shared.color_distance import color_distance
from tests.helpers import extract_prompt_json_example


def test_diagrams_set_region_sum_value_contract_matches_trace() -> None:
    task = DiagramsSetRegionSumValueTask()
    task_variants = (
        "sum_only_in_named_set",
        "sum_in_named_set",
        "sum_in_named_union",
        "sum_in_named_intersection",
        "sum_in_exactly_two_sets",
    )

    for variant_index, task_variant in enumerate(task_variants):
        seed = 61700 + variant_index
        out = task.generate(seed, params={"task_variant": task_variant, "scene_variant": "set_diagram"}, max_attempts=10)
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]
        render_map = trace["render_map"]
        evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value]

        expected_answer = sum(
            int(execution["region_number_map"][str(region_id)])
            for region_id in execution["contributing_region_ids"]
        )
        expected_bboxes = [
            [float(value) for value in render_map["number_bboxes_px"][str(bbox_id)]]
            for bbox_id in execution["supporting_number_bbox_ids"]
        ]

        assert out.answer_gt.type == "integer"
        assert out.evidence_gt.type == "bbox_set"
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert str(out.task_variant) == str(task_variant)
        assert str(execution["task_variant"]) == str(task_variant)
        assert str(execution["scene_variant"]) == "set_diagram"
        assert str(execution["question_format"]) == "set_region_sum_value"
        assert str(execution["view_family"]) == "set_diagram_numeric"
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
        assert int(out.answer_gt.value) == int(expected_answer)
        assert trace["projected_evidence"]["bbox_set"] == evidence_bboxes
        assert evidence_bboxes == expected_bboxes
        assert len(execution["number_specs"]) == int(execution["number_count"]) == 7
        assert len(render_map["number_bboxes_px"]) == 7
        assert int(execution["set_count"]) == 3
        assert int(trace["query_spec"]["params"]["contributing_region_count"]) == len(execution["contributing_region_ids"])


def test_diagrams_set_prompt_examples_match_variant_contract() -> None:
    task = DiagramsSetRegionSumValueTask()
    expected = {
        "sum_only_in_named_set": (
            {"evidence": [[300, 326, 329, 367]], "answer": 7},
            {"answer": 7},
        ),
        "sum_in_named_set": (
            {"evidence": [[300, 326, 329, 367], [559, 267, 589, 309], [451, 506, 481, 548], [559, 420, 589, 462]], "answer": 20},
            {"answer": 20},
        ),
        "sum_in_named_union": (
            {"evidence": [[300, 326, 329, 367], [818, 326, 847, 367], [559, 267, 589, 309], [451, 506, 481, 548], [667, 506, 697, 548], [559, 420, 589, 462]], "answer": 31},
            {"answer": 31},
        ),
        "sum_in_named_intersection": (
            {"evidence": [[559, 267, 589, 309], [559, 420, 589, 462]], "answer": 12},
            {"answer": 12},
        ),
        "sum_in_exactly_two_sets": (
            {"evidence": [[559, 267, 589, 309], [451, 506, 481, 548], [667, 506, 697, 548]], "answer": 18},
            {"answer": 18},
        ),
    }

    for index, (task_variant, (expected_answer_and_evidence, expected_answer_only)) in enumerate(expected.items(), start=61740):
        out = task.generate(index, params={"task_variant": task_variant}, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected_answer_and_evidence
        assert answer_only == expected_answer_only


def test_diagrams_set_region_sum_value_is_deterministic() -> None:
    task = DiagramsSetRegionSumValueTask()
    params = {"task_variant": "sum_in_named_union", "scene_variant": "set_diagram"}
    out_a = task.generate(61800, params=params, max_attempts=10)
    out_b = task.generate(61800, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_diagrams_set_balanced_sampling_defaults_cover_variants() -> None:
    task = DiagramsSetRegionSumValueTask()
    task_variants: Counter[str] = Counter()
    scene_variants: Counter[str] = Counter()

    for index in range(20):
        out = task.generate(hash64(61830, "diagrams_set", index), params={"_sampling_index": index}, max_attempts=10)
        execution = out.trace_payload["execution_trace"]
        task_variants[str(execution["task_variant"])] += 1
        scene_variants[str(execution["scene_variant"])] += 1

    assert set(task_variants.keys()) == {
        "sum_only_in_named_set",
        "sum_in_named_set",
        "sum_in_named_union",
        "sum_in_named_intersection",
        "sum_in_exactly_two_sets",
    }
    assert set(scene_variants.keys()) == {"set_diagram"}


def test_diagrams_set_variants_use_expected_region_counts_and_unique_digits() -> None:
    task = DiagramsSetRegionSumValueTask()
    expectations = {
        "sum_only_in_named_set": 1,
        "sum_in_named_set": 4,
        "sum_in_named_union": 6,
        "sum_in_named_intersection": 2,
        "sum_in_exactly_two_sets": 3,
    }
    for offset, (task_variant, expected_region_count) in enumerate(expectations.items()):
        out = task.generate(61880 + offset, params={"task_variant": task_variant, "scene_variant": "set_diagram"}, max_attempts=10)
        execution = out.trace_payload["execution_trace"]
        number_values = [int(spec["number_value"]) for spec in execution["number_specs"]]

        assert int(execution["set_count"]) == 3
        assert int(execution["number_count"]) == 7
        assert len(execution["contributing_region_ids"]) == int(expected_region_count)
        assert len(number_values) == len(set(number_values))
        assert all(1 <= int(value) <= 9 for value in number_values)


def test_diagrams_set_union_reasoning_load_exceeds_single_set_only() -> None:
    task = DiagramsSetRegionSumValueTask()
    simpler = task.generate(61920, params={"task_variant": "sum_only_in_named_set", "scene_variant": "set_diagram"}, max_attempts=10)
    harder = task.generate(61920, params={"task_variant": "sum_in_named_union", "scene_variant": "set_diagram"}, max_attempts=10)

    assert float(harder.complexity.complexity_components["reasoning_load"]) > float(
        simpler.complexity.complexity_components["reasoning_load"]
    )


def test_diagrams_set_palette_is_lab_separated() -> None:
    task = DiagramsSetRegionSumValueTask()
    out = task.generate(61950, params={"task_variant": "sum_in_named_set", "scene_variant": "set_diagram"}, max_attempts=10)
    execution = out.trace_payload["execution_trace"]
    colors = [
        tuple(int(channel) for channel in execution["set_fill_rgb_map"][set_id])
        for set_id in ("A", "B", "C")
    ]
    min_distance = float(execution["min_set_color_distance"])
    distance_space = str(execution["color_distance_space"])

    for color_a, color_b in combinations(colors, 2):
        assert float(color_distance(color_a, color_b, distance_space=distance_space)) >= float(min_distance)


def test_diagrams_set_c_label_stays_below_lower_circle_and_clear_of_c_only_number() -> None:
    task = DiagramsSetRegionSumValueTask()
    out = task.generate(61980, params={"task_variant": "sum_in_named_set", "scene_variant": "set_diagram"}, max_attempts=10)
    render_map = out.trace_payload["render_map"]
    set_c_region = [float(value) for value in render_map["region_bboxes_px"]["set_C_region"]]
    set_c_label = [float(value) for value in render_map["set_label_bboxes_px"]["set_C_label"]]
    c_only_bbox = [float(value) for value in render_map["number_slot_bboxes_px"]["number_bbox_2"]]

    assert set_c_label[1] >= set_c_region[3]
    assert set_c_label[1] >= c_only_bbox[3]


def test_diagrams_set_number_boxes_do_not_overlap() -> None:
    task = DiagramsSetRegionSumValueTask()
    out = task.generate(62020, params={"task_variant": "sum_in_exactly_two_sets", "scene_variant": "set_diagram"}, max_attempts=10)
    bbox_map = out.trace_payload["render_map"]["number_slot_bboxes_px"]
    bboxes = [[float(value) for value in bbox] for bbox in bbox_map.values()]

    for index, left_bbox in enumerate(bboxes):
        for right_bbox in bboxes[index + 1 :]:
            overlaps = not (
                left_bbox[2] <= right_bbox[0]
                or right_bbox[2] <= left_bbox[0]
                or left_bbox[3] <= right_bbox[1]
                or right_bbox[3] <= left_bbox[1]
            )
            assert not overlaps


def test_diagrams_set_regions_visibly_overlap() -> None:
    task = DiagramsSetRegionSumValueTask()
    out = task.generate(62060, params={"task_variant": "sum_in_named_union", "scene_variant": "set_diagram"}, max_attempts=10)
    region_map = out.trace_payload["render_map"]["region_bboxes_px"]
    set_a = [float(value) for value in region_map["set_A_region"]]
    set_b = [float(value) for value in region_map["set_B_region"]]
    set_c = [float(value) for value in region_map["set_C_region"]]

    def _overlap_width(left: list[float], right: list[float]) -> float:
        return max(0.0, min(float(left[2]), float(right[2])) - max(float(left[0]), float(right[0])))

    def _overlap_height(top: list[float], bottom: list[float]) -> float:
        return max(0.0, min(float(top[3]), float(bottom[3])) - max(float(top[1]), float(bottom[1])))

    assert _overlap_width(set_a, set_b) > 10.0
    assert _overlap_width(set_a, set_c) > 10.0
    assert _overlap_width(set_b, set_c) > 10.0
    assert _overlap_height(set_a, set_c) > 10.0
    assert _overlap_height(set_b, set_c) > 10.0

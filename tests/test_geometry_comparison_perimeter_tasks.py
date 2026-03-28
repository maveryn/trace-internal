"""Behavior tests for geometry comparison perimeter task."""

from __future__ import annotations

import json
from collections import Counter

from trace.core.seed import hash64
from trace.tasks.geometry.comparison.perimeter import GeometryComparisonPerimeterTask


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def test_geometry_comparison_perimeter_contract_matches_scene() -> None:
    task = GeometryComparisonPerimeterTask()
    for index, query_type in enumerate(("largest", "smallest")):
        out = task.generate(
            11130 + index,
            params={"query_type": query_type, "object_count": 6},
            max_attempts=400,
        )
        trace = out.trace_payload
        execution = trace["execution_trace"]
        assert out.answer_gt.type == "option_letter"
        assert isinstance(out.answer_gt.value, str) and len(out.answer_gt.value) == 1
        assert out.evidence_gt.type == "graph_point_set"
        assert isinstance(out.evidence_gt.value, list) and len(out.evidence_gt.value) == 4
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert trace["query_spec"]["prompt_variant_active_key"] == "answer_and_evidence"
        assert int(execution["object_count"]) == 6
        assert str(execution["query_type"]) == query_type
        assert execution["question_format"] == "label_choice_no_text_options"
        assert float(execution["winner_gap_normalized"]) >= 0.2 - 1e-9
        assert float(execution["winner_gap_abs"]) >= 4.0 - 1e-9
        assert 0.0 <= float(out.complexity.complexity_score) <= 1.0
        assert set(out.complexity.complexity_components.keys()) == {
            "visual_scan",
            "comparison_reasoning",
            "ambiguity",
            "output_burden",
        }
        assert all(0.0 <= float(value) <= 1.0 for value in out.complexity.complexity_components.values())
        assert len(execution["object_labels"]) == 6
        assert len(set(execution["object_labels"])) == 6
        assert "option" not in out.prompt.lower()
        assert "\nA." not in out.prompt and "\nB." not in out.prompt

        values_by_label = {str(key): float(value) for key, value in execution["values_by_label"].items()}
        if query_type == "largest":
            expected_label = max(values_by_label.items(), key=lambda item: (item[1], item[0]))[0]
        else:
            expected_label = min(values_by_label.items(), key=lambda item: (item[1], item[0]))[0]
        assert str(out.answer_gt.value) == expected_label == str(execution["winner_label"])

        winner_entity = next(
            entity for entity in trace["scene_ir"]["entities"] if str(entity["attrs"]["label"]) == str(expected_label)
        )
        frame = trace["render_spec"]["graph_coordinate_frame"]
        origin_x, origin_y = (int(frame["origin_pixel"][0]), int(frame["origin_pixel"][1]))
        spacing = int(frame["spacing_px"])
        expected_graph_points = [
            [
                int(round((float(point[0]) - float(origin_x)) / float(spacing))),
                int(round((float(origin_y) - float(point[1])) / float(spacing))),
            ]
            for point in winner_entity["attrs"]["vertices"]
        ]
        assert sorted(out.evidence_gt.value) == sorted(expected_graph_points)


def test_geometry_comparison_perimeter_prompt_example_matches_contract() -> None:
    task = GeometryComparisonPerimeterTask()
    out = task.generate(11132, params={"object_count": 5}, max_attempts=400)
    answer_only = _extract_prompt_json_example(out.prompt_variants["answer_only"])
    answer_and_evidence = _extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
    assert answer_only == {"answer": "B"}
    assert list(answer_and_evidence.keys()) == ["evidence", "answer"]
    assert isinstance(answer_and_evidence["evidence"], list)
    assert len(answer_and_evidence["evidence"]) == 4
    assert answer_and_evidence["answer"] == "B"


def test_geometry_comparison_perimeter_balanced_sampling_defaults() -> None:
    task = GeometryComparisonPerimeterTask()
    query_counts: Counter[str] = Counter()
    object_counts: Counter[int] = Counter()
    joint_counts: Counter[tuple[str, int]] = Counter()
    for index in range(72):
        out = task.generate(
            hash64(11133, "comparison_perimeter", index),
            params={"_sampling_index": index},
            max_attempts=400,
        )
        execution = out.trace_payload["execution_trace"]
        query_type = str(execution["query_type"])
        object_count = int(execution["object_count"])
        query_counts[query_type] += 1
        object_counts[object_count] += 1
        joint_counts[(query_type, object_count)] += 1
    assert set(query_counts.keys()) == {"largest", "smallest"}
    assert set(object_counts.keys()) == {4, 5, 6}
    assert max(query_counts.values()) - min(query_counts.values()) <= 1
    assert max(object_counts.values()) - min(object_counts.values()) <= 1
    assert max(joint_counts.values()) - min(joint_counts.values()) <= 1

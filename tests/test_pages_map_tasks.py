"""Behavior tests for pages map-navigation tasks."""

from __future__ import annotations

from collections import Counter

from trace.core.seed import hash64
from trace.tasks.pages.map.navigation_label import PagesMapNavigationLabelTask
from tests.helpers import extract_prompt_json_example


def test_pages_map_navigation_label_contract_matches_evidence_bboxes() -> None:
    task = PagesMapNavigationLabelTask()
    query_ids = (
        "destination_after_directions",
        "landmark_after_route_step",
    )

    for query_id_index, query_id in enumerate(query_ids):
        out = task.generate(
            62400 + query_id_index,
            params={"query_id": query_id, "scene_variant": "campus_map"},
            max_attempts=10,
        )
        trace = out.trace_payload
        execution = trace["execution_trace"]
        render = trace["render_spec"]
        render_map = trace["render_map"]
        evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value]
        evidence_bbox_ids = [str(bbox_id) for bbox_id in execution["evidence_bbox_ids"]]
        bbox_source = {
            **render_map["landmark_bboxes_px"],
            **render_map["zone_label_bboxes_px"],
        }

        assert out.answer_gt.type == "string"
        assert out.evidence_gt.type == "bbox_set"
        assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
        assert str(out.query_id) == "default"
        assert str(out.query_id) == str(query_id)
        assert str(execution["query_id"]) == "default"
        assert str(execution["query_id"]) == str(query_id)
        assert str(execution["scene_variant"]) == "campus_map"
        assert str(execution["question_format"]) == "map_navigation_label"
        assert str(execution["view_family"]) == "printed_campus_map"
        assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
        assert str(out.answer_gt.value) == str(execution["answer_label"])
        assert 10 <= int(execution["landmark_count"]) <= 14
        assert len(execution["landmark_specs"]) == int(execution["landmark_count"])
        assert len(render_map["landmark_bboxes_px"]) == int(execution["landmark_count"])
        assert len(render_map["zone_label_bboxes_px"]) == 4
        assert trace["projected_evidence"]["bbox_set"] == evidence_bboxes

        expected_bboxes = [[float(value) for value in bbox_source[bbox_id]] for bbox_id in evidence_bbox_ids]
        assert evidence_bboxes == expected_bboxes
        assert [str(item) for item in execution["supporting_bbox_ids"]] == evidence_bbox_ids

        if str(query_id) == "destination_after_directions":
            assert len(execution["route_landmark_ids"]) >= 3
            assert str(execution["evidence_semantics"]) == "route_landmarks_ordered"
            assert len(execution["evidence_landmark_bbox_ids"]) == len(execution["route_landmark_ids"])
        elif str(query_id) == "landmark_after_route_step":
            assert len(execution["highlighted_route_landmark_ids"]) >= 4
            assert render_map["highlighted_route_bboxes_px"]
            assert str(execution["evidence_semantics"]) == "highlighted_route_landmarks_ordered_to_answer"


def test_pages_map_navigation_label_prompt_examples_match_string_contract() -> None:
    task = PagesMapNavigationLabelTask()
    expected = {
        "destination_after_directions": "Clinic",
        "landmark_after_route_step": "Gallery",
    }

    for index, (query_id, expected_answer) in enumerate(expected.items(), start=62460):
        out = task.generate(index, params={"query_id": query_id, "scene_variant": "campus_map"}, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert str(answer_and_evidence["answer"]) == str(expected_answer)
        assert str(answer_only["answer"]) == str(expected_answer)
        assert isinstance(answer_and_evidence["evidence"], list)


def test_pages_map_navigation_label_is_deterministic() -> None:
    task = PagesMapNavigationLabelTask()
    params = {"query_id": "landmark_after_route_step", "scene_variant": "campus_map"}
    out_a = task.generate(62510, params=params, max_attempts=10)
    out_b = task.generate(62510, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()


def test_pages_map_navigation_label_balanced_sampling_covers_variants() -> None:
    task = PagesMapNavigationLabelTask()
    query_ids: Counter[str] = Counter()
    scene_variants: Counter[str] = Counter()

    for index in range(12):
        out = task.generate(hash64(62540, "pages_map", index), params={}, max_attempts=10)
        execution = out.trace_payload["execution_trace"]
        query_ids[str(execution["query_id"])] += 1
        scene_variants[str(execution["scene_variant"])] += 1

    assert set(query_ids.keys()) == {
        "destination_after_directions",
        "landmark_after_route_step",
    }
    assert set(scene_variants.keys()) == {"campus_map"}
    assert all(count >= 4 for count in query_ids.values())

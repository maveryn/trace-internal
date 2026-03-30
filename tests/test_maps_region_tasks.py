"""Behavior tests for maps region tasks."""

from __future__ import annotations

from trace.tasks.maps.region.association_label import MapsRegionAssociationLabelTask
from tests.helpers import extract_prompt_json_example


def test_maps_region_association_label_contract_matches_answer_region_bbox() -> None:
    task = MapsRegionAssociationLabelTask()
    task_variants = (
        "max_category_region",
        "min_category_region",
        "matches_legend_bin",
    )
    scene_variants = ("map_strip", "map_card", "map_outline")

    for variant_index, task_variant in enumerate(task_variants):
        for scene_index, scene_variant in enumerate(scene_variants):
            seed = 30100 + (variant_index * 20) + scene_index
            out = task.generate(seed, params={"task_variant": task_variant, "scene_variant": scene_variant}, max_attempts=10)
            trace = out.trace_payload
            execution = trace["execution_trace"]
            render = trace["render_spec"]
            render_map = trace["render_map"]
            evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value]

            assert str(out.task_variant) == str(task_variant)
            assert out.answer_gt.type == "option_letter"
            assert out.evidence_gt.type == "bbox_set"
            assert len(evidence_bboxes) == 1
            assert str(execution["scene_variant"]) == str(scene_variant)
            assert str(render["scene_variant"]) == str(scene_variant)
            assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
            assert 5 <= int(execution["region_count"]) <= 7
            assert 6 <= int(execution["grid_cols"]) <= 7
            assert 4 <= int(execution["grid_rows"]) <= 5
            assert int(execution["category_count"]) == 4
            assert str(execution["question_format"]) == "region_association_label"
            assert str(execution["view_family"]) == "region_legend_map"
            assert trace["projected_evidence"]["bbox_set"] == evidence_bboxes
            assert str(out.answer_gt.value) == str(execution["answer_region_label"])

            expected_bbox = [
                float(value)
                for value in render_map["region_bboxes_px"][str(execution["answer_region_bbox_id"])]
            ]
            assert evidence_bboxes[0] == expected_bbox
            assert [str(item) for item in execution["supporting_region_bbox_ids"]] == [
                str(execution["answer_region_bbox_id"])
            ]

            region_specs = execution["region_specs"]
            region_labels = [str(spec["region_label"]) for spec in region_specs]
            assert len(region_specs) == int(execution["region_count"])
            assert region_labels == sorted(region_labels)
            assert len(set(region_labels)) == len(region_labels)
            assert len(render_map["region_bboxes_px"]) == len(region_specs)
            assert len(execution["legend_specs"]) == 4
            assert len(render_map["legend_entry_bboxes_px"]) == 4

            if str(task_variant) == "max_category_region":
                winners = [
                    str(spec["region_label"])
                    for spec in region_specs
                    if int(spec["category_index"]) == max(int(item["category_index"]) for item in region_specs)
                ]
                assert winners == [str(out.answer_gt.value)]
            elif str(task_variant) == "min_category_region":
                winners = [
                    str(spec["region_label"])
                    for spec in region_specs
                    if int(spec["category_index"]) == min(int(item["category_index"]) for item in region_specs)
                ]
                assert winners == [str(out.answer_gt.value)]
            else:
                matches = [
                    str(spec["region_label"])
                    for spec in region_specs
                    if str(spec["category_label"]) == str(execution["query_category_label"])
                ]
                assert matches == [str(out.answer_gt.value)]


def test_maps_region_association_prompt_examples_match_variant_contract() -> None:
    task = MapsRegionAssociationLabelTask()
    expected = {
        "max_category_region": (
            {"evidence": [[174, 129, 412, 333]], "answer": "C"},
            {"answer": "C"},
        ),
        "min_category_region": (
            {"evidence": [[146, 360, 370, 562]], "answer": "A"},
            {"answer": "A"},
        ),
        "matches_legend_bin": (
            {"evidence": [[438, 180, 674, 420]], "answer": "F"},
            {"answer": "F"},
        ),
    }
    for index, (task_variant, (expected_answer_and_evidence, expected_answer_only)) in enumerate(expected.items(), start=30180):
        out = task.generate(index, params={"task_variant": task_variant}, max_attempts=10)
        answer_and_evidence = extract_prompt_json_example(out.prompt_variants["answer_and_evidence"])
        answer_only = extract_prompt_json_example(out.prompt_variants["answer_only"])
        assert answer_and_evidence == expected_answer_and_evidence
        assert answer_only == expected_answer_only


def test_maps_region_association_label_is_deterministic() -> None:
    task = MapsRegionAssociationLabelTask()
    params = {"task_variant": "matches_legend_bin", "scene_variant": "map_card"}
    out_a = task.generate(30230, params=params, max_attempts=10)
    out_b = task.generate(30230, params=params, max_attempts=10)

    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.trace_payload["query_spec"]["prompt_variant"] == out_b.trace_payload["query_spec"]["prompt_variant"]
    assert out_a.prompt == out_b.prompt
    assert out_a.image.tobytes() == out_b.image.tobytes()

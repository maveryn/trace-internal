"""Shared assertions for 3D below-scene option panels."""

from __future__ import annotations

from typing import Any, Mapping, Sequence


def assert_option_panel_matches_candidates(
    output: Any,
    candidate_specs: Sequence[Mapping[str, Any]],
    *,
    answer_label: str,
    answer_object_id: str,
    expected_image_size: tuple[int, int],
) -> None:
    """Assert option-panel metadata maps letters to scene objects.

    Annotation should point to the selected object in the scene, not to option
    text in the panel.
    """

    trace = output.trace_payload["execution_trace"]
    render_map = output.trace_payload["render_map"]
    labels = sorted(str(spec["point_label"]) for spec in candidate_specs)
    choices = [dict(choice) for choice in render_map["option_choices"]]
    choice_by_label = {str(choice["label"]): choice for choice in choices}
    option_bboxes = dict(render_map["option_choice_bboxes_px"])
    panel_bbox = [float(value) for value in render_map["option_panel_bbox_px"]]
    annotation_bbox = [float(value) for value in output.annotation_gt.value[0]]

    assert output.image.size == expected_image_size
    assert int(render_map["option_panel_height_px"]) == int(expected_image_size[1] - panel_bbox[1])
    assert panel_bbox == [0.0, panel_bbox[1], float(expected_image_size[0]), float(expected_image_size[1])]
    assert panel_bbox[1] > 0.0
    assert sorted(option_bboxes) == labels
    assert sorted(choice_by_label) == labels
    assert [str(choice["label"]) for choice in choices] == labels
    assert trace["option_choices"] == choices
    assert trace["option_descriptor_by_label"] == {
        str(choice["label"]): str(choice["descriptor"]) for choice in choices
    }

    for spec in candidate_specs:
        label = str(spec["point_label"])
        object_id = str(spec["object_id"])
        assert str(choice_by_label[label]["object_id"]) == object_id
        assert str(choice_by_label[label]["descriptor"]).strip()
        assert str(choice_by_label[label]["object_name"]).strip()

    assert output.annotation_gt.value == [render_map["object_bboxes_px"][str(answer_object_id)]]
    assert str(answer_label) in option_bboxes
    assert annotation_bbox[3] <= panel_bbox[1]
    assert output.annotation_gt.value[0] != option_bboxes[str(answer_label)]

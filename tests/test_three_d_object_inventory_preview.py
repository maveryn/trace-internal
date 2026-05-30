from collections import Counter

from trace.tasks.three_d.shared.object_inventory_preview import render_three_d_object_profile_preview
from trace.tasks.three_d.shared.object_resources import THREE_D_OBJECT_PROFILES


def test_inventory_preview_dispatches_all_registered_profiles_to_native_adapters():
    errors = []
    preview_renderer_counts = Counter()
    for profile in THREE_D_OBJECT_PROFILES:
        try:
            preview = render_three_d_object_profile_preview(
                profile,
                canvas_width=320,
                canvas_height=250,
                instance_seed=17,
            )
        except Exception as exc:  # pragma: no cover - failure aggregation for clearer review output.
            errors.append(f"{profile.profile_id}: {type(exc).__name__}: {exc}")
            continue
        preview_renderer_counts[str(preview.preview_renderer)] += 1
        assert preview.image.width > 0
        assert preview.image.height > 0
        assert preview.object_bbox_px[2] > preview.object_bbox_px[0]
        assert preview.object_bbox_px[3] > preview.object_bbox_px[1]
        assert preview.metadata["profile_renderer"] == profile.renderer
        assert preview.metadata["profile_source_scene"] == profile.source_scene

    assert errors == []
    assert preview_renderer_counts == Counter(str(profile.renderer) for profile in THREE_D_OBJECT_PROFILES)

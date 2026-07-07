"""Contract tests for the physics extension task batch."""

from __future__ import annotations

import itertools
import math

import trace.tasks  # noqa: F401
from trace.core.task_review_distribution import extract_sampling_axes
from trace.core.scene_config import get_scene_defaults
from trace.tasks.physics.analog_meter.meter_readout_value import PhysicsAnalogMeterReadoutValueTask
from trace.tasks.physics.bridge_circuit.bridge_missing_resistance_value import (
    PhysicsBridgeCircuitMissingResistanceValueTask,
)
from trace.tasks.physics.bulb_circuit.brightness_extremum_label import (
    PhysicsBulbCircuitBrightnessExtremumLabelTask,
)
from trace.tasks.physics.circuit_state_change.bulb_brightness_change_label import (
    PhysicsCircuitStateChangeBulbBrightnessLabelTask,
)
from trace.tasks.physics.switch_circuit.lit_bulb_count import PhysicsSwitchCircuitLitBulbCountTask
from trace.tasks.physics.buoyancy_density.object_density_value import PhysicsBuoyancyDensityObjectDensityValueTask
from trace.tasks.physics.fluid_flow.continuity_speed_value import PhysicsFluidFlowContinuitySpeedValueTask
from trace.tasks.physics.graduated_cylinder.displacement_volume_value import (
    PhysicsGraduatedCylinderDisplacementVolumeValueTask,
)
from trace.tasks.physics.graduated_cylinder.volume_readout_value import (
    PhysicsGraduatedCylinderVolumeReadoutValueTask,
)
from trace.tasks.physics.manometer.pressure_difference_value import PhysicsManometerPressureDifferenceValueTask
from trace.tasks.physics.electromagnetic_induction.induced_current_direction_count import (
    PhysicsElectromagneticInductionDirectionCountTask,
)
from trace.tasks.physics.electrostatic_field.field_direction_choice import (
    PhysicsElectrostaticFieldDirectionChoiceTask,
)
from trace.tasks.physics.electrostatic_field.potential_value import (
    PhysicsElectrostaticFieldPotentialValueTask,
)
from trace.tasks.physics.electrostatic_field.zero_field_point_label import (
    PhysicsElectrostaticFieldZeroFieldPointLabelTask,
)
from trace.tasks.physics.shared.diagram_style import (
    PHYSICS_ELECTROSTATICS_SEMANTIC_COLORS,
    resolve_physics_diagram_style,
)
from trace.tasks.physics.wire_magnetism.wire_field_direction_choice import PhysicsWireMagnetismFieldDirectionChoiceTask
from trace.tasks.physics.vernier_caliper.length_readout_value import (
    PhysicsVernierCaliperLengthReadoutValueTask,
)
from trace.tasks.physics.free_body_forces.net_force_direction_choice import (
    PhysicsFreeBodyForcesNetForceDirectionChoiceTask,
)
from trace.tasks.physics.gear_train.output_direction_label import (
    PhysicsGearTrainOutputDirectionLabelTask,
)
from trace.tasks.physics.gear_train.output_speed_value import (
    PhysicsGearTrainOutputSpeedValueTask,
)
from trace.tasks.physics.motion_graph.average_speed_value import (
    PhysicsMotionGraphAverageSpeedValueTask,
)
from trace.tasks.physics.motion_graph.interval_displacement_value import (
    PhysicsMotionGraphIntervalDisplacementValueTask,
)
from trace.tasks.physics.motion_graph.speed_change_state_choice import (
    PhysicsMotionGraphSpeedChangeStateChoiceTask,
)
from trace.tasks.physics.orbital_motion.focus_location_label import (
    PhysicsOrbitalMotionFocusLocationLabelTask,
)
from trace.tasks.physics.orbital_motion.orbital_speed_extremum_label import (
    PhysicsOrbitalMotionSpeedExtremumLabelTask,
)
from trace.tasks.physics.stack_stability.stability_status_label import (
    PhysicsStackStabilityStatusLabelTask,
)
from trace.tasks.physics.refraction_layers.medium_speed_order_label import (
    PhysicsRefractionLayersMediumSpeedOrderLabelTask,
)
from trace.tasks.physics.shadow_cause.light_source_label import PhysicsShadowCauseLightSourceLabelTask
from trace.tasks.physics.lens_optics.image_property_choice import PhysicsLensOpticsImagePropertyChoiceTask
from trace.tasks.physics.piston_cylinder.boundary_work_value import PhysicsPistonCylinderBoundaryWorkValueTask
from trace.tasks.physics.thermal_mixing.final_temperature_value import (
    PhysicsThermalMixingFinalTemperatureValueTask,
)
from trace.tasks.physics.thermometer.temperature_conversion_value import PhysicsThermometerTemperatureConversionValueTask
from trace.tasks.physics.signal_transform.periodic_harmonic_spectrum_match_label import (
    PhysicsSignalTransformPeriodicHarmonicSpectrumMatchLabelTask,
)
from trace.tasks.physics.wave_interference.interference_point_choice import (
    PhysicsWavesInterferencePointChoiceTask,
)
from trace.tasks.physics.wave_interference.path_difference_value import (
    PhysicsWavesPathDifferenceValueTask,
)
from trace.tasks.physics.waveform_panel.wave_property_extremum_label import (
    PhysicsWaveformPanelWavePropertyExtremumLabelTask,
)
from trace.tasks.registry import list_default_task_ids
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults


NEW_PHYSICS_TASK_IDS = {
    "task_physics__orbital_motion__focus_location_label",
    "task_physics__orbital_motion__orbital_speed_extremum_label",
    "task_physics__graduated_cylinder__volume_readout_value",
    "task_physics__graduated_cylinder__displacement_volume_value",
    "task_physics__wire_magnetism__wire_field_direction_choice",
    "task_physics__refraction_layers__medium_speed_order_label",
    "task_physics__shadow_cause__light_source_label",
    "task_physics__lens_optics__image_property_choice",
    "task_physics__bulb_circuit__brightness_extremum_label",
    "task_physics__switch_circuit__lit_bulb_count",
    "task_physics__circuit_state_change__bulb_brightness_change_label",
    "task_physics__bridge_circuit__bridge_missing_resistance_value",
    "task_physics__motion_graph__average_speed_value",
    "task_physics__motion_graph__speed_change_state_choice",
    "task_physics__motion_graph__interval_displacement_value",
    "task_physics__buoyancy_density__object_density_value",
    "task_physics__waveform_panel__wave_property_extremum_label",
    "task_physics__manometer__pressure_difference_value",
    "task_physics__analog_meter__meter_readout_value",
    "task_physics__piston_cylinder__boundary_work_value",
    "task_physics__thermal_mixing__final_temperature_value",
    "task_physics__thermometer__temperature_conversion_value",
    "task_physics__fluid_flow__continuity_speed_value",
    "task_physics__gear_train__output_direction_label",
    "task_physics__gear_train__output_speed_value",
    "task_physics__signal_transform__periodic_harmonic_spectrum_match_label",
    "task_physics__wave_interference__interference_point_choice",
    "task_physics__wave_interference__path_difference_value",
    "task_physics__vernier_caliper__length_readout_value",
    "task_physics__stack_stability__stability_status_label",
    "task_physics__collision__sticky_collision_direction_choice",
    "task_physics__collision__sticky_collision_speed_value",
    "task_physics__electromagnetic_induction__induced_current_direction_count",
    "task_physics__electrostatic_field__field_direction_choice",
    "task_physics__electrostatic_field__potential_value",
    "task_physics__electrostatic_field__zero_field_point_label",
    "task_physics__free_body_forces__net_force_direction_choice",
}


def _assert_bbox_map_in_bounds(out) -> None:
    width, height = out.image.size
    assert out.annotation_gt.type == "bbox_map"
    for bbox in out.annotation_gt.value.values():
        assert 0 <= bbox[0] < bbox[2] <= width
        assert 0 <= bbox[1] < bbox[3] <= height


def _assert_bbox_set_in_bounds(out) -> None:
    width, height = out.image.size
    assert out.annotation_gt.type == "bbox_set"
    for bbox in out.annotation_gt.value:
        assert 0 <= bbox[0] < bbox[2] <= width
        assert 0 <= bbox[1] < bbox[3] <= height


def _assert_bbox_in_bounds(out) -> None:
    width, height = out.image.size
    assert out.annotation_gt.type == "bbox"
    bbox = out.annotation_gt.value
    assert 0 <= bbox[0] < bbox[2] <= width
    assert 0 <= bbox[1] < bbox[3] <= height


def _assert_segment_in_bounds(out) -> None:
    width, height = out.image.size
    assert out.annotation_gt.type == "segment"
    assert len(out.annotation_gt.value) == 2
    for point in out.annotation_gt.value:
        assert 0 <= point[0] <= width
        assert 0 <= point[1] <= height


def _assert_point_map_in_bounds(out) -> None:
    width, height = out.image.size
    assert out.annotation_gt.type == "point_map"
    for point in out.annotation_gt.value.values():
        assert 0 <= point[0] <= width
        assert 0 <= point[1] <= height


def _assert_point_in_bounds(out) -> None:
    width, height = out.image.size
    assert out.annotation_gt.type == "point"
    point = out.annotation_gt.value
    assert 0 <= point[0] <= width
    assert 0 <= point[1] <= height


def test_physics_extension_task_ids_are_default_registered() -> None:
    physics_ids = {task_id for task_id in list_default_task_ids() if task_id.startswith("task_physics__")}

    assert len(physics_ids) == 50
    assert NEW_PHYSICS_TASK_IDS.issubset(physics_ids)


def test_physics_electromagnetic_induction_count_contract() -> None:
    task = PhysicsElectromagneticInductionDirectionCountTask()
    for query_id in [
        "clockwise_induced_current_count",
        "counterclockwise_induced_current_count",
        "no_induced_current_count",
    ]:
        out = task.generate(90501, params={"query_id": query_id, "target_answer": 3}, max_attempts=20)
        execution = out.trace_payload["execution_trace"]

        assert out.scene_id == "electromagnetic_induction"
        assert out.query_id == query_id
        assert out.answer_gt.type == "integer"
        assert out.answer_gt.value == 3
        assert out.annotation_gt.type == "bbox_set"
        assert len(out.annotation_gt.value) == 3
        _assert_bbox_set_in_bounds(out)
        assert execution["target_answer"] == 3
        assert len(execution["matching_panel_ids"]) == 3
        assert out.trace_payload["projected_annotation"]["bbox_set"] == out.annotation_gt.value
        assert out.prompt_variants["answer_only"]
        assert out.prompt_variants["answer_and_annotation"]


def test_physics_electromagnetic_induction_count_supports_zero_and_six() -> None:
    task = PhysicsElectromagneticInductionDirectionCountTask()
    zero = task.generate(
        90531,
        params={"query_id": "clockwise_induced_current_count", "target_answer": 0},
        max_attempts=20,
    )
    six = task.generate(
        90532,
        params={"query_id": "no_induced_current_count", "target_answer": 6},
        max_attempts=20,
    )

    assert zero.answer_gt.value == 0
    assert zero.annotation_gt.value == []
    assert zero.trace_payload["execution_trace"]["matching_panel_ids"] == []
    assert six.answer_gt.value == 6
    assert len(six.annotation_gt.value) == 6
    _assert_bbox_set_in_bounds(six)


def test_physics_electrostatic_field_direction_choice_contract() -> None:
    out = PhysicsElectrostaticFieldDirectionChoiceTask().generate(
        90601,
        params={
            "query_id": "force_on_negative_charge",
            "target_direction": "north",
            "correct_option_letter": "D",
        },
        max_attempts=20,
    )

    assert out.scene_id == "electrostatic_field"
    assert out.query_id == "force_on_negative_charge"
    assert out.answer_gt.type == "option_letter"
    assert out.answer_gt.value == "D"
    assert set(out.annotation_gt.value) == {"Q1", "Q2", "Q3", "P"}
    _assert_point_map_in_bounds(out)
    assert out.trace_payload["projected_annotation"]["point_map"] == out.annotation_gt.value
    assert out.trace_payload["execution_trace"]["direction_mode"] == "negative_force"
    assert out.trace_payload["execution_trace"]["target_direction"] == "north"
    assert out.trace_payload["execution_trace"]["direction_scenario"]["test_charge_sign"] == "-"
    assert out.trace_payload["render_map"]["query_point_test_charge_sign"] == "-"


def test_physics_electrostatic_field_zero_field_contract() -> None:
    out = PhysicsElectrostaticFieldZeroFieldPointLabelTask().generate(
        90611,
        params={"correct_option_letter": "E"},
        max_attempts=20,
    )

    assert out.scene_id == "electrostatic_field"
    assert out.query_id == "single"
    assert out.answer_gt.type == "option_letter"
    assert out.answer_gt.value == "E"
    assert set(out.annotation_gt.value) == {"Q1", "Q2", "zero_point"}
    _assert_point_map_in_bounds(out)
    assert out.trace_payload["projected_annotation"]["point_map"] == out.annotation_gt.value
    assert out.trace_payload["execution_trace"]["zero_field_scenario"]["correct_option_letter"] == "E"
    render_map = out.trace_payload["render_map"]
    for marker_bbox in render_map["candidate_marker_bboxes_px"].values():
        assert marker_bbox[2] - marker_bbox[0] <= 22
        assert marker_bbox[3] - marker_bbox[1] <= 22
    center_by_letter = {
        str(entity["meta"]["option_letter"]): entity["meta"]["center_px"]
        for entity in out.trace_payload["scene_ir"]["entities"]
        if entity.get("entity_type") == "candidate_zero_field_point"
    }
    for letter, label_bbox in render_map["candidate_label_bboxes_px"].items():
        label_center = [(float(label_bbox[0]) + float(label_bbox[2])) / 2.0, (float(label_bbox[1]) + float(label_bbox[3])) / 2.0]
        point_center = center_by_letter[str(letter)]
        assert math.hypot(label_center[0] - float(point_center[0]), label_center[1] - float(point_center[1])) <= 48.0


def test_physics_electrostatic_field_potential_value_contract() -> None:
    out = PhysicsElectrostaticFieldPotentialValueTask().generate(
        90621,
        params={"target_answer": -4},
        max_attempts=20,
    )

    assert out.scene_id == "electrostatic_field"
    assert out.query_id == "single"
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == -4
    assert set(out.annotation_gt.value) == {"Q1", "Q2", "Q3", "P"}
    _assert_point_map_in_bounds(out)
    assert out.trace_payload["projected_annotation"]["point_map"] == out.annotation_gt.value
    assert out.trace_payload["execution_trace"]["potential_scenario"]["potential_value"] == -4


def test_physics_electrostatic_field_style_pool_keeps_light_and_dark_themes() -> None:
    scene = get_scene_defaults("physics", "electrostatic_field")
    _generation, rendering, _prompt = split_generation_rendering_prompt_defaults(
        scene,
        task_id="task_physics__electrostatic_field__field_direction_choice",
    )
    selected = []
    for seed in range(24):
        _style, metadata = resolve_physics_diagram_style(
            instance_seed=seed,
            params=rendering,
            scene_id="electrostatic_field",
            protected_colors=PHYSICS_ELECTROSTATICS_SEMANTIC_COLORS,
        )
        selected.append((metadata["theme_id"], tuple(metadata["theme_compatibility"])))

    theme_ids = {theme_id for theme_id, _compatibility in selected}
    compatibilities = {item for _theme_id, compatibility in selected for item in compatibility}
    assert len(theme_ids) > 1
    assert "light" in compatibilities
    assert "dark" in compatibilities


def test_physics_orbital_focus_contract() -> None:
    out = PhysicsOrbitalMotionFocusLocationLabelTask().generate(80101, params={}, max_attempts=20)
    trace = out.trace_payload

    assert out.scene_id == "orbital_motion"
    assert out.query_id == "single"
    assert out.answer_gt.type == "option_letter"
    assert out.annotation_gt.type == "point"
    _assert_point_in_bounds(out)
    assert trace["projected_annotation"]["point"] == out.annotation_gt.value
    assert trace["projected_annotation"]["pixel_point"] == out.annotation_gt.value
    assert trace["render_map"]["selected_label"] == out.answer_gt.value
    assert trace["render_map"]["selected_point"] == out.annotation_gt.value
    assert out.prompt_variants["answer_only"]
    assert out.prompt_variants["answer_and_annotation"]

    endpoints = trace["render_map"]["major_axis_endpoints"]
    candidate_points = trace["render_map"]["candidate_points"]
    assert len(candidate_points) == 6

    def _distance_to_major_axis(point: list[float]) -> float:
        ax, ay = endpoints[0]
        bx, by = endpoints[1]
        px, py = point
        return abs((by - ay) * px - (bx - ax) * py + bx * ay - by * ax) / math.hypot(bx - ax, by - ay)

    major_axis_candidate_labels = [
        label for label, point in candidate_points.items() if _distance_to_major_axis(point) < 1.5
    ]
    assert out.answer_gt.value in major_axis_candidate_labels
    assert len(major_axis_candidate_labels) == 4
    assert len(candidate_points) - len(major_axis_candidate_labels) == 2


def test_physics_orbital_speed_extremum_uses_sun_distance() -> None:
    task = PhysicsOrbitalMotionSpeedExtremumLabelTask()
    for query_id, direction in [
        ("greatest_speed_position_label", min),
        ("least_speed_position_label", max),
    ]:
        out = task.generate(80177, params={"query_id": query_id}, max_attempts=20)
        render_map = out.trace_payload["render_map"]
        sun = render_map["sun_point"]
        assert len(render_map["candidate_points"]) == 4
        distances = {
            str(label): math.hypot(float(point[0] - sun[0]), float(point[1] - sun[1]))
            for label, point in render_map["candidate_points"].items()
        }
        expected_label = direction(distances, key=distances.get)

        assert out.query_id == query_id
        assert out.answer_gt.value == expected_label
        assert render_map["selected_label"] == expected_label
        assert out.annotation_gt.type == "point"
        assert out.annotation_gt.value == render_map["selected_point"]
        assert out.trace_payload["projected_annotation"]["point"] == out.annotation_gt.value
        assert out.trace_payload["projected_annotation"]["pixel_point"] == out.annotation_gt.value
        assert min(
            math.hypot(
                float(render_map["selected_point"][0] - endpoint[0]),
                float(render_map["selected_point"][1] - endpoint[1]),
            )
            for endpoint in render_map["major_axis_endpoints"]
        ) > 20.0
        _assert_point_in_bounds(out)


def test_physics_graduated_cylinder_readout_contracts() -> None:
    volume = PhysicsGraduatedCylinderVolumeReadoutValueTask().generate(80201, params={}, max_attempts=20)
    displacement = PhysicsGraduatedCylinderDisplacementVolumeValueTask().generate(80203, params={}, max_attempts=20)

    assert volume.scene_id == "graduated_cylinder"
    assert volume.query_id == "single"
    assert volume.answer_gt.type == "integer"
    assert volume.answer_gt.value == volume.trace_payload["render_map"]["cylinders"]["single"]["volume_ml"]
    assert volume.annotation_gt.value == volume.trace_payload["render_map"]["cylinders"]["single"]["readout_bbox"]
    _assert_bbox_in_bounds(volume)

    assert displacement.scene_id == "graduated_cylinder"
    assert displacement.query_id == "single"
    assert displacement.answer_gt.type == "integer"
    assert displacement.answer_gt.value == displacement.trace_payload["render_map"]["displacement_ml"]
    assert set(displacement.annotation_gt.value) == {"before_cylinder", "after_cylinder"}
    assert displacement.annotation_gt.value["before_cylinder"] == displacement.trace_payload["render_map"]["cylinders"]["before"]["readout_bbox"]
    assert displacement.annotation_gt.value["after_cylinder"] == displacement.trace_payload["render_map"]["cylinders"]["after"]["readout_bbox"]
    _assert_bbox_map_in_bounds(displacement)


def test_physics_buoyancy_density_contract() -> None:
    out = PhysicsBuoyancyDensityObjectDensityValueTask().generate(
        80251,
        params={
            "scene_variant": "rectangular_tank",
            "object_shape": "rounded_block",
            "submerged_fraction": "2/3",
            "liquid_density_tenths": 12,
            "target_answer": 0.8,
        },
        max_attempts=20,
    )
    execution = out.trace_payload["execution_trace"]
    render_map = out.trace_payload["render_map"]

    assert out.scene_id == "buoyancy_density"
    assert out.query_id == "single"
    assert out.answer_gt.type == "number"
    assert math.isclose(float(out.answer_gt.value), 0.8, abs_tol=1e-9)
    assert math.isclose(
        float(out.answer_gt.value),
        float(execution["liquid_density_g_cm3"])
        * float(execution["submerged_fraction_num"])
        / float(execution["submerged_fraction_den"]),
        abs_tol=1e-9,
    )
    assert out.annotation_gt.value == render_map["floating_object_bbox_px"]
    _assert_bbox_in_bounds(out)
    assert out.trace_payload["projected_annotation"]["bbox"] == out.annotation_gt.value
    assert render_map["submerged_fraction"] == {"numerator": 2, "denominator": 3, "value": 2 / 3}
    assert math.isclose(float(render_map["liquid_density_g_cm3"]), 1.2, abs_tol=1e-9)
    assert math.isclose(float(render_map["object_density_g_cm3"]), 0.8, abs_tol=1e-9)


def test_physics_manometer_pressure_difference_contract() -> None:
    out = PhysicsManometerPressureDifferenceValueTask().generate(
        80277,
        params={
            "height_cm": 6,
            "kpa_per_cm": 3,
            "higher_pressure_side": "A",
        },
        max_attempts=20,
    )
    execution = out.trace_payload["execution_trace"]
    render_map = out.trace_payload["render_map"]

    assert out.scene_id == "manometer"
    assert out.query_id == "single"
    assert out.trace_payload["query_spec"]["params"]["internal_query_id"] == "u_tube_pressure_difference"
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == 18
    assert out.answer_gt.value == int(execution["height_cm"]) * int(execution["kpa_per_cm"])
    assert render_map["pressure_difference_kpa"] == 18
    assert render_map["higher_pressure_side"] == "A"
    assert render_map["left_level_y_px"] > render_map["right_level_y_px"]
    assert set(out.annotation_gt.value) == {"height_difference", "fluid_density_label"}
    assert render_map["annotation_bbox_map_px"] == out.annotation_gt.value
    _assert_bbox_map_in_bounds(out)
    assert out.trace_payload["projected_annotation"]["bbox_map"] == out.annotation_gt.value


def test_physics_fluid_flow_continuity_contracts() -> None:
    task = PhysicsFluidFlowContinuitySpeedValueTask()
    missing_v2 = task.generate(
        80283,
        params={
            "orientation": "horizontal_pipe",
            "missing_speed_station": "v2",
            "area_1_cm2": 6,
            "speed_1_m_s": 4,
            "area_2_cm2": 3,
        },
        max_attempts=20,
    )
    missing_v1 = task.generate(
        80285,
        params={
            "orientation": "vertical_pipe",
            "missing_speed_station": "v1",
            "area_1_cm2": 8,
            "area_2_cm2": 4,
            "speed_2_m_s": 10,
        },
        max_attempts=20,
    )

    assert missing_v2.scene_id == "fluid_flow"
    assert missing_v2.query_id == "single"
    assert missing_v2.answer_gt.type == "integer"
    assert missing_v2.answer_gt.value == 8
    assert missing_v2.trace_payload["execution_trace"]["continuity_lhs"] == 24
    assert missing_v2.trace_payload["execution_trace"]["continuity_rhs"] == 24
    assert missing_v2.trace_payload["render_map"]["missing_station"] == "v2"
    assert missing_v2.annotation_gt.type == "bbox"
    assert missing_v2.annotation_gt.value == missing_v2.trace_payload["render_map"]["missing_speed_label_bbox_px"]
    _assert_bbox_in_bounds(missing_v2)
    assert missing_v2.trace_payload["projected_annotation"]["bbox"] == missing_v2.annotation_gt.value
    sampling_axes = extract_sampling_axes(missing_v2)
    for axis in ("area_1_cm2", "area_2_cm2", "speed_1_m_s", "speed_2_m_s"):
        assert sampling_axes[axis]["observed"]
    assert "area_1" not in sampling_axes
    assert "speed_1" not in sampling_axes

    assert missing_v1.answer_gt.type == "integer"
    assert missing_v1.answer_gt.value == 5
    assert missing_v1.trace_payload["execution_trace"]["continuity_lhs"] == 40
    assert missing_v1.trace_payload["execution_trace"]["continuity_rhs"] == 40
    assert missing_v1.trace_payload["render_map"]["missing_station"] == "v1"
    assert missing_v1.annotation_gt.type == "bbox"
    assert missing_v1.annotation_gt.value == missing_v1.trace_payload["render_map"]["missing_speed_label_bbox_px"]
    _assert_bbox_in_bounds(missing_v1)


def test_physics_gear_train_direction_contracts() -> None:
    task = PhysicsGearTrainOutputDirectionLabelTask()
    two_gears = task.generate(
        80291,
        params={
            "target_direction": "clockwise",
            "correct_option_letter": "C",
        },
        max_attempts=20,
    )
    five_gears = task.generate(
        80293,
        params={
            "target_direction": "counterclockwise",
            "correct_option_letter": "A",
        },
        max_attempts=20,
    )

    assert two_gears.scene_id == "gear_train"
    assert two_gears.query_id == "single"
    assert two_gears.answer_gt.type == "option_letter"
    assert two_gears.answer_gt.value == "C"
    assert two_gears.trace_payload["execution_trace"]["target_direction"] == "clockwise"
    assert two_gears.trace_payload["render_map"]["panel_output_directions"]["C"] == "clockwise"
    assert list(two_gears.trace_payload["render_map"]["panel_output_directions"].values()).count("clockwise") == 1
    assert two_gears.annotation_gt.type == "bbox"
    _assert_bbox_in_bounds(two_gears)
    assert two_gears.trace_payload["projected_annotation"]["bbox"] == two_gears.annotation_gt.value
    assert two_gears.trace_payload["render_map"]["selected_panel_bbox_px"] == two_gears.annotation_gt.value
    assert "clockwise" in two_gears.prompt_variants["answer_only"]

    assert five_gears.answer_gt.type == "option_letter"
    assert five_gears.answer_gt.value == "A"
    assert five_gears.trace_payload["execution_trace"]["target_direction"] == "counterclockwise"
    assert five_gears.trace_payload["render_map"]["panel_output_directions"]["A"] == "counterclockwise"
    assert list(five_gears.trace_payload["render_map"]["panel_output_directions"].values()).count("counterclockwise") == 1
    _assert_bbox_in_bounds(five_gears)
    assert "counterclockwise" in five_gears.prompt_variants["answer_only"]


def test_physics_gear_train_direction_option_letters_balance_with_sample_cursor() -> None:
    task = PhysicsGearTrainOutputDirectionLabelTask()
    answer_counts = {"A": 0, "B": 0, "C": 0, "D": 0}
    direction_counts = {"clockwise": 0, "counterclockwise": 0}

    for index in range(40):
        out = task.generate(
            80311 + int(index),
            params={"_sample_cursor": int(index)},
            max_attempts=20,
        )
        answer_counts[str(out.answer_gt.value)] += 1
        direction_counts[str(out.trace_payload["execution_trace"]["target_direction"])] += 1

    assert answer_counts == {"A": 10, "B": 10, "C": 10, "D": 10}
    assert direction_counts == {"clockwise": 20, "counterclockwise": 20}


def test_physics_gear_train_speed_contracts() -> None:
    task = PhysicsGearTrainOutputSpeedValueTask()
    slower = task.generate(
        80297,
        params={
            "scene_variant": "straight_chain",
            "gear_count": 2,
            "input_teeth": 20,
            "output_teeth": 40,
            "input_rpm": 120,
        },
        max_attempts=20,
    )
    faster_with_idlers = task.generate(
        80299,
        params={
            "scene_variant": "staggered_chain",
            "gear_count": 4,
            "input_teeth": 36,
            "output_teeth": 12,
            "input_rpm": 60,
        },
        max_attempts=20,
    )

    assert slower.scene_id == "gear_train"
    assert slower.query_id == "single"
    assert slower.answer_gt.type == "integer"
    assert slower.answer_gt.value == 60
    assert slower.trace_payload["execution_trace"]["input_rpm"] == 120
    assert slower.trace_payload["execution_trace"]["input_teeth"] == 20
    assert slower.trace_payload["execution_trace"]["output_teeth"] == 40
    assert slower.trace_payload["execution_trace"]["speed_relation"] == "slower"
    assert set(slower.annotation_gt.value) == {"input_gear", "output_gear"}
    _assert_bbox_map_in_bounds(slower)
    assert slower.trace_payload["projected_annotation"]["bbox_map"] == slower.annotation_gt.value
    assert "gear_train_bbox_px" in slower.trace_payload["render_map"]

    assert faster_with_idlers.answer_gt.type == "integer"
    assert faster_with_idlers.answer_gt.value == 180
    assert faster_with_idlers.trace_payload["execution_trace"]["gear_count"] == 4
    assert len(faster_with_idlers.trace_payload["execution_trace"]["idler_teeth"]) == 2
    assert faster_with_idlers.trace_payload["execution_trace"]["speed_relation"] == "faster"
    assert faster_with_idlers.trace_payload["render_map"]["ratio_numerator"] == 2160
    assert faster_with_idlers.trace_payload["render_map"]["ratio_denominator"] == 12
    _assert_bbox_map_in_bounds(faster_with_idlers)


def test_physics_manometer_pressure_side_does_not_change_absolute_answer() -> None:
    task = PhysicsManometerPressureDifferenceValueTask()
    left_high = task.generate(80281, params={"height_cm": 5, "kpa_per_cm": 4, "higher_pressure_side": "A"}, max_attempts=20)
    right_high = task.generate(80281, params={"height_cm": 5, "kpa_per_cm": 4, "higher_pressure_side": "B"}, max_attempts=20)

    assert left_high.answer_gt.value == 20
    assert right_high.answer_gt.value == 20
    assert left_high.trace_payload["render_map"]["left_level_y_px"] > left_high.trace_payload["render_map"]["right_level_y_px"]
    assert right_high.trace_payload["render_map"]["right_level_y_px"] > right_high.trace_payload["render_map"]["left_level_y_px"]


def test_physics_analog_meter_readout_contracts() -> None:
    task = PhysicsAnalogMeterReadoutValueTask()
    ammeter = task.generate(
        80291,
        params={"query_id": "ammeter_readout", "meter_profile": "ammeter_a", "readout_value": 7},
        max_attempts=20,
    )
    voltmeter = task.generate(
        80293,
        params={"query_id": "voltmeter_readout", "meter_profile": "voltmeter_v", "readout_value": 11},
        max_attempts=20,
    )

    assert ammeter.scene_id == "analog_meter"
    assert ammeter.query_id == "ammeter_readout"
    assert ammeter.answer_gt.type == "integer"
    assert ammeter.answer_gt.value == 7
    assert ammeter.trace_payload["execution_trace"]["unit"] == "A"
    assert ammeter.trace_payload["render_map"]["readout_value"] == 7
    assert ammeter.annotation_gt.value == ammeter.trace_payload["render_map"]["needle_segment_px"]
    _assert_segment_in_bounds(ammeter)
    assert ammeter.trace_payload["projected_annotation"]["segment"] == ammeter.annotation_gt.value

    assert voltmeter.scene_id == "analog_meter"
    assert voltmeter.query_id == "voltmeter_readout"
    assert voltmeter.answer_gt.type == "integer"
    assert voltmeter.answer_gt.value == 11
    assert voltmeter.trace_payload["execution_trace"]["unit"] == "V"
    assert voltmeter.trace_payload["render_map"]["scale_max"] == 12
    assert voltmeter.annotation_gt.value == voltmeter.trace_payload["render_map"]["needle_segment_px"]
    _assert_segment_in_bounds(voltmeter)


def test_physics_piston_cylinder_boundary_work_contracts() -> None:
    task = PhysicsPistonCylinderBoundaryWorkValueTask()
    expansion = task.generate(
        80297,
        params={
            "orientation": "vertical_pair",
            "pressure_mpa": 3,
            "initial_volume_l": 2,
            "final_volume_l": 6,
        },
        max_attempts=20,
    )
    compression = task.generate(
        80299,
        params={
            "orientation": "horizontal_pair",
            "pressure_mpa": 4,
            "initial_volume_l": 7,
            "final_volume_l": 3,
        },
        max_attempts=20,
    )
    vertical_compression = task.generate(
        80301,
        params={
            "orientation": "vertical_pair",
            "pressure_mpa": 6,
            "initial_volume_l": 7,
            "final_volume_l": 2,
        },
        max_attempts=20,
    )

    assert expansion.scene_id == "piston_cylinder"
    assert expansion.query_id == "single"
    assert expansion.answer_gt.type == "integer"
    assert expansion.answer_gt.value == 12
    assert expansion.trace_payload["execution_trace"]["delta_volume_l"] == 4
    assert expansion.trace_payload["render_map"]["boundary_work_kj"] == 12
    assert set(expansion.annotation_gt.value) == {
        "pressure_readout",
        "initial_cylinder",
        "final_cylinder",
    }
    _assert_bbox_map_in_bounds(expansion)
    assert expansion.trace_payload["projected_annotation"]["bbox_map"] == expansion.annotation_gt.value
    assert expansion.annotation_gt.value["pressure_readout"] == expansion.trace_payload["render_map"]["pressure_label_bbox_px"]
    assert expansion.annotation_gt.value["initial_cylinder"] == expansion.trace_payload["render_map"]["initial_cylinder_bbox_px"]
    assert expansion.annotation_gt.value["final_cylinder"] == expansion.trace_payload["render_map"]["final_cylinder_bbox_px"]

    assert compression.answer_gt.type == "integer"
    assert compression.answer_gt.value == -16
    assert compression.trace_payload["execution_trace"]["delta_volume_l"] == -4
    assert compression.trace_payload["render_map"]["pressure_mpa"] == 4
    assert compression.trace_payload["render_map"]["initial_volume_l"] == 7
    assert compression.trace_payload["render_map"]["final_volume_l"] == 3
    _assert_bbox_map_in_bounds(compression)

    assert vertical_compression.answer_gt.value == -30
    assert vertical_compression.trace_payload["render_map"]["initial_volume_l"] == 7
    assert vertical_compression.trace_payload["render_map"]["final_volume_l"] == 2
    _assert_bbox_map_in_bounds(vertical_compression)


def test_physics_thermometer_temperature_conversion_contracts() -> None:
    task = PhysicsThermometerTemperatureConversionValueTask()
    celsius_to_fahrenheit = task.generate(
        80300,
        params={
            "query_id": "celsius_to_fahrenheit_value",
            "scale_profile": "celsius_weather",
            "source_temperature": 25,
        },
        max_attempts=20,
    )
    fahrenheit_to_celsius = task.generate(
        80302,
        params={
            "query_id": "fahrenheit_to_celsius_value",
            "scale_profile": "fahrenheit_weather",
            "source_temperature": 68,
        },
        max_attempts=20,
    )

    assert celsius_to_fahrenheit.scene_id == "thermometer"
    assert celsius_to_fahrenheit.query_id == "celsius_to_fahrenheit_value"
    assert celsius_to_fahrenheit.answer_gt.type == "integer"
    assert celsius_to_fahrenheit.answer_gt.value == 77
    assert celsius_to_fahrenheit.trace_payload["execution_trace"]["source_unit"] == "C"
    assert celsius_to_fahrenheit.trace_payload["execution_trace"]["target_unit"] == "F"
    assert celsius_to_fahrenheit.trace_payload["render_map"]["source_temperature"] == 25
    assert celsius_to_fahrenheit.trace_payload["render_map"]["target_temperature"] == 77
    assert celsius_to_fahrenheit.annotation_gt.type == "segment"
    assert celsius_to_fahrenheit.annotation_gt.value == celsius_to_fahrenheit.trace_payload["render_map"]["liquid_level_segment_px"]
    _assert_segment_in_bounds(celsius_to_fahrenheit)
    assert celsius_to_fahrenheit.trace_payload["projected_annotation"]["segment"] == celsius_to_fahrenheit.annotation_gt.value
    assert celsius_to_fahrenheit.trace_payload["render_map"]["annotation_source"] == "liquid_level_segment_px"
    assert "scale_region" in celsius_to_fahrenheit.trace_payload["render_map"]["context_bbox_map_px"]

    assert fahrenheit_to_celsius.scene_id == "thermometer"
    assert fahrenheit_to_celsius.query_id == "fahrenheit_to_celsius_value"
    assert fahrenheit_to_celsius.answer_gt.type == "integer"
    assert fahrenheit_to_celsius.answer_gt.value == 20
    assert fahrenheit_to_celsius.trace_payload["execution_trace"]["source_unit"] == "F"
    assert fahrenheit_to_celsius.trace_payload["execution_trace"]["target_unit"] == "C"
    assert fahrenheit_to_celsius.trace_payload["render_map"]["scale_profile"]["scale_min"] == 20
    assert fahrenheit_to_celsius.annotation_gt.type == "segment"
    assert fahrenheit_to_celsius.annotation_gt.value == fahrenheit_to_celsius.trace_payload["render_map"]["liquid_level_segment_px"]
    _assert_segment_in_bounds(fahrenheit_to_celsius)
    assert fahrenheit_to_celsius.trace_payload["projected_annotation"]["segment"] == fahrenheit_to_celsius.annotation_gt.value


def test_physics_thermal_mixing_final_temperature_contract() -> None:
    out = PhysicsThermalMixingFinalTemperatureValueTask().generate(
        80303,
        params={"cup_count": 3, "target_answer": 40},
        max_attempts=20,
    )
    execution = out.trace_payload["execution_trace"]
    temperatures = [int(value) for value in execution["initial_temperatures_c"]]

    assert out.scene_id == "thermal_mixing"
    assert out.query_id == "single"
    assert execution["internal_query_id"] == "equal_amount_final_temperature"
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == 40
    assert len(temperatures) == 3
    assert sum(temperatures) % len(temperatures) == 0
    assert sum(temperatures) // len(temperatures) == out.answer_gt.value
    assert out.annotation_gt.type == "bbox_set"
    assert len(out.annotation_gt.value) == 3
    _assert_bbox_set_in_bounds(out)
    assert out.trace_payload["projected_annotation"]["bboxes"] == out.annotation_gt.value


def test_physics_vernier_caliper_length_readout_contract() -> None:
    out = PhysicsVernierCaliperLengthReadoutValueTask().generate(
        80304,
        params={"main_mm": 23, "aligned_vernier_tick": 4, "correct_option_letter": "D"},
        max_attempts=20,
    )
    execution = out.trace_payload["execution_trace"]
    render_map = out.trace_payload["render_map"]

    assert out.scene_id == "vernier_caliper"
    assert out.query_id == "single"
    assert out.answer_gt.type == "option_letter"
    assert out.answer_gt.value == "D"
    assert execution["main_mm"] == 23
    assert execution["aligned_vernier_tick"] == 4
    assert math.isclose(float(execution["target_readout_mm"]), 23.4, abs_tol=1e-9)
    assert execution["target_answer"] == "D"
    assert execution["correct_option_letter"] == "D"
    assert math.isclose(float(render_map["answer_mm"]), 23.4, abs_tol=1e-9)
    assert math.isclose(float(render_map["option_values_mm"]["D"]), 23.4, abs_tol=1e-9)
    assert render_map["correct_option_letter"] == "D"
    assert set(render_map["option_bboxes_px"]) == {"A", "B", "C", "D", "E", "F"}
    assert render_map["nearest_aligned_main_tick"] == 27
    sampling_axes = extract_sampling_axes(out)
    assert sampling_axes["aligned_vernier_tick"]["observed"] == "4"
    assert sampling_axes["correct_option_letter"]["observed"] == "D"
    assert "aligned_tick" not in sampling_axes
    assert render_map["main_scale_max_mm"] == 62
    assert render_map["annotation_source"] == "selected_option_bbox_px"
    assert set(render_map["readout_witness_point_map_px"]) == {
        "vernier_zero_tick",
        "aligned_vernier_tick",
    }
    assert out.annotation_gt.type == "bbox"
    assert out.annotation_gt.value == render_map["correct_option_bbox_px"]
    _assert_bbox_in_bounds(out)
    assert set(render_map["context_bbox_map_px"]) == {
        "main_scale_region",
        "vernier_zero",
        "vernier_scale_region",
        "aligned_vernier_tick",
    }
    assert out.trace_payload["projected_annotation"]["bbox"] == out.annotation_gt.value
    assert out.prompt_variants["answer_only"]
    assert out.prompt_variants["answer_and_annotation"]


def test_physics_wire_magnetism_contract() -> None:
    out = PhysicsWireMagnetismFieldDirectionChoiceTask().generate(
        80301,
        params={"current_direction": "out_of_page", "point_position": "east", "target_label": "B"},
        max_attempts=20,
    )
    execution = out.trace_payload["execution_trace"]

    assert out.scene_id == "wire_magnetism"
    assert out.query_id == "single"
    assert execution["internal_query_id"] == "perpendicular_wire_field_direction_at_point"
    assert out.answer_gt.type == "option_letter"
    assert out.answer_gt.value == "B"
    assert out.annotation_gt.type == "bbox_map"
    assert set(out.annotation_gt.value) == {"wire_current", "point_p"}
    assert execution["current_direction"] == "out_of_page"
    assert execution["point_position"] == "east"
    assert execution["field_direction"] == "north"
    assert set(execution["answer_option_labels"]) == {"A", "B", "C", "D"}
    assert set(execution["option_map"].values()) == {"north", "south", "east", "west"}
    assert execution["option_map"][out.answer_gt.value] == execution["field_direction"]
    assert out.annotation_gt.value["wire_current"] not in out.trace_payload["render_map"]["option_bboxes"].values()
    _assert_bbox_map_in_bounds(out)


def test_physics_refraction_layers_speed_order_contract() -> None:
    out = PhysicsRefractionLayersMediumSpeedOrderLabelTask().generate(
        80401,
        params={"layer_orientation": "horizontal", "speed_order": ["M2", "M1", "M3"]},
        max_attempts=20,
    )
    execution = out.trace_payload["execution_trace"]
    render_map = out.trace_payload["render_map"]
    expected_options = {" > ".join(order) for order in itertools.permutations(("M1", "M2", "M3"))}

    assert out.scene_id == "refraction_layers"
    assert out.query_id == "single"
    assert out.answer_gt.type == "option_letter"
    assert out.annotation_gt.type == "bbox_set"
    assert len(out.annotation_gt.value) == 2
    _assert_bbox_set_in_bounds(out)
    assert set(execution["option_map"].values()) == expected_options
    assert execution["internal_query_id"] == "three_medium_speed_order"
    assert execution["option_map"][out.answer_gt.value] == " > ".join(execution["speed_order"])
    assert render_map["correct_label"] == out.answer_gt.value
    assert render_map["speed_order"] == ["M2", "M1", "M3"]
    assert out.trace_payload["projected_annotation"]["bbox_set"] == out.annotation_gt.value

    speeds = execution["medium_speeds"]
    angles = execution["angle_by_medium_deg"]
    for faster, slower in zip(execution["speed_order"], execution["speed_order"][1:]):
        assert speeds[faster] > speeds[slower]
        assert angles[faster] > angles[slower]
    for medium, angle in zip(render_map["segment_mediums"], render_map["segment_angles_deg"]):
        assert math.isclose(float(angle), float(angles[medium]), abs_tol=1e-3)


def test_physics_shadow_cause_light_source_contract() -> None:
    out = PhysicsShadowCauseLightSourceLabelTask().generate(
        80441,
        params={
            "shadow_direction": "southeast",
            "correct_option_letter": "C",
            "object_shape": "block",
        },
        max_attempts=20,
    )
    execution = out.trace_payload["execution_trace"]
    render_map = out.trace_payload["render_map"]

    assert out.scene_id == "shadow_cause"
    assert out.query_id == "single"
    assert out.answer_gt.type == "option_letter"
    assert out.answer_gt.value == "C"
    assert out.annotation_gt.type == "bbox"
    _assert_bbox_in_bounds(out)
    assert execution["query_id"] == "single"
    assert execution["internal_query_id"] == "source_from_shadow_label"
    assert execution["shadow_direction"] == "southeast"
    assert execution["source_direction"] == "northwest"
    assert execution["candidate_directions"][out.answer_gt.value] == "northwest"
    assert render_map["correct_option_letter"] == out.answer_gt.value
    assert render_map["candidate_directions"][out.answer_gt.value] == render_map["source_direction"]
    assert out.annotation_gt.value == render_map["candidate_light_sources"][out.answer_gt.value]["option_bbox_px"]
    assert out.trace_payload["projected_annotation"]["bbox"] == out.annotation_gt.value
    assert out.annotation_gt.value not in [
        record["option_bbox_px"]
        for label, record in render_map["candidate_light_sources"].items()
        if label != out.answer_gt.value
    ]


def test_physics_lens_optics_image_property_contract() -> None:
    out = PhysicsLensOpticsImagePropertyChoiceTask().generate(
        80471,
        params={
            "object_position_case": "between_f_2f",
            "correct_option_letter": "D",
            "post_image_noise": {"enabled": False},
        },
        max_attempts=20,
    )
    execution = out.trace_payload["execution_trace"]
    render_map = out.trace_payload["render_map"]

    assert out.scene_id == "lens_optics"
    assert out.query_id == "single"
    assert out.answer_gt.type == "option_letter"
    assert out.answer_gt.value == "D"
    assert execution["lens_type"] == "converging"
    assert execution["internal_query_id"] == "converging_lens_image_property_choice"
    assert execution["object_position_case"] == "between_f_2f"
    assert execution["option_map"][out.answer_gt.value] == "real_inverted_larger"
    assert set(out.annotation_gt.value) == {"lens", "object_arrow", "focal_marks"}
    _assert_bbox_map_in_bounds(out)
    assert render_map["correct_option_letter"] == out.answer_gt.value
    assert render_map["image_property"] == "real_inverted_larger"
    assert out.trace_payload["projected_annotation"]["bbox_map"] == out.annotation_gt.value
    assert "image_arrow_bbox_px" not in render_map
    for option_bbox in render_map["option_bboxes_px"].values():
        assert option_bbox not in out.annotation_gt.value.values()


def test_physics_bulb_circuit_brightness_contract() -> None:
    out = PhysicsBulbCircuitBrightnessExtremumLabelTask().generate(
        80501,
        params={
            "scene_variant": "mixed_branch",
            "query_id": "brightest_bulb_label",
            "target_label": "B3",
            "resistance_values": [3, 8, 2, 5, 10],
        },
        max_attempts=20,
    )
    execution = out.trace_payload["execution_trace"]
    powers = {str(spec["label"]): float(spec["relative_power"]) for spec in execution["bulb_specs"]}

    assert out.scene_id == "bulb_circuit"
    assert out.query_id == "brightest_bulb_label"
    assert out.answer_gt.type == "string"
    assert out.answer_gt.value == max(powers, key=powers.get)
    assert out.answer_gt.value == "B3"
    assert out.annotation_gt.value == out.trace_payload["render_map"]["bulb_bboxes"]["B3"]
    _assert_bbox_in_bounds(out)
    assert out.trace_payload["projected_annotation"]["bbox"] == out.annotation_gt.value


def test_physics_switch_circuit_lit_bulb_count_contract() -> None:
    out = PhysicsSwitchCircuitLitBulbCountTask().generate(
        80541,
        params={
            "target_answer": 3,
            "switch_states": {
                "S1": "closed",
                "S2": "closed",
                "S3": "open",
                "S4": "closed",
                "S5": "open",
            },
        },
        max_attempts=20,
    )
    execution = out.trace_payload["execution_trace"]
    render_map = out.trace_payload["render_map"]

    assert out.scene_id == "switch_circuit"
    assert out.query_id == "single"
    assert execution["internal_query_id"] == "lit_bulb_count"
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == 3
    assert out.annotation_gt.type == "bbox_set"
    assert execution["lit_bulbs"] == ["B1", "B2", "B4"]
    assert len(out.annotation_gt.value) == int(out.answer_gt.value)
    assert out.annotation_gt.value == [
        render_map["bulb_bboxes"]["B1"],
        render_map["bulb_bboxes"]["B2"],
        render_map["bulb_bboxes"]["B4"],
    ]
    _assert_bbox_set_in_bounds(out)
    assert out.trace_payload["projected_annotation"]["bbox_set"] == out.annotation_gt.value


def test_physics_circuit_state_change_bulb_brightness_contract() -> None:
    out = PhysicsCircuitStateChangeBulbBrightnessLabelTask().generate(
        80561,
        params={
            "query_id": "brightens_after_switch_change",
            "switch_action": "closes",
            "target_label": "B2",
            "resistance_values": {
                "series_bulb": 5,
                "main_branch_bulb": 3,
                "switched_branch_bulb": 8,
                "reference_branch_bulb_1": 4,
                "reference_branch_bulb_2": 10,
            },
        },
        max_attempts=20,
    )
    execution = out.trace_payload["execution_trace"]
    matches = [spec for spec in execution["bulb_specs"] if str(spec["change_class"]) == "brightens"]

    assert out.scene_id == "circuit_state_change"
    assert out.query_id == "brightens_after_switch_change"
    assert out.answer_gt.type == "string"
    assert out.answer_gt.value == "B2"
    assert len(matches) == 1
    assert str(matches[0]["label"]) == out.answer_gt.value
    assert out.annotation_gt.type == "bbox_map"
    assert set(out.annotation_gt.value) == {"changed_switch", "B1", "B2", "B3", "B4", "B5"}
    _assert_bbox_map_in_bounds(out)
    assert out.trace_payload["projected_annotation"]["bbox_map"] == out.annotation_gt.value


def test_physics_bridge_circuit_missing_resistance_contract() -> None:
    out = PhysicsBridgeCircuitMissingResistanceValueTask().generate(
        80601,
        params={
            "missing_resistor": "R4",
            "target_answer": 7,
        },
        max_attempts=20,
    )
    execution = out.trace_payload["execution_trace"]
    values = {str(key): int(value) for key, value in execution["resistor_values"].items()}

    assert out.scene_id == "bridge_circuit"
    assert out.query_id == "single"
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == values["R4"] == 7
    assert values["R1"] * values["R4"] == values["R2"] * values["R3"]
    assert out.annotation_gt.type == "bbox"
    assert out.annotation_gt.value == out.trace_payload["render_map"]["annotation_bbox_map"]["target_resistor"]
    _assert_bbox_in_bounds(out)
    assert out.trace_payload["projected_annotation"]["bbox"] == out.annotation_gt.value


def test_physics_motion_graph_contract() -> None:
    out = PhysicsMotionGraphSpeedChangeStateChoiceTask().generate(
        80701,
        params={
            "motion_state": "slowing_down",
            "correct_option_letter": "B",
        },
        max_attempts=20,
    )
    execution = out.trace_payload["execution_trace"]
    segment = execution["target_segment"]

    assert out.scene_id == "motion_graph"
    assert out.query_id == "single"
    assert out.answer_gt.type == "option_letter"
    assert out.answer_gt.value == "B"
    _assert_segment_in_bounds(out)
    assert out.annotation_gt.value == out.trace_payload["render_map"]["curve_segment_px"]
    assert out.trace_payload["projected_annotation"]["segment"] == out.annotation_gt.value
    assert execution["motion_operation"] == "speed_change_state_choice"
    assert execution["graph_kind"] == "velocity_time"
    assert execution["option_map"][out.answer_gt.value] == "slowing_down"
    assert abs(int(segment["y_end"])) < abs(int(segment["y_start"]))


def test_physics_motion_graph_average_speed_contract() -> None:
    out = PhysicsMotionGraphAverageSpeedValueTask().generate(
        80705,
        params={
            "t_start": 1,
            "t_end": 3,
            "d_start": 2,
            "d_end": 12,
            "post_image_noise": {"enabled": False},
        },
        max_attempts=20,
    )
    execution = out.trace_payload["execution_trace"]

    assert out.scene_id == "motion_graph"
    assert out.query_id == "single"
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == 5
    _assert_segment_in_bounds(out)
    assert out.annotation_gt.value == out.trace_payload["render_map"]["distance_segment_px"]
    assert out.trace_payload["projected_annotation"]["segment"] == out.annotation_gt.value
    assert execution["graph_kind"] == "distance_time"
    assert execution["delta_d_m"] == 10
    assert execution["delta_t_s"] == 2
    assert execution["average_speed_m_s"] == out.answer_gt.value


def test_physics_motion_graph_interval_displacement_contract() -> None:
    out = PhysicsMotionGraphIntervalDisplacementValueTask().generate(
        80711,
        params={
            "query_id": "constant_acceleration_interval_displacement",
            "t_start": 2,
            "t_end": 6,
            "v_start": 2,
            "v_end": 6,
            "post_image_noise": {"enabled": False},
        },
        max_attempts=20,
    )
    execution = out.trace_payload["execution_trace"]

    assert out.scene_id == "motion_graph"
    assert out.query_id == "constant_acceleration_interval_displacement"
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == 16
    _assert_segment_in_bounds(out)
    assert out.annotation_gt.value == out.trace_payload["render_map"]["velocity_segment_px"]
    assert out.trace_payload["projected_annotation"]["segment"] == out.annotation_gt.value
    assert execution["displacement_m"] == out.answer_gt.value
    assert execution["velocity_values_m_s"][2:7] == [2, 3, 4, 5, 6]


def test_physics_stack_stability_contract() -> None:
    out = PhysicsStackStabilityStatusLabelTask().generate(
        80731,
        params={
            "query_id": "tipping_stack_label",
            "correct_option_letter": "E",
        },
        max_attempts=20,
    )
    render_map = out.trace_payload["render_map"]
    statuses = render_map["candidate_statuses"]
    selected_label = str(out.answer_gt.value)
    selected_com_x = float(render_map["candidate_com_points_px"][selected_label][0])
    selected_support = render_map["candidate_support_bboxes_px"][selected_label]

    assert out.scene_id == "stack_stability"
    assert out.query_id == "tipping_stack_label"
    assert out.answer_gt.type == "option_letter"
    assert out.answer_gt.value == "E"
    assert out.annotation_gt.type == "bbox"
    assert list(statuses.values()).count("tipping") == 1
    assert statuses["E"] == "tipping"
    assert selected_com_x < float(selected_support[0]) or selected_com_x > float(selected_support[2])
    _assert_bbox_in_bounds(out)
    assert render_map["annotation_bbox_px"] == out.annotation_gt.value


def test_physics_free_body_forces_contract() -> None:
    out = PhysicsFreeBodyForcesNetForceDirectionChoiceTask().generate(
        80751,
        params={
            "scene_variant": "gridded_table",
            "net_force_direction": "northeast",
            "correct_option_letter": "D",
            "force_specs": [
                {"direction": "east", "magnitude_n": 9},
                {"direction": "west", "magnitude_n": 3},
                {"direction": "north", "magnitude_n": 12},
                {"direction": "south", "magnitude_n": 6},
            ],
            "post_image_noise": {"enabled": False},
        },
        max_attempts=20,
    )
    trace = out.trace_payload

    assert out.scene_id == "free_body_forces"
    assert out.query_id == "single"
    assert out.answer_gt.type == "option_letter"
    assert out.answer_gt.value == "D"
    assert out.annotation_gt.type == "bbox_map"
    assert set(out.annotation_gt.value) == {"force_diagram", "selected_candidate"}
    _assert_bbox_map_in_bounds(out)
    assert trace["projected_annotation"]["bbox_map"] == out.annotation_gt.value
    assert out.annotation_gt.value == trace["render_map"]["annotation_bbox_map_px"]
    assert trace["execution_trace"]["resultant_vector"] == [6, 6]
    assert trace["execution_trace"]["option_directions"]["D"] == "northeast"


def test_physics_waveform_panel_contract() -> None:
    out = PhysicsWaveformPanelWavePropertyExtremumLabelTask().generate(
        80851,
        params={
            "query_id": "longest_wavelength_label",
            "panel_count": 6,
            "target_label": "D",
        },
        max_attempts=20,
    )
    execution = out.trace_payload["execution_trace"]
    selected = next(panel for panel in execution["panels"] if str(panel["label"]) == "D")

    assert out.scene_id == "waveform_panel"
    assert out.query_id == "longest_wavelength_label"
    assert out.answer_gt.type == "option_letter"
    assert out.answer_gt.value == "D"
    assert out.annotation_gt.type == "bbox"
    assert out.annotation_gt.value == selected["bbox_px"]
    assert int(selected["cycle_count"]) == min(int(panel["cycle_count"]) for panel in execution["panels"])
    assert out.trace_payload["projected_annotation"]["bbox"] == out.annotation_gt.value
    for panel in execution["panels"]:
        panel_box = panel["bbox_px"]
        label_box = panel["label_bbox_px"]
        panel_mid_y = (float(panel_box[1]) + float(panel_box[3])) / 2.0
        assert float(label_box[0]) <= float(panel_box[0]) + 40.0
        assert float(label_box[1]) < panel_mid_y
        assert float(label_box[3]) < panel_mid_y


def test_physics_signal_transform_contracts() -> None:
    periodic = PhysicsSignalTransformPeriodicHarmonicSpectrumMatchLabelTask().generate(
        80883,
        params={
            "waveform_family": "triangle_wave",
            "correct_option_letter": "B",
        },
        max_attempts=20,
    )
    assert periodic.scene_id == "signal_transform"
    assert periodic.query_id == "single"
    assert periodic.answer_gt.type == "option_letter"
    assert periodic.answer_gt.value == "B"
    assert periodic.annotation_gt.type == "bbox_map"
    assert set(periodic.annotation_gt.value) == {"input_waveform", "selected_spectrum"}
    assert set(periodic.trace_payload["execution_trace"]["answer_option_labels"]) == {"A", "B", "C", "D"}
    assert set(periodic.trace_payload["execution_trace"]["option_map"]) == {"A", "B", "C", "D"}
    assert periodic.trace_payload["execution_trace"]["internal_query_id"] == "periodic_wave_harmonic_spectrum"
    assert periodic.trace_payload["execution_trace"]["waveform_family"] == "triangle_wave"
    assert periodic.trace_payload["execution_trace"]["correct_spectrum"]["signature"] == "odd_harmonics_fast"
    assert periodic.trace_payload["execution_trace"]["correct_spectrum"]["bins"] == [1, 3, 5, 7]
    assert periodic.trace_payload["execution_trace"]["option_map"]["B"] == periodic.trace_payload["execution_trace"]["correct_spectrum"]
    assert periodic.trace_payload["render_map"]["option_bboxes"]["B"] == periodic.annotation_gt.value["selected_spectrum"]
    _assert_bbox_map_in_bounds(periodic)


def test_physics_extension_defaults_expose_prompt_and_rendering_contracts() -> None:
    stack_stability = get_scene_defaults("physics", "stack_stability")
    switch_circuit = get_scene_defaults("physics", "switch_circuit")
    manometer = get_scene_defaults("physics", "manometer")
    wire_magnetism = get_scene_defaults("physics", "wire_magnetism")
    induction_scene = get_scene_defaults("physics", "electromagnetic_induction")
    electrostatic_scene = get_scene_defaults("physics", "electrostatic_field")
    shadow_scene = get_scene_defaults("physics", "shadow_cause")
    wave_interference = get_scene_defaults("physics", "wave_interference")
    waveform_panel = get_scene_defaults("physics", "waveform_panel")
    vernier_caliper = get_scene_defaults("physics", "vernier_caliper")

    orbital_scene = get_scene_defaults("physics", "orbital_motion")
    orbital_generation, orbital_rendering, orbital_prompt = split_generation_rendering_prompt_defaults(
        orbital_scene,
        task_id="task_physics__orbital_motion__focus_location_label",
    )
    assert "query_id_weights" not in orbital_generation
    assert int(orbital_rendering["canvas_width"]) == 1040
    assert str(orbital_prompt["bundle_id"]) == "physics_orbital_motion_v1"
    assert str(orbital_prompt["task_key"]) == "orbital_motion_focus_location_label_query"

    cylinder_scene = get_scene_defaults("physics", "graduated_cylinder")
    cylinder_generation, cylinder_rendering, cylinder_prompt = split_generation_rendering_prompt_defaults(
        cylinder_scene,
        task_id="task_physics__graduated_cylinder__displacement_volume_value",
    )
    assert "query_id_weights" not in cylinder_generation
    assert int(cylinder_rendering["canvas_height"]) == 720
    assert str(cylinder_prompt["bundle_id"]) == "physics_graduated_cylinder_v1"
    assert str(cylinder_prompt["task_key"]) == "displacement_volume_value_query"

    buoyancy_scene = get_scene_defaults("physics", "buoyancy_density")
    buoyancy_generation, buoyancy_rendering, buoyancy_prompt = split_generation_rendering_prompt_defaults(
        buoyancy_scene,
        task_id="task_physics__buoyancy_density__object_density_value",
    )
    assert "query_id_weights" not in buoyancy_generation
    assert set(buoyancy_generation["scene_variant_weights"]) == {"rectangular_tank", "beaker_tank", "wide_tank"}
    assert set(buoyancy_generation["object_shape_weights"]) == {"block", "rounded_block"}
    assert int(buoyancy_rendering["canvas_height"]) == 720
    assert str(buoyancy_prompt["bundle_id"]) == "physics_buoyancy_density_v1"
    assert str(buoyancy_prompt["task_key"]) == "object_density_value_query"

    manometer_generation, manometer_rendering, manometer_prompt = split_generation_rendering_prompt_defaults(
        manometer,
        task_id="task_physics__manometer__pressure_difference_value",
    )
    assert "query_id_weights" not in manometer_generation
    assert set(manometer_generation["height_cm_support"]) == set(range(2, 13))
    assert set(manometer_generation["kpa_per_cm_support"]) == {1, 2, 3, 4, 5}
    assert int(manometer_rendering["canvas_height"]) == 720
    assert str(manometer_prompt["bundle_id"]) == "physics_manometer_v1"
    assert str(manometer_prompt["task_key"]) == "pressure_difference_value_query"

    fluid_flow = get_scene_defaults("physics", "fluid_flow")
    flow_generation, flow_rendering, flow_prompt = split_generation_rendering_prompt_defaults(
        fluid_flow,
        task_id="task_physics__fluid_flow__continuity_speed_value",
    )
    assert "query_id_weights" not in flow_generation
    assert set(flow_generation["orientation_weights"]) == {"horizontal_pipe", "vertical_pipe"}
    assert set(flow_generation["area_cm2_support"]) == {2, 3, 4, 5, 6, 8, 9, 10, 12}
    assert int(flow_rendering["canvas_height"]) == 720
    assert str(flow_prompt["bundle_id"]) == "physics_fluid_flow_v1"
    assert str(flow_prompt["task_key"]) == "continuity_speed_value_query"

    wire_generation, wire_rendering, wire_prompt = split_generation_rendering_prompt_defaults(
        wire_magnetism,
        task_id="task_physics__wire_magnetism__wire_field_direction_choice",
    )
    assert "query_id_weights" not in wire_generation
    assert "balanced_query_id_sampling" not in wire_generation
    assert set(wire_generation["current_direction_weights"]) == {"out_of_page", "into_page"}
    assert set(wire_generation["point_position_weights"]) == {"north", "south", "east", "west"}
    assert int(wire_rendering["canvas_width"]) == 1080
    assert str(wire_prompt["bundle_id"]) == "physics_wire_magnetism_v1"
    assert str(wire_prompt["task_key"]) == "wire_field_direction_choice_query"

    induction_generation, induction_rendering, induction_prompt = split_generation_rendering_prompt_defaults(
        induction_scene,
        task_id="task_physics__electromagnetic_induction__induced_current_direction_count",
    )
    assert "query_id_weights" not in induction_generation
    assert set(induction_generation["target_answer_support"]) == set(range(7))
    assert int(induction_rendering["canvas_width"]) == 1180
    assert str(induction_prompt["bundle_id"]) == "physics_electromagnetic_induction_v1"
    assert str(induction_prompt["task_key"]) == "induced_current_direction_count_query"

    electrostatic_generation, electrostatic_rendering, electrostatic_prompt = split_generation_rendering_prompt_defaults(
        electrostatic_scene,
        task_id="task_physics__electrostatic_field__field_direction_choice",
    )
    assert "query_id_weights" not in electrostatic_generation
    assert set(electrostatic_generation["scene_variant_weights"]) == {"clean_grid", "paper_grid", "dense_grid"}
    assert "direction_mode_weights" not in electrostatic_generation
    assert "balanced_direction_mode_sampling" not in electrostatic_generation
    assert int(electrostatic_rendering["canvas_width"]) == 1180
    assert str(electrostatic_prompt["bundle_id"]) == "physics_electrostatic_field_v1"
    assert str(electrostatic_prompt["task_key"]) == "field_direction_choice_query"

    refraction_scene = get_scene_defaults("physics", "refraction_layers")
    refraction_generation, refraction_rendering, refraction_prompt = split_generation_rendering_prompt_defaults(
        refraction_scene,
        task_id="task_physics__refraction_layers__medium_speed_order_label",
    )
    assert "query_id_weights" not in refraction_generation
    assert set(refraction_generation["layer_orientation_weights"]) == {"horizontal", "vertical"}
    assert int(refraction_rendering["canvas_width"]) == 1080
    assert str(refraction_prompt["bundle_id"]) == "physics_refraction_layers_v1"
    assert str(refraction_prompt["task_key"]) == "refraction_speed_order_query"

    shadow_generation, shadow_rendering, shadow_prompt = split_generation_rendering_prompt_defaults(
        shadow_scene,
        task_id="task_physics__shadow_cause__light_source_label",
    )
    assert "query_id_weights" not in shadow_generation
    assert set(shadow_generation["correct_option_letter_weights"]) == {"A", "B", "C", "D", "E", "F"}
    assert set(shadow_generation["shadow_direction_weights"]) == {
        "east",
        "northeast",
        "north",
        "northwest",
        "west",
        "southwest",
        "south",
        "southeast",
    }
    assert set(shadow_generation["object_shape_weights"]) == {"block", "cylinder", "sphere"}
    assert int(shadow_rendering["canvas_width"]) == 1120
    assert str(shadow_prompt["bundle_id"]) == "physics_shadow_cause_v1"
    assert str(shadow_prompt["task_key"]) == "shadow_cause_query"

    lens_cfg = get_scene_defaults("physics", "lens_optics")
    lens_generation, lens_rendering, lens_prompt = split_generation_rendering_prompt_defaults(
        lens_cfg,
        task_id="task_physics__lens_optics__image_property_choice",
    )
    assert set(lens_generation["scene_variant_weights"]) == {"clean_axis", "paper_grid", "lab_card"}
    assert set(lens_generation["object_position_case_weights"]) == {
        "beyond_2f",
        "at_2f",
        "between_f_2f",
        "inside_f",
    }
    assert set(lens_generation["correct_option_letter_weights"]) == {"A", "B", "C", "D"}
    assert int(lens_rendering["canvas_width"]) == 1120
    assert str(lens_prompt["bundle_id"]) == "physics_lens_optics_v1"
    assert str(lens_prompt["task_key"]) == "lens_image_property_query"

    bulb_scene = get_scene_defaults("physics", "bulb_circuit")
    bulb_generation, bulb_rendering, bulb_prompt = split_generation_rendering_prompt_defaults(
        bulb_scene,
        task_id="task_physics__bulb_circuit__brightness_extremum_label",
    )
    assert set(bulb_generation["scene_variant_weights"]) == {"series_unequal", "parallel_unequal", "mixed_branch"}
    assert int(bulb_rendering["canvas_width"]) == 1280
    assert str(bulb_prompt["bundle_id"]) == "physics_bulb_circuit_v1"
    assert str(bulb_prompt["task_key"]) == "brightness_extremum_query"

    switch_generation, switch_rendering, switch_prompt = split_generation_rendering_prompt_defaults(
        switch_circuit,
        task_id="task_physics__switch_circuit__lit_bulb_count",
    )
    assert "query_id_weights" not in switch_generation
    assert "balanced_query_id_sampling" not in switch_generation
    assert set(switch_generation["scene_variant_weights"]) == {"mixed_branch"}
    assert list(switch_generation["target_answer_support"]) == [0, 1, 2, 3, 4, 5]
    assert int(switch_rendering["canvas_width"]) == 1280
    assert str(switch_prompt["bundle_id"]) == "physics_switch_circuit_v1"
    assert str(switch_prompt["task_key"]) == "lit_bulb_count_query"

    state_scene = get_scene_defaults("physics", "circuit_state_change")
    state_generation, state_rendering, state_prompt = split_generation_rendering_prompt_defaults(
        state_scene,
        task_id="task_physics__circuit_state_change__bulb_brightness_change_label",
    )
    assert "query_id_weights" not in state_generation
    assert "balanced_query_id_sampling" not in state_generation
    assert list(state_generation["resistance_options"]) == [2, 3, 4, 5, 6, 8, 10, 12]
    assert int(state_rendering["canvas_width"]) == 1280
    assert str(state_prompt["bundle_id"]) == "physics_circuit_state_change_v1"
    assert str(state_prompt["task_key"]) == "bulb_brightness_change_query"

    bridge_circuit = get_scene_defaults("physics", "bridge_circuit")
    bridge_generation, bridge_rendering, bridge_prompt = split_generation_rendering_prompt_defaults(
        bridge_circuit,
        task_id="task_physics__bridge_circuit__bridge_missing_resistance_value",
    )
    assert "query_id_weights" not in bridge_generation
    assert "balanced_query_id_sampling" not in bridge_generation
    assert set(bridge_generation["missing_resistor_weights"]) == {"R1", "R2", "R3", "R4"}
    assert int(bridge_rendering["canvas_width"]) == 1280
    assert str(bridge_prompt["bundle_id"]) == "physics_bridge_circuit_v1"
    assert str(bridge_prompt["task_key"]) == "bridge_missing_resistance_query"

    analog_meter = get_scene_defaults("physics", "analog_meter")
    meter_generation, meter_rendering, meter_prompt = split_generation_rendering_prompt_defaults(
        analog_meter,
        task_id="task_physics__analog_meter__meter_readout_value",
    )
    assert "query_id_weights" not in meter_generation
    assert "balanced_query_id_sampling" not in meter_generation
    assert set(meter_generation["meter_profile_weights"]) == {"ammeter_a", "ammeter_ma", "voltmeter_v"}
    assert int(meter_rendering["canvas_height"]) == 720
    assert str(meter_prompt["bundle_id"]) == "physics_analog_meter_v1"
    assert str(meter_prompt["task_key"]) == "analog_meter_readout_query"

    piston_cylinder = get_scene_defaults("physics", "piston_cylinder")
    piston_generation, piston_rendering, piston_prompt = split_generation_rendering_prompt_defaults(
        piston_cylinder,
        task_id="task_physics__piston_cylinder__boundary_work_value",
    )
    assert "query_id_weights" not in piston_generation
    assert set(piston_generation["orientation_weights"]) == {"vertical_pair", "horizontal_pair"}
    assert set(piston_generation["pressure_mpa_support"]) == {1, 2, 3, 4, 5, 6}
    assert int(piston_rendering["canvas_height"]) == 740
    assert str(piston_prompt["bundle_id"]) == "physics_piston_cylinder_v1"
    assert str(piston_prompt["task_key"]) == "boundary_work_value_query"

    thermometer = get_scene_defaults("physics", "thermometer")
    thermometer_generation, thermometer_rendering, thermometer_prompt = split_generation_rendering_prompt_defaults(
        thermometer,
        task_id="task_physics__thermometer__temperature_conversion_value",
    )
    assert "query_id_weights" not in thermometer_generation
    assert "balanced_query_id_sampling" not in thermometer_generation
    assert set(thermometer_generation["scale_profile_weights"]) == {
        "celsius_weather",
        "celsius_lab",
        "fahrenheit_weather",
        "fahrenheit_compact",
    }
    assert int(thermometer_rendering["canvas_width"]) == 1100
    assert str(thermometer_prompt["bundle_id"]) == "physics_thermometer_v1"
    assert str(thermometer_prompt["task_key"]) == "temperature_conversion_query"

    thermal_mixing = get_scene_defaults("physics", "thermal_mixing")
    thermal_mixing_generation, thermal_mixing_rendering, thermal_mixing_prompt = split_generation_rendering_prompt_defaults(
        thermal_mixing,
        task_id="task_physics__thermal_mixing__final_temperature_value",
    )
    assert "query_id_weights" not in thermal_mixing_generation
    assert "balanced_query_id_sampling" not in thermal_mixing_generation
    assert set(str(key) for key in thermal_mixing_generation["cup_count_weights"]) == {"2", "3", "4"}
    assert set(thermal_mixing_generation["final_temperature_support"]) == {20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70}
    assert int(thermal_mixing_rendering["canvas_width"]) == 1180
    assert str(thermal_mixing_prompt["bundle_id"]) == "physics_thermal_mixing_v1"
    assert str(thermal_mixing_prompt["task_key"]) == "final_temperature_value_query"

    motion_graph = get_scene_defaults("physics", "motion_graph")
    motion_generation, motion_rendering, motion_prompt = split_generation_rendering_prompt_defaults(
        motion_graph,
        task_id="task_physics__motion_graph__speed_change_state_choice",
    )
    assert "query_id_weights" not in motion_generation
    assert "balanced_query_id_sampling" not in motion_generation
    assert set(motion_generation["motion_state_weights"]) == {"speeding_up", "slowing_down", "constant_speed"}
    assert set(motion_generation["correct_option_letter_weights"]) == {"A", "B", "C", "D"}
    assert int(motion_rendering["canvas_width"]) == 1120
    assert str(motion_prompt["bundle_id"]) == "physics_motion_graph_v1"
    assert str(motion_prompt["task_key"]) == "motion_graph_speed_change_state_choice_query"

    average_generation, average_rendering, average_prompt = split_generation_rendering_prompt_defaults(
        motion_graph,
        task_id="task_physics__motion_graph__average_speed_value",
    )
    assert "query_id_weights" not in average_generation
    assert "balanced_query_id_sampling" not in average_generation
    assert set(average_generation["average_speed_interval_width_support"]) == {1, 2}
    assert set(average_generation["average_speed_support"]) == {1, 2, 3, 4, 5, 6}
    assert int(average_rendering["canvas_width"]) == 1120
    assert int(average_rendering["y_min"]) == 0
    assert int(average_rendering["y_max"]) == 12
    assert str(average_prompt["bundle_id"]) == "physics_motion_graph_v1"
    assert str(average_prompt["task_key"]) == "motion_graph_average_speed_value_query"

    interval_generation, interval_rendering, interval_prompt = split_generation_rendering_prompt_defaults(
        motion_graph,
        task_id="task_physics__motion_graph__interval_displacement_value",
    )
    assert "query_id_weights" not in interval_generation
    assert "balanced_query_id_sampling" not in interval_generation
    assert set(interval_generation["scene_variant_weights"]) == {"clean_grid", "paper_grid", "bold_grid"}
    assert set(interval_generation["constant_acceleration_interval_width_support"]) == {2, 4}
    assert int(interval_rendering["canvas_width"]) == 1120
    assert int(interval_rendering["y_min"]) == 0
    assert str(interval_prompt["bundle_id"]) == "physics_motion_graph_v1"
    assert str(interval_prompt["task_key"]) == "motion_graph_interval_displacement_value_query"

    stack_generation, stack_rendering, stack_prompt = split_generation_rendering_prompt_defaults(
        stack_stability,
        task_id="task_physics__stack_stability__stability_status_label",
    )
    assert "query_id_weights" not in stack_generation
    assert "balanced_query_id_sampling" not in stack_generation
    assert set(stack_generation["correct_option_letter_weights"]) == {"A", "B", "C", "D", "E", "F"}
    assert int(stack_rendering["canvas_width"]) == 1180
    assert str(stack_prompt["bundle_id"]) == "physics_stack_stability_v1"
    assert str(stack_prompt["task_key"]) == "stack_stability_status_label_query"

    free_body_forces = get_scene_defaults("physics", "free_body_forces")
    free_body_generation, free_body_rendering, free_body_prompt = split_generation_rendering_prompt_defaults(
        free_body_forces,
        task_id="task_physics__free_body_forces__net_force_direction_choice",
    )
    assert "query_id_weights" not in free_body_generation
    assert set(free_body_generation["correct_option_letter_weights"]) == {"A", "B", "C", "D", "E", "F", "G", "H"}
    assert int(free_body_rendering["canvas_width"]) == 1180
    assert str(free_body_prompt["bundle_id"]) == "physics_free_body_forces_v1"
    assert str(free_body_prompt["task_key"]) == "net_force_direction_choice_query"

    gear_train = get_scene_defaults("physics", "gear_train")
    gear_generation, gear_rendering, gear_prompt = split_generation_rendering_prompt_defaults(
        gear_train,
        task_id="task_physics__gear_train__output_direction_label",
    )
    assert "query_id_weights" not in gear_generation
    assert set(gear_generation["scene_variant_weights"]) == {"straight_chain", "staggered_chain", "arc_chain"}
    assert set(gear_generation["gear_count_support"]) == {2, 3, 4}
    assert int(gear_rendering["direction_choice_canvas_width"]) == 1180
    assert int(gear_rendering["direction_choice_canvas_height"]) == 860
    assert str(gear_prompt["bundle_id"]) == "physics_gear_train_v1"
    assert str(gear_prompt["task_key"]) == "output_direction_label_query"

    gear_speed_generation, gear_speed_rendering, gear_speed_prompt = split_generation_rendering_prompt_defaults(
        gear_train,
        task_id="task_physics__gear_train__output_speed_value",
    )
    assert "query_id_weights" not in gear_speed_generation
    assert set(gear_speed_generation["scene_variant_weights"]) == {"straight_chain", "staggered_chain", "arc_chain"}
    assert set(gear_speed_generation["gear_count_support"]) == {2, 3, 4}
    assert set(gear_speed_generation["tooth_count_support"]) == {12, 16, 18, 20, 24, 30, 36, 40, 48}
    assert int(gear_speed_rendering["canvas_width"]) == 1040
    assert str(gear_speed_prompt["bundle_id"]) == "physics_gear_train_v1"
    assert str(gear_speed_prompt["task_key"]) == "output_speed_value_query"

    wave_choice_generation, wave_choice_rendering, wave_choice_prompt = split_generation_rendering_prompt_defaults(
        wave_interference,
        task_id="task_physics__wave_interference__interference_point_choice",
    )
    assert "query_id_weights" not in wave_choice_generation
    assert "balanced_query_id_sampling" not in wave_choice_generation
    assert set(wave_choice_generation["scene_variant_weights"]) == {"clean_tank", "grid_tank", "lab_sheet"}
    assert set(wave_choice_generation["phase_relation_weights"]) == {"in_phase", "opposite_phase"}
    assert set(wave_choice_generation["option_letter_weights"]) == {"A", "B", "C", "D", "E"}
    assert int(wave_choice_rendering["canvas_width"]) == 1180
    assert str(wave_choice_prompt["bundle_id"]) == "physics_wave_interference_v1"
    assert str(wave_choice_prompt["task_key"]) == "interference_point_choice_query"

    wave_path_generation, wave_path_rendering, wave_path_prompt = split_generation_rendering_prompt_defaults(
        wave_interference,
        task_id="task_physics__wave_interference__path_difference_value",
    )
    assert "query_id_weights" not in wave_path_generation
    assert "balanced_query_id_sampling" not in wave_path_generation
    assert set(wave_path_generation["path_difference_step_support"]) == {1, 2, 3, 4, 5}
    assert int(wave_path_rendering["canvas_width"]) == 1180
    assert str(wave_path_prompt["bundle_id"]) == "physics_wave_interference_v1"
    assert str(wave_path_prompt["task_key"]) == "path_difference_value_query"

    waveform_generation, waveform_rendering, waveform_prompt = split_generation_rendering_prompt_defaults(
        waveform_panel,
        task_id="task_physics__waveform_panel__wave_property_extremum_label",
    )
    assert "query_id_weights" not in waveform_generation
    assert "balanced_query_id_sampling" not in waveform_generation
    assert set(int(key) for key in waveform_generation["panel_count_weights"]) == {4, 5, 6}
    assert int(waveform_rendering["canvas_width"]) == 1180
    assert str(waveform_prompt["bundle_id"]) == "physics_waveform_panel_v1"
    assert str(waveform_prompt["task_key"]) == "wave_property_extremum_label_query"

    signal_defaults = get_scene_defaults("physics", "signal_transform")
    signal_generation, signal_rendering, signal_prompt = split_generation_rendering_prompt_defaults(
        signal_defaults,
        task_id="task_physics__signal_transform__periodic_harmonic_spectrum_match_label",
    )
    assert "query_id_weights" not in signal_generation
    assert set(signal_generation["scene_variant_weights"]) == {"clean_match", "grid_match", "lab_sheet"}
    assert set(signal_generation["waveform_family_weights"]) == {"square_wave", "triangle_wave", "sawtooth_wave"}
    assert set(signal_generation["correct_option_letter_weights"]) == {"A", "B", "C", "D"}
    assert int(signal_rendering["canvas_width"]) == 1280
    assert int(signal_rendering["option_width_px"]) == 530
    assert str(signal_prompt["bundle_id"]) == "physics_signal_transform_v1"
    assert str(signal_prompt["task_key"]) == "periodic_harmonic_spectrum_match_query"

    vernier_generation, vernier_rendering, vernier_prompt = split_generation_rendering_prompt_defaults(
        vernier_caliper,
        task_id="task_physics__vernier_caliper__length_readout_value",
    )
    assert "query_id_weights" not in vernier_generation
    assert set(vernier_generation["main_mm_support"]) == set(range(8, 56))
    assert set(vernier_generation["aligned_vernier_tick_support"]) == set(range(1, 10))
    assert int(vernier_rendering["canvas_height"]) == 720
    assert int(vernier_rendering["main_scale_max_mm"]) == 62
    assert str(vernier_prompt["bundle_id"]) == "physics_vernier_caliper_v1"
    assert str(vernier_prompt["task_key"]) == "vernier_caliper_readout_query"

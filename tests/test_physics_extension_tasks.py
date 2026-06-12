"""Contract tests for the physics extension task batch."""

from __future__ import annotations

import itertools
import math

import trace.tasks  # noqa: F401
from trace.core.task_review_distribution import extract_sampling_axes
from trace.core.scene_config import get_scene_defaults
from trace.tasks.physics.circuits.analog_meter import PhysicsAnalogMeterReadoutValueTask
from trace.tasks.physics.circuits.bridge_balance import PhysicsBridgeCircuitMissingResistanceValueTask
from trace.tasks.physics.circuits.bulb_brightness import PhysicsBulbCircuitBrightnessExtremumLabelTask
from trace.tasks.physics.circuits.state_change_brightness import PhysicsCircuitStateChangeBulbBrightnessLabelTask
from trace.tasks.physics.circuits.switch_circuit import PhysicsSwitchCircuitLitBulbCountTask
from trace.tasks.physics.fluids.buoyancy_density import PhysicsBuoyancyDensityObjectDensityValueTask
from trace.tasks.physics.fluids.fluid_flow import PhysicsFluidFlowContinuitySpeedValueTask
from trace.tasks.physics.fluids.graduated_cylinder import (
    PhysicsGraduatedCylinderDisplacementVolumeValueTask,
    PhysicsGraduatedCylinderVolumeReadoutValueTask,
)
from trace.tasks.physics.fluids.manometer import PhysicsManometerPressureDifferenceValueTask
from trace.tasks.physics.magnetism.electromagnetic_induction import PhysicsElectromagneticInductionDirectionCountTask
from trace.tasks.physics.magnetism.wire_field import PhysicsWireMagnetismFieldDirectionChoiceTask
from trace.tasks.physics.measurement.vernier_caliper import PhysicsVernierCaliperLengthReadoutValueTask
from trace.tasks.physics.mechanics.collision_aftermath import PhysicsCollisionIncomingPathCauseChoiceTask
from trace.tasks.physics.mechanics.free_body_forces import PhysicsFreeBodyForcesNetForceDirectionChoiceTask
from trace.tasks.physics.mechanics.gear_train import (
    PhysicsGearTrainOutputDirectionLabelTask,
    PhysicsGearTrainOutputSpeedValueTask,
)
from trace.tasks.physics.mechanics.motion_graph import (
    PhysicsMotionGraphIntervalDisplacementValueTask,
    PhysicsMotionGraphSpeedChangeStateChoiceTask,
)
from trace.tasks.physics.mechanics.orbital_motion import (
    PhysicsOrbitalMotionFocusLocationLabelTask,
    PhysicsOrbitalMotionSpeedExtremumLabelTask,
)
from trace.tasks.physics.mechanics.stack_stability import PhysicsMechanicsStackStabilityStatusLabelTask
from trace.tasks.physics.optics.refraction_layers import PhysicsRefractionLayersMediumSpeedOrderLabelTask
from trace.tasks.physics.optics.shadow_cause import PhysicsShadowCauseLightSourceLabelTask
from trace.tasks.physics.optics.lens_optics import PhysicsLensOpticsImagePropertyChoiceTask
from trace.tasks.physics.thermodynamics.piston_cylinder import PhysicsPistonCylinderBoundaryWorkValueTask
from trace.tasks.physics.thermodynamics.thermal_mixing import PhysicsThermalMixingFinalTemperatureValueTask
from trace.tasks.physics.thermodynamics.thermometer import PhysicsThermometerTemperatureConversionValueTask
from trace.tasks.physics.waves.signal_transform import (
    PhysicsSignalTransformPeriodicHarmonicSpectrumMatchLabelTask,
    PhysicsSignalTransformPulseWidthSpectrumMatchLabelTask,
    PhysicsSignalTransformSinusoidComponentSpectrumMatchLabelTask,
)
from trace.tasks.physics.waves.waveform_panel import PhysicsWaveformPanelWavePropertyExtremumLabelTask
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
    "task_physics__motion_graph__speed_change_state_choice",
    "task_physics__motion_graph__velocity_sign_choice",
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
    "task_physics__signal_transform__pulse_width_spectrum_match_label",
    "task_physics__signal_transform__sinusoid_component_spectrum_match_label",
    "task_physics__vernier_caliper__length_readout_value",
    "task_physics__stack_stability__stability_status_label",
    "task_physics__collision__incoming_path_cause_choice",
    "task_physics__electromagnetic_induction__induced_current_direction_count",
    "task_physics__free_body_forces__net_force_direction_choice",
}


def _assert_keyed_bbox_map_in_bounds(out) -> None:
    width, height = out.image.size
    assert out.annotation_gt.type == "keyed_bbox_map"
    for bbox in out.annotation_gt.value.values():
        assert 0 <= bbox[0] < bbox[2] <= width
        assert 0 <= bbox[1] < bbox[3] <= height


def _assert_bbox_set_in_bounds(out) -> None:
    width, height = out.image.size
    assert out.annotation_gt.type == "bbox_set"
    for bbox in out.annotation_gt.value:
        assert 0 <= bbox[0] < bbox[2] <= width
        assert 0 <= bbox[1] < bbox[3] <= height


def _assert_keyed_point_map_in_bounds(out) -> None:
    width, height = out.image.size
    assert out.annotation_gt.type == "keyed_point_map"
    for point in out.annotation_gt.value.values():
        assert 0 <= point[0] <= width
        assert 0 <= point[1] <= height


def test_physics_extension_task_ids_are_default_registered() -> None:
    physics_ids = {task_id for task_id in list_default_task_ids() if task_id.startswith("task_physics__")}

    assert len(physics_ids) == 53
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


def test_physics_orbital_focus_contract() -> None:
    out = PhysicsOrbitalMotionFocusLocationLabelTask().generate(80101, params={}, max_attempts=20)
    trace = out.trace_payload

    assert out.scene_id == "orbital_motion"
    assert out.query_id == "sun_focus_label"
    assert out.answer_gt.type == "option_letter"
    assert set(out.annotation_gt.value) == {
        "center",
        "selected_focus",
        "major_axis_endpoint_1",
        "major_axis_endpoint_2",
    }
    _assert_keyed_point_map_in_bounds(out)
    assert trace["projected_annotation"]["keyed_point_map"] == out.annotation_gt.value
    assert trace["render_map"]["selected_label"] == out.answer_gt.value
    assert out.prompt_variants["answer_only"]
    assert out.prompt_variants["answer_and_annotation"]


def test_physics_orbital_speed_extremum_uses_sun_distance() -> None:
    task = PhysicsOrbitalMotionSpeedExtremumLabelTask()
    for query_id, direction in [
        ("greatest_speed_position_label", min),
        ("least_speed_position_label", max),
    ]:
        out = task.generate(80177, params={"query_id": query_id}, max_attempts=20)
        render_map = out.trace_payload["render_map"]
        sun = out.annotation_gt.value["sun"]
        distances = {
            str(label): math.hypot(float(point[0] - sun[0]), float(point[1] - sun[1]))
            for label, point in render_map["candidate_points"].items()
        }
        expected_label = direction(distances, key=distances.get)

        assert out.query_id == query_id
        assert out.answer_gt.value == expected_label
        assert render_map["selected_label"] == expected_label
        assert set(out.annotation_gt.value) == {"sun", "selected_position"}
        _assert_keyed_point_map_in_bounds(out)


def test_physics_graduated_cylinder_readout_contracts() -> None:
    volume = PhysicsGraduatedCylinderVolumeReadoutValueTask().generate(80201, params={}, max_attempts=20)
    displacement = PhysicsGraduatedCylinderDisplacementVolumeValueTask().generate(80203, params={}, max_attempts=20)

    assert volume.scene_id == "graduated_cylinder"
    assert volume.query_id == "single_cylinder_volume_readout"
    assert volume.answer_gt.type == "integer"
    assert volume.answer_gt.value == volume.trace_payload["render_map"]["cylinders"]["single"]["volume_ml"]
    assert set(volume.annotation_gt.value) == {"meniscus", "scale_region"}
    _assert_keyed_bbox_map_in_bounds(volume)

    assert displacement.scene_id == "graduated_cylinder"
    assert displacement.query_id == "before_after_displacement_volume"
    assert displacement.answer_gt.type == "integer"
    assert displacement.answer_gt.value == displacement.trace_payload["render_map"]["displacement_ml"]
    assert set(displacement.annotation_gt.value) == {
        "before_meniscus",
        "before_scale_region",
        "after_meniscus",
        "after_scale_region",
    }
    _assert_keyed_bbox_map_in_bounds(displacement)


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
    assert out.query_id == "floating_object_density_value"
    assert out.answer_gt.type == "number"
    assert math.isclose(float(out.answer_gt.value), 0.8, abs_tol=1e-9)
    assert math.isclose(
        float(out.answer_gt.value),
        float(execution["liquid_density_g_cm3"])
        * float(execution["submerged_fraction_num"])
        / float(execution["submerged_fraction_den"]),
        abs_tol=1e-9,
    )
    assert set(out.annotation_gt.value) == {
        "floating_object",
        "waterline",
        "fluid_density_label",
        "submerged_fraction_marker",
    }
    _assert_keyed_bbox_map_in_bounds(out)
    assert out.trace_payload["projected_annotation"]["keyed_bbox_map"] == out.annotation_gt.value
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
    assert out.query_id == "u_tube_pressure_difference"
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == 18
    assert out.answer_gt.value == int(execution["height_cm"]) * int(execution["kpa_per_cm"])
    assert render_map["pressure_difference_kpa"] == 18
    assert render_map["higher_pressure_side"] == "A"
    assert render_map["left_level_y_px"] > render_map["right_level_y_px"]
    assert set(out.annotation_gt.value) == {
        "left_pressure_point",
        "right_pressure_point",
        "height_difference",
        "fluid_density_label",
    }
    _assert_keyed_bbox_map_in_bounds(out)
    assert out.trace_payload["projected_annotation"]["keyed_bbox_map"] == out.annotation_gt.value


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
    assert missing_v2.query_id == "continuity_missing_speed"
    assert missing_v2.answer_gt.type == "integer"
    assert missing_v2.answer_gt.value == 8
    assert missing_v2.trace_payload["execution_trace"]["continuity_lhs"] == 24
    assert missing_v2.trace_payload["execution_trace"]["continuity_rhs"] == 24
    assert missing_v2.trace_payload["render_map"]["missing_station"] == "v2"
    assert set(missing_v2.annotation_gt.value) == {"station_1", "station_2", "flow_path"}
    _assert_keyed_bbox_map_in_bounds(missing_v2)
    assert missing_v2.trace_payload["projected_annotation"]["keyed_bbox_map"] == missing_v2.annotation_gt.value
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
    _assert_keyed_bbox_map_in_bounds(missing_v1)


def test_physics_gear_train_direction_contracts() -> None:
    task = PhysicsGearTrainOutputDirectionLabelTask()
    two_gears = task.generate(
        80291,
        params={
            "scene_variant": "straight_chain",
            "gear_count": 2,
            "input_direction": "clockwise",
        },
        max_attempts=20,
    )
    five_gears = task.generate(
        80293,
        params={
            "scene_variant": "arc_chain",
            "gear_count": 5,
            "input_direction": "counterclockwise",
        },
        max_attempts=20,
    )

    assert two_gears.scene_id == "gear_train"
    assert two_gears.query_id == "marked_output_direction"
    assert two_gears.answer_gt.type == "string"
    assert two_gears.answer_gt.value == "counterclockwise"
    assert two_gears.trace_payload["execution_trace"]["mesh_reversals"] == 1
    assert two_gears.trace_payload["render_map"]["output_direction"] == "counterclockwise"
    assert set(two_gears.annotation_gt.value) == {
        "input_gear",
        "input_rotation_arrow",
        "output_gear",
        "gear_train",
    }
    _assert_keyed_bbox_map_in_bounds(two_gears)
    assert two_gears.trace_payload["projected_annotation"]["keyed_bbox_map"] == two_gears.annotation_gt.value
    assert "clockwise" in two_gears.prompt_variants["answer_only"]
    assert "counterclockwise" in two_gears.prompt_variants["answer_only"]

    assert five_gears.answer_gt.type == "string"
    assert five_gears.answer_gt.value == "counterclockwise"
    assert five_gears.trace_payload["execution_trace"]["mesh_reversals"] == 4
    assert five_gears.trace_payload["render_map"]["gear_count"] == 5
    _assert_keyed_bbox_map_in_bounds(five_gears)


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
    assert slower.query_id == "simple_gear_ratio_output_speed"
    assert slower.answer_gt.type == "integer"
    assert slower.answer_gt.value == 60
    assert slower.trace_payload["execution_trace"]["input_rpm"] == 120
    assert slower.trace_payload["execution_trace"]["input_teeth"] == 20
    assert slower.trace_payload["execution_trace"]["output_teeth"] == 40
    assert slower.trace_payload["execution_trace"]["speed_relation"] == "slower"
    assert set(slower.annotation_gt.value) == {"input_gear", "output_gear", "gear_train"}
    _assert_keyed_bbox_map_in_bounds(slower)
    assert slower.trace_payload["projected_annotation"]["keyed_bbox_map"] == slower.annotation_gt.value

    assert faster_with_idlers.answer_gt.type == "integer"
    assert faster_with_idlers.answer_gt.value == 180
    assert faster_with_idlers.trace_payload["execution_trace"]["gear_count"] == 4
    assert len(faster_with_idlers.trace_payload["execution_trace"]["idler_teeth"]) == 2
    assert faster_with_idlers.trace_payload["execution_trace"]["speed_relation"] == "faster"
    assert faster_with_idlers.trace_payload["render_map"]["ratio_numerator"] == 2160
    assert faster_with_idlers.trace_payload["render_map"]["ratio_denominator"] == 12
    _assert_keyed_bbox_map_in_bounds(faster_with_idlers)


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
    assert set(ammeter.annotation_gt.value) == {"needle", "scale_region", "unit_label"}
    _assert_keyed_bbox_map_in_bounds(ammeter)
    assert ammeter.trace_payload["projected_annotation"]["keyed_bbox_map"] == ammeter.annotation_gt.value

    assert voltmeter.scene_id == "analog_meter"
    assert voltmeter.query_id == "voltmeter_readout"
    assert voltmeter.answer_gt.type == "integer"
    assert voltmeter.answer_gt.value == 11
    assert voltmeter.trace_payload["execution_trace"]["unit"] == "V"
    assert voltmeter.trace_payload["render_map"]["scale_max"] == 12
    assert set(voltmeter.annotation_gt.value) == {"needle", "scale_region", "unit_label"}
    _assert_keyed_bbox_map_in_bounds(voltmeter)


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

    assert expansion.scene_id == "piston_cylinder"
    assert expansion.query_id == "constant_pressure_boundary_work"
    assert expansion.answer_gt.type == "integer"
    assert expansion.answer_gt.value == 12
    assert expansion.trace_payload["execution_trace"]["delta_volume_l"] == 4
    assert expansion.trace_payload["render_map"]["boundary_work_kj"] == 12
    assert set(expansion.annotation_gt.value) == {
        "piston_cylinder",
        "initial_state_label",
        "final_state_label",
        "process_arrow",
    }
    _assert_keyed_bbox_map_in_bounds(expansion)
    assert expansion.trace_payload["projected_annotation"]["keyed_bbox_map"] == expansion.annotation_gt.value

    assert compression.answer_gt.type == "integer"
    assert compression.answer_gt.value == -16
    assert compression.trace_payload["execution_trace"]["delta_volume_l"] == -4
    assert compression.trace_payload["render_map"]["pressure_mpa"] == 4
    assert compression.trace_payload["render_map"]["initial_volume_l"] == 7
    assert compression.trace_payload["render_map"]["final_volume_l"] == 3
    _assert_keyed_bbox_map_in_bounds(compression)


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
    assert set(celsius_to_fahrenheit.annotation_gt.value) == {"liquid_level", "scale_region", "source_unit_label"}
    _assert_keyed_bbox_map_in_bounds(celsius_to_fahrenheit)
    assert celsius_to_fahrenheit.trace_payload["projected_annotation"]["keyed_bbox_map"] == celsius_to_fahrenheit.annotation_gt.value

    assert fahrenheit_to_celsius.scene_id == "thermometer"
    assert fahrenheit_to_celsius.query_id == "fahrenheit_to_celsius_value"
    assert fahrenheit_to_celsius.answer_gt.type == "integer"
    assert fahrenheit_to_celsius.answer_gt.value == 20
    assert fahrenheit_to_celsius.trace_payload["execution_trace"]["source_unit"] == "F"
    assert fahrenheit_to_celsius.trace_payload["execution_trace"]["target_unit"] == "C"
    assert fahrenheit_to_celsius.trace_payload["render_map"]["scale_profile"]["scale_min"] == 20
    assert set(fahrenheit_to_celsius.annotation_gt.value) == {"liquid_level", "scale_region", "source_unit_label"}
    _assert_keyed_bbox_map_in_bounds(fahrenheit_to_celsius)


def test_physics_thermal_mixing_final_temperature_contract() -> None:
    out = PhysicsThermalMixingFinalTemperatureValueTask().generate(
        80303,
        params={"cup_count": 3, "target_answer": 40},
        max_attempts=20,
    )
    execution = out.trace_payload["execution_trace"]
    temperatures = [int(value) for value in execution["initial_temperatures_c"]]

    assert out.scene_id == "thermal_mixing"
    assert out.query_id == "equal_amount_final_temperature"
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
        params={"main_mm": 23, "aligned_vernier_tick": 4},
        max_attempts=20,
    )
    execution = out.trace_payload["execution_trace"]
    render_map = out.trace_payload["render_map"]

    assert out.scene_id == "vernier_caliper"
    assert out.query_id == "main_scale_vernier_mm"
    assert out.answer_gt.type == "number"
    assert math.isclose(float(out.answer_gt.value), 23.4, abs_tol=1e-9)
    assert execution["main_mm"] == 23
    assert execution["aligned_vernier_tick"] == 4
    assert math.isclose(float(execution["target_answer"]), 23.4, abs_tol=1e-9)
    assert math.isclose(float(render_map["answer_mm"]), 23.4, abs_tol=1e-9)
    assert render_map["nearest_aligned_main_tick"] == 27
    sampling_axes = extract_sampling_axes(out)
    assert sampling_axes["aligned_vernier_tick"]["observed"] == "4"
    assert "aligned_tick" not in sampling_axes
    assert set(out.annotation_gt.value) == {
        "main_scale_region",
        "vernier_zero",
        "vernier_scale_region",
        "aligned_vernier_tick",
    }
    _assert_keyed_bbox_map_in_bounds(out)
    assert out.trace_payload["projected_annotation"]["keyed_bbox_map"] == out.annotation_gt.value
    assert out.prompt_variants["answer_only"]
    assert out.prompt_variants["answer_and_annotation"]


def test_physics_wire_magnetism_contract() -> None:
    out = PhysicsWireMagnetismFieldDirectionChoiceTask().generate(80301, params={"orientation": "horizontal"}, max_attempts=20)
    execution = out.trace_payload["execution_trace"]

    assert out.scene_id == "wire_magnetism"
    assert out.query_id == "field_direction_at_point"
    assert out.answer_gt.type == "option_letter"
    assert out.annotation_gt.type == "keyed_bbox_map"
    assert set(out.annotation_gt.value) == {"wire_current", "point_p"}
    assert execution["option_map"][out.answer_gt.value] == execution["field_direction"]
    assert out.annotation_gt.value["wire_current"] not in out.trace_payload["render_map"]["option_bboxes"].values()
    _assert_keyed_bbox_map_in_bounds(out)


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
    assert out.query_id == "three_medium_speed_order"
    assert out.answer_gt.type == "option_letter"
    assert out.annotation_gt.type == "keyed_bbox_map"
    assert set(out.annotation_gt.value) == {"interface_1_bend", "interface_2_bend"}
    _assert_keyed_bbox_map_in_bounds(out)
    assert set(execution["option_map"].values()) == expected_options
    assert execution["option_map"][out.answer_gt.value] == " > ".join(execution["speed_order"])
    assert render_map["correct_label"] == out.answer_gt.value
    assert render_map["speed_order"] == ["M2", "M1", "M3"]

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
    assert out.query_id == "source_from_shadow_label"
    assert out.answer_gt.type == "option_letter"
    assert out.answer_gt.value == "C"
    assert out.annotation_gt.type == "keyed_bbox_map"
    assert set(out.annotation_gt.value) == {"object", "shadow"}
    _assert_keyed_bbox_map_in_bounds(out)
    assert execution["shadow_direction"] == "southeast"
    assert execution["source_direction"] == "northwest"
    assert execution["candidate_directions"][out.answer_gt.value] == "northwest"
    assert render_map["correct_option_letter"] == out.answer_gt.value
    assert render_map["candidate_directions"][out.answer_gt.value] == render_map["source_direction"]
    assert out.annotation_gt.value["object"] == render_map["annotation_keyed_bboxes_px"]["object"]
    assert out.annotation_gt.value["shadow"] == render_map["annotation_keyed_bboxes_px"]["shadow"]
    assert out.annotation_gt.value["object"] not in [
        record["lamp_bbox_px"]
        for record in render_map["candidate_light_sources"].values()
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
    assert out.query_id == "converging_lens_image_property_choice"
    assert out.answer_gt.type == "option_letter"
    assert out.answer_gt.value == "D"
    assert execution["lens_type"] == "converging"
    assert execution["object_position_case"] == "between_f_2f"
    assert execution["option_map"][out.answer_gt.value] == "real_inverted_larger"
    assert set(out.annotation_gt.value) == {"lens", "object_arrow", "focal_marks"}
    _assert_keyed_bbox_map_in_bounds(out)
    assert render_map["correct_option_letter"] == out.answer_gt.value
    assert render_map["image_property"] == "real_inverted_larger"
    assert out.trace_payload["projected_annotation"]["keyed_bbox_map"] == out.annotation_gt.value
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
    assert out.annotation_gt.type == "keyed_bbox_map"
    assert set(out.annotation_gt.value) == {"B1", "B2", "B3", "B4", "B5"}
    _assert_keyed_bbox_map_in_bounds(out)
    assert out.trace_payload["projected_annotation"]["keyed_bbox_map"] == out.annotation_gt.value


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
    assert out.query_id == "lit_bulb_count"
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
    assert out.annotation_gt.type == "keyed_bbox_map"
    assert set(out.annotation_gt.value) == {"changed_switch", "B1", "B2", "B3", "B4", "B5"}
    _assert_keyed_bbox_map_in_bounds(out)
    assert out.trace_payload["projected_annotation"]["keyed_bbox_map"] == out.annotation_gt.value


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
    assert out.query_id == "missing_bridge_resistance"
    assert out.answer_gt.type == "integer"
    assert out.answer_gt.value == values["R4"] == 7
    assert values["R1"] * values["R4"] == values["R2"] * values["R3"]
    assert out.annotation_gt.type == "keyed_bbox_map"
    assert set(out.annotation_gt.value) == {"R1", "R2", "R3", "target_resistor", "zero_meter"}
    _assert_keyed_bbox_map_in_bounds(out)
    assert out.trace_payload["projected_annotation"]["keyed_bbox_map"] == out.annotation_gt.value


def test_physics_motion_graph_contract() -> None:
    out = PhysicsMotionGraphSpeedChangeStateChoiceTask().generate(
        80701,
        params={
            "query_id": "speed_change_state_choice",
            "motion_state": "slowing_down",
            "correct_option_letter": "B",
        },
        max_attempts=20,
    )
    execution = out.trace_payload["execution_trace"]
    segment = execution["target_segment"]

    assert out.scene_id == "motion_graph"
    assert out.query_id == "speed_change_state_choice"
    assert out.answer_gt.type == "option_letter"
    assert out.answer_gt.value == "B"
    assert out.annotation_gt.type == "keyed_bbox_map"
    assert set(out.annotation_gt.value) == {"query_region", "curve_segment"}
    _assert_keyed_bbox_map_in_bounds(out)
    assert execution["graph_kind"] == "velocity_time"
    assert execution["option_map"][out.answer_gt.value] == "slowing_down"
    assert abs(int(segment["y_end"])) < abs(int(segment["y_start"]))


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
    assert out.annotation_gt.type == "keyed_bbox_map"
    assert set(out.annotation_gt.value) == {"marked_interval", "velocity_segment", "axis_scale"}
    _assert_keyed_bbox_map_in_bounds(out)
    assert out.trace_payload["projected_annotation"]["keyed_bbox_map"] == out.annotation_gt.value
    assert execution["displacement_m"] == out.answer_gt.value
    assert execution["velocity_values_m_s"][2:7] == [2, 3, 4, 5, 6]


def test_physics_stack_stability_contract() -> None:
    out = PhysicsMechanicsStackStabilityStatusLabelTask().generate(
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
    assert out.annotation_gt.type == "keyed_bbox_map"
    assert set(out.annotation_gt.value) == {"center_of_mass", "projection", "support_footprint"}
    assert list(statuses.values()).count("tipping") == 1
    assert statuses["E"] == "tipping"
    assert selected_com_x < float(selected_support[0]) or selected_com_x > float(selected_support[2])
    _assert_keyed_bbox_map_in_bounds(out)


def test_physics_collision_aftermath_contract() -> None:
    out = PhysicsCollisionIncomingPathCauseChoiceTask().generate(
        80741,
        params={
            "scene_variant": "aftermath_compact_table",
            "final_motion_direction": "southwest",
            "correct_option_letter": "E",
            "post_image_noise": {"enabled": False},
        },
        max_attempts=20,
    )
    trace = out.trace_payload

    assert out.scene_id == "collision"
    assert out.query_id == "incoming_path_cause_choice"
    assert out.answer_gt.type == "option_letter"
    assert out.answer_gt.value == "E"
    assert set(out.annotation_gt.value) == {"impact_point", "target_after_motion"}
    _assert_keyed_bbox_map_in_bounds(out)
    assert trace["projected_annotation"]["keyed_bbox_map"] == out.annotation_gt.value
    assert trace["execution_trace"]["scenario"]["correct_incoming_direction"] == "southwest"
    assert trace["execution_trace"]["scenario"]["option_directions"]["E"] == "southwest"
    assert "option_E" not in out.annotation_gt.value


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
    assert out.query_id == "net_force_direction_choice"
    assert out.answer_gt.type == "option_letter"
    assert out.answer_gt.value == "D"
    assert out.annotation_gt.type == "bbox_set"
    assert len(out.annotation_gt.value) == 4
    _assert_bbox_set_in_bounds(out)
    assert trace["projected_annotation"]["bbox_set"] == out.annotation_gt.value
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
    assert out.annotation_gt.type == "bbox_set"
    assert out.annotation_gt.value == [selected["bbox_px"]]
    assert int(selected["cycle_count"]) == min(int(panel["cycle_count"]) for panel in execution["panels"])
    assert out.trace_payload["projected_annotation"]["bbox_set"] == out.annotation_gt.value


def test_physics_signal_transform_contracts() -> None:
    sinusoid = PhysicsSignalTransformSinusoidComponentSpectrumMatchLabelTask().generate(
        80881,
        params={
            "query_id": "sinusoid_component_spectrum",
            "waveform_family": "single_sinusoid",
            "correct_option_letter": "D",
        },
        max_attempts=20,
    )
    periodic = PhysicsSignalTransformPeriodicHarmonicSpectrumMatchLabelTask().generate(
        80883,
        params={
            "query_id": "periodic_wave_harmonic_spectrum",
            "waveform_family": "triangle_wave",
            "correct_option_letter": "B",
        },
        max_attempts=20,
    )
    pulse = PhysicsSignalTransformPulseWidthSpectrumMatchLabelTask().generate(
        80885,
        params={
            "query_id": "pulse_width_spectrum",
            "waveform_family": "narrow_pulse",
            "correct_option_letter": "E",
        },
        max_attempts=20,
    )

    assert sinusoid.scene_id == "signal_transform"
    assert sinusoid.query_id == "sinusoid_component_spectrum"
    assert sinusoid.answer_gt.type == "option_letter"
    assert sinusoid.answer_gt.value == "D"
    assert sinusoid.annotation_gt.type == "keyed_bbox_map"
    assert set(sinusoid.annotation_gt.value) == {"input_waveform", "selected_spectrum"}
    _assert_keyed_bbox_map_in_bounds(sinusoid)
    assert sinusoid.trace_payload["projected_annotation"]["keyed_bbox_map"] == sinusoid.annotation_gt.value
    assert sinusoid.trace_payload["execution_trace"]["option_map"]["D"] == sinusoid.trace_payload["execution_trace"]["correct_spectrum"]
    assert sinusoid.trace_payload["execution_trace"]["correct_spectrum"]["kind"] == "spikes"
    assert len(sinusoid.trace_payload["execution_trace"]["correct_spectrum"]["bins"]) == 1
    assert sinusoid.trace_payload["render_map"]["option_bboxes"]["D"] == sinusoid.annotation_gt.value["selected_spectrum"]

    assert periodic.query_id == "periodic_wave_harmonic_spectrum"
    assert periodic.answer_gt.value == "B"
    assert periodic.trace_payload["execution_trace"]["waveform_family"] == "triangle_wave"
    assert periodic.trace_payload["execution_trace"]["correct_spectrum"]["signature"] == "odd_harmonics_fast"
    assert periodic.trace_payload["execution_trace"]["correct_spectrum"]["bins"] == [1, 3, 5, 7]
    _assert_keyed_bbox_map_in_bounds(periodic)

    assert pulse.query_id == "pulse_width_spectrum"
    assert pulse.answer_gt.value == "E"
    assert pulse.trace_payload["execution_trace"]["waveform_family"] == "narrow_pulse"
    assert pulse.trace_payload["execution_trace"]["correct_spectrum"]["signature"] == "wide_sinc_envelope"
    assert pulse.trace_payload["execution_trace"]["correct_spectrum"]["kind"] == "sinc"
    assert pulse.trace_payload["execution_trace"]["option_map"]["E"] == pulse.trace_payload["execution_trace"]["correct_spectrum"]
    _assert_keyed_bbox_map_in_bounds(pulse)


def test_physics_extension_defaults_expose_prompt_and_rendering_contracts() -> None:
    mechanics = get_scene_defaults("physics", "mechanics")
    circuits = get_scene_defaults("physics", "circuits")
    fluids = get_scene_defaults("physics", "fluids")
    magnetism = get_scene_defaults("physics", "magnetism")
    optics = get_scene_defaults("physics", "optics")
    waves = get_scene_defaults("physics", "waves")
    measurement = get_scene_defaults("physics", "measurement")

    orbital_generation, orbital_rendering, orbital_prompt = split_generation_rendering_prompt_defaults(
        mechanics,
        task_id="physics_mechanics_orbital_motion_family",
    )
    assert set(orbital_generation["query_id_weights"]) == {
        "sun_focus_label",
        "greatest_speed_position_label",
        "least_speed_position_label",
    }
    assert int(orbital_rendering["canvas_width"]) == 1040
    assert str(orbital_prompt["scene_key"]) == "orbital_motion_diagram"
    assert "selected_focus" in str(orbital_prompt["annotation_hint_sun_focus_label"])

    cylinder_generation, cylinder_rendering, cylinder_prompt = split_generation_rendering_prompt_defaults(
        fluids,
        task_id="physics_fluids_graduated_cylinder_family",
    )
    assert set(cylinder_generation["query_id_weights"]) == {
        "single_cylinder_volume_readout",
        "before_after_displacement_volume",
    }
    assert int(cylinder_rendering["canvas_height"]) == 720
    assert str(cylinder_prompt["task_key"]) == "graduated_cylinder_query"
    assert "before_meniscus" in str(cylinder_prompt["annotation_hint_before_after_displacement_volume"])

    buoyancy_generation, buoyancy_rendering, buoyancy_prompt = split_generation_rendering_prompt_defaults(
        fluids,
        task_id="physics_fluids_buoyancy_density_family",
    )
    assert set(buoyancy_generation["query_id_weights"]) == {"floating_object_density_value"}
    assert set(buoyancy_generation["scene_variant_weights"]) == {"rectangular_tank", "beaker_tank", "wide_tank"}
    assert set(buoyancy_generation["object_shape_weights"]) == {"block", "rounded_block", "capsule_block"}
    assert int(buoyancy_rendering["canvas_height"]) == 720
    assert str(buoyancy_prompt["task_key"]) == "buoyancy_density_query"
    assert "submerged_fraction_marker" in str(buoyancy_prompt["annotation_hint_floating_object_density_value"])

    manometer_generation, manometer_rendering, manometer_prompt = split_generation_rendering_prompt_defaults(
        fluids,
        task_id="physics_fluids_manometer_family",
    )
    assert set(manometer_generation["query_id_weights"]) == {"u_tube_pressure_difference"}
    assert set(manometer_generation["height_cm_support"]) == set(range(2, 13))
    assert set(manometer_generation["kpa_per_cm_support"]) == {1, 2, 3, 4, 5}
    assert int(manometer_rendering["canvas_height"]) == 720
    assert str(manometer_prompt["task_key"]) == "manometer_pressure_difference_query"
    assert "height_difference" in str(manometer_prompt["annotation_hint_u_tube_pressure_difference"])

    flow_generation, flow_rendering, flow_prompt = split_generation_rendering_prompt_defaults(
        fluids,
        task_id="physics_fluids_fluid_flow_family",
    )
    assert set(flow_generation["query_id_weights"]) == {"continuity_missing_speed"}
    assert set(flow_generation["orientation_weights"]) == {"horizontal_pipe", "vertical_pipe"}
    assert set(flow_generation["area_cm2_support"]) == {2, 3, 4, 5, 6, 8, 9, 10, 12}
    assert int(flow_rendering["canvas_height"]) == 720
    assert str(flow_prompt["scene_key"]) == "fluid_flow_diagram"
    assert "station_1" in str(flow_prompt["annotation_hint_continuity_missing_speed"])

    wire_generation, wire_rendering, wire_prompt = split_generation_rendering_prompt_defaults(
        magnetism,
        task_id="physics_magnetism_wire_field_family",
    )
    assert set(wire_generation["query_id_weights"]) == {"field_direction_at_point"}
    assert set(wire_generation["orientation_weights"]) == {"horizontal", "vertical"}
    assert int(wire_rendering["canvas_width"]) == 1080
    assert str(wire_prompt["scene_key"]) == "wire_magnetism_field"
    assert "wire_current" in str(wire_prompt["annotation_hint_field_direction_at_point"])

    induction_generation, induction_rendering, induction_prompt = split_generation_rendering_prompt_defaults(
        magnetism,
        task_id="physics_magnetism_electromagnetic_induction_family",
    )
    assert set(induction_generation["query_id_weights"]) == {
        "clockwise_induced_current_count",
        "counterclockwise_induced_current_count",
        "no_induced_current_count",
    }
    assert set(induction_generation["target_answer_support"]) == set(range(7))
    assert int(induction_rendering["canvas_width"]) == 1180
    assert str(induction_prompt["scene_key"]) == "electromagnetic_induction_panel_grid"
    assert "full mini-panels" in str(induction_prompt["annotation_hint_clockwise_induced_current_count"])

    refraction_generation, refraction_rendering, refraction_prompt = split_generation_rendering_prompt_defaults(
        optics,
        task_id="physics_optics_refraction_layers_family",
    )
    assert set(refraction_generation["query_id_weights"]) == {"three_medium_speed_order"}
    assert set(refraction_generation["layer_orientation_weights"]) == {"horizontal", "vertical"}
    assert int(refraction_rendering["canvas_width"]) == 1080
    assert str(refraction_prompt["scene_key"]) == "refraction_layers_diagram"
    assert "interface_1_bend" in str(refraction_prompt["annotation_hint_three_medium_speed_order"])

    shadow_generation, shadow_rendering, shadow_prompt = split_generation_rendering_prompt_defaults(
        optics,
        task_id="physics_optics_shadow_cause_family",
    )
    assert set(shadow_generation["query_id_weights"]) == {"source_from_shadow_label"}
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
    assert str(shadow_prompt["scene_key"]) == "shadow_cause_diagram"
    assert "object" in str(shadow_prompt["annotation_hint_source_from_shadow_label"])

    lens_generation, lens_rendering, lens_prompt = split_generation_rendering_prompt_defaults(
        optics,
        task_id="physics_optics_lens_optics_family",
    )
    assert set(lens_generation["query_id_weights"]) == {"converging_lens_image_property_choice"}
    assert set(lens_generation["scene_variant_weights"]) == {"clean_axis", "paper_grid", "lab_card"}
    assert set(lens_generation["object_position_case_weights"]) == {
        "beyond_2f",
        "at_2f",
        "between_f_2f",
        "inside_f",
    }
    assert set(lens_generation["correct_option_letter_weights"]) == {"A", "B", "C", "D"}
    assert int(lens_rendering["canvas_width"]) == 1120
    assert str(lens_prompt["scene_key"]) == "lens_optics_diagram"
    assert "object_arrow" in str(lens_prompt["annotation_hint_converging_lens_image_property_choice"])

    bulb_generation, bulb_rendering, bulb_prompt = split_generation_rendering_prompt_defaults(
        circuits,
        task_id="physics_circuits_bulb_brightness_family",
    )
    assert set(bulb_generation["query_id_weights"]) == {"brightest_bulb_label", "dimmest_bulb_label"}
    assert set(bulb_generation["scene_variant_weights"]) == {"series_unequal", "parallel_unequal", "mixed_branch"}
    assert int(bulb_rendering["canvas_width"]) == 1280
    assert str(bulb_prompt["scene_key"]) == "bulb_circuit_diagram"
    assert "B1" in str(bulb_prompt["annotation_hint_brightness_extremum"])

    switch_generation, switch_rendering, switch_prompt = split_generation_rendering_prompt_defaults(
        circuits,
        task_id="physics_circuits_switch_circuit_family",
    )
    assert set(switch_generation["query_id_weights"]) == {"lit_bulb_count"}
    assert set(switch_generation["scene_variant_weights"]) == {"mixed_branch"}
    assert list(switch_generation["target_answer_support"]) == [0, 1, 2, 3, 4, 5]
    assert int(switch_rendering["canvas_width"]) == 1280
    assert str(switch_prompt["scene_key"]) == "switch_circuit_diagram"
    assert "empty array" in str(switch_prompt["annotation_hint_lit_bulb_count"])

    state_generation, state_rendering, state_prompt = split_generation_rendering_prompt_defaults(
        circuits,
        task_id="physics_circuits_state_change_bulb_brightness_family",
    )
    assert set(state_generation["query_id_weights"]) == {
        "brightens_after_switch_change",
        "dims_after_switch_change",
        "turns_on_after_switch_change",
        "turns_off_after_switch_change",
    }
    assert list(state_generation["resistance_options"]) == [2, 3, 4, 5, 6, 8, 10, 12]
    assert int(state_rendering["canvas_width"]) == 1280
    assert str(state_prompt["scene_key"]) == "circuit_state_change_diagram"
    assert str(state_prompt["task_key"]) == "state_change_brightness_query"
    assert "B1 through B5" in str(state_prompt["annotation_hint_state_change_brightness"])

    bridge_generation, bridge_rendering, bridge_prompt = split_generation_rendering_prompt_defaults(
        circuits,
        task_id="physics_circuits_bridge_missing_resistance_family",
    )
    assert set(bridge_generation["query_id_weights"]) == {"missing_bridge_resistance"}
    assert set(bridge_generation["missing_resistor_weights"]) == {"R1", "R2", "R3", "R4"}
    assert int(bridge_rendering["canvas_width"]) == 1280
    assert str(bridge_prompt["scene_key"]) == "bridge_circuit_diagram"
    assert "zero_meter" in str(bridge_prompt["annotation_hint_missing_bridge_resistance"])

    meter_generation, meter_rendering, meter_prompt = split_generation_rendering_prompt_defaults(
        circuits,
        task_id="physics_circuits_analog_meter_family",
    )
    assert set(meter_generation["query_id_weights"]) == {"ammeter_readout", "voltmeter_readout"}
    assert set(meter_generation["meter_profile_weights"]) == {"ammeter_a", "ammeter_ma", "voltmeter_v"}
    assert int(meter_rendering["canvas_height"]) == 720
    assert str(meter_prompt["scene_key"]) == "analog_meter_diagram"
    assert "scale_region" in str(meter_prompt["annotation_hint_ammeter_readout"])

    thermodynamics = get_scene_defaults("physics", "thermodynamics")
    piston_generation, piston_rendering, piston_prompt = split_generation_rendering_prompt_defaults(
        thermodynamics,
        task_id="physics_thermodynamics_piston_cylinder_family",
    )
    assert set(piston_generation["query_id_weights"]) == {"constant_pressure_boundary_work"}
    assert set(piston_generation["orientation_weights"]) == {"vertical_pair", "horizontal_pair"}
    assert set(piston_generation["pressure_mpa_support"]) == {1, 2, 3, 4, 5, 6}
    assert int(piston_rendering["canvas_height"]) == 740
    assert str(piston_prompt["scene_key"]) == "piston_cylinder_apparatus"
    assert "initial_state_label" in str(piston_prompt["annotation_hint_constant_pressure_boundary_work"])

    thermometer_generation, thermometer_rendering, thermometer_prompt = split_generation_rendering_prompt_defaults(
        thermodynamics,
        task_id="physics_thermodynamics_thermometer_family",
    )
    assert set(thermometer_generation["query_id_weights"]) == {
        "celsius_to_fahrenheit_value",
        "fahrenheit_to_celsius_value",
    }
    assert set(thermometer_generation["scale_profile_weights"]) == {
        "celsius_weather",
        "celsius_lab",
        "fahrenheit_weather",
        "fahrenheit_compact",
    }
    assert int(thermometer_rendering["canvas_width"]) == 1100
    assert str(thermometer_prompt["scene_key"]) == "thermometer_scale"
    assert "source_unit_label" in str(thermometer_prompt["annotation_hint_celsius_to_fahrenheit_value"])

    thermal_mixing_generation, thermal_mixing_rendering, thermal_mixing_prompt = split_generation_rendering_prompt_defaults(
        thermodynamics,
        task_id="physics_thermodynamics_thermal_mixing_family",
    )
    assert set(thermal_mixing_generation["query_id_weights"]) == {"equal_amount_final_temperature"}
    assert set(str(key) for key in thermal_mixing_generation["cup_count_weights"]) == {"2", "3", "4"}
    assert set(thermal_mixing_generation["final_temperature_support"]) == {20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70}
    assert int(thermal_mixing_rendering["canvas_width"]) == 1180
    assert str(thermal_mixing_prompt["scene_key"]) == "thermal_mixing_setup"
    assert "initial cups" in str(thermal_mixing_prompt["annotation_hint_equal_amount_final_temperature"])

    motion_generation, motion_rendering, motion_prompt = split_generation_rendering_prompt_defaults(
        mechanics,
        task_id="physics_mechanics_motion_graph_family",
    )
    assert set(motion_generation["query_id_weights"]) == {"velocity_sign_choice", "speed_change_state_choice"}
    assert set(motion_generation["correct_option_letter_weights"]) == {"A", "B", "C", "D"}
    assert int(motion_rendering["canvas_width"]) == 1120
    assert str(motion_prompt["scene_key"]) == "motion_graph_diagram"
    assert "curve_segment" in str(motion_prompt["annotation_hint_speed_change_state_choice"])

    interval_generation, interval_rendering, interval_prompt = split_generation_rendering_prompt_defaults(
        mechanics,
        task_id="physics_mechanics_motion_graph_interval_displacement_family",
    )
    assert set(interval_generation["query_id_weights"]) == {
        "constant_velocity_interval_displacement",
        "constant_acceleration_interval_displacement",
    }
    assert set(interval_generation["scene_variant_weights"]) == {"clean_grid", "paper_grid", "bold_grid"}
    assert set(interval_generation["constant_acceleration_interval_width_support"]) == {2, 4}
    assert int(interval_rendering["canvas_width"]) == 1120
    assert int(interval_rendering["y_min"]) == 0
    assert str(interval_prompt["scene_key"]) == "motion_graph_diagram"
    assert "axis_scale" in str(interval_prompt["annotation_hint_constant_acceleration_interval_displacement"])

    stack_generation, stack_rendering, stack_prompt = split_generation_rendering_prompt_defaults(
        mechanics,
        task_id="physics_mechanics_stack_stability_family",
    )
    assert set(stack_generation["query_id_weights"]) == {"stable_stack_label", "tipping_stack_label"}
    assert set(stack_generation["correct_option_letter_weights"]) == {"A", "B", "C", "D", "E", "F"}
    assert int(stack_rendering["canvas_width"]) == 1180
    assert str(stack_prompt["scene_key"]) == "stack_stability_diagram"
    assert "center_of_mass" in str(stack_prompt["annotation_hint_stable_stack_label"])

    aftermath_generation, aftermath_rendering, aftermath_prompt = split_generation_rendering_prompt_defaults(
        mechanics,
        task_id="physics_mechanics_collision_aftermath_family",
    )
    assert set(aftermath_generation["query_id_weights"]) == {"incoming_path_cause_choice"}
    assert set(aftermath_generation["scene_variant_weights"]) == {
        "aftermath_table",
        "aftermath_gridded_table",
        "aftermath_compact_table",
    }
    assert set(aftermath_generation["final_motion_direction_weights"]) == {
        "east",
        "northeast",
        "north",
        "northwest",
        "west",
        "southwest",
        "south",
        "southeast",
    }
    assert set(aftermath_generation["correct_option_letter_weights"]) == {"A", "B", "C", "D", "E", "F"}
    assert int(aftermath_rendering["canvas_width"]) == 1180
    assert str(aftermath_prompt["scene_key"]) == "collision_aftermath_diagram"
    assert "impact_point" in str(aftermath_prompt["annotation_hint_incoming_path_cause_choice"])

    free_body_generation, free_body_rendering, free_body_prompt = split_generation_rendering_prompt_defaults(
        mechanics,
        task_id="physics_mechanics_free_body_forces_family",
    )
    assert set(free_body_generation["query_id_weights"]) == {"net_force_direction_choice"}
    assert set(free_body_generation["correct_option_letter_weights"]) == {"A", "B", "C", "D", "E", "F", "G", "H"}
    assert int(free_body_rendering["canvas_width"]) == 1180
    assert str(free_body_prompt["scene_key"]) == "free_body_force_diagram"
    assert "applied force arrow" in str(free_body_prompt["annotation_hint_net_force_direction_choice"])

    gear_generation, gear_rendering, gear_prompt = split_generation_rendering_prompt_defaults(
        mechanics,
        task_id="physics_mechanics_gear_train_family",
    )
    assert set(gear_generation["query_id_weights"]) == {"marked_output_direction"}
    assert set(gear_generation["scene_variant_weights"]) == {"straight_chain", "staggered_chain", "arc_chain"}
    assert set(gear_generation["gear_count_support"]) == {2, 3, 4, 5, 6}
    assert int(gear_rendering["canvas_width"]) == 1040
    assert str(gear_prompt["scene_key"]) == "gear_train_diagram"
    assert "input_rotation_arrow" in str(gear_prompt["annotation_hint_marked_output_direction"])
    assert "clockwise" in str(gear_prompt["json_example"])

    gear_speed_generation, gear_speed_rendering, gear_speed_prompt = split_generation_rendering_prompt_defaults(
        mechanics,
        task_id="physics_mechanics_gear_train_speed_family",
    )
    assert set(gear_speed_generation["query_id_weights"]) == {"simple_gear_ratio_output_speed"}
    assert set(gear_speed_generation["scene_variant_weights"]) == {"straight_chain", "staggered_chain", "arc_chain"}
    assert set(gear_speed_generation["gear_count_support"]) == {2, 3, 4}
    assert set(gear_speed_generation["tooth_count_support"]) == {12, 16, 18, 20, 24, 30, 36, 40, 48}
    assert int(gear_speed_rendering["canvas_width"]) == 1040
    assert str(gear_speed_prompt["scene_key"]) == "gear_train_diagram"
    assert "input_gear" in str(gear_speed_prompt["annotation_hint_simple_gear_ratio_output_speed"])
    assert "rpm" in str(gear_speed_prompt["answer_hint_simple_gear_ratio_output_speed"])

    waveform_generation, waveform_rendering, waveform_prompt = split_generation_rendering_prompt_defaults(
        waves,
        task_id="physics_waves_waveform_panel_family",
    )
    assert set(waveform_generation["query_id_weights"]) == {
        "highest_amplitude_label",
        "lowest_amplitude_label",
        "highest_frequency_label",
        "lowest_frequency_label",
        "longest_wavelength_label",
        "shortest_wavelength_label",
    }
    assert set(int(key) for key in waveform_generation["panel_count_weights"]) == {4, 5, 6}
    assert int(waveform_rendering["canvas_width"]) == 1180
    assert str(waveform_prompt["scene_key"]) == "waveform_panel_diagram"
    assert "selected waveform panel" in str(waveform_prompt["annotation_hint_highest_amplitude_label"])

    signal_generation, signal_rendering, signal_prompt = split_generation_rendering_prompt_defaults(
        waves,
        task_id="physics_waves_signal_transform_family",
    )
    assert set(signal_generation["query_id_weights"]) == {
        "sinusoid_component_spectrum",
        "periodic_wave_harmonic_spectrum",
        "pulse_width_spectrum",
    }
    assert set(signal_generation["scene_variant_weights"]) == {"clean_match", "grid_match", "lab_sheet"}
    assert int(signal_rendering["canvas_width"]) == 1280
    assert str(signal_prompt["scene_key"]) == "signal_transform_diagram"
    assert "selected_spectrum" in str(signal_prompt["annotation_hint_sinusoid_component_spectrum"])

    caliper_generation, caliper_rendering, caliper_prompt = split_generation_rendering_prompt_defaults(
        measurement,
        task_id="physics_measurement_vernier_caliper_family",
    )
    assert set(caliper_generation["query_id_weights"]) == {"main_scale_vernier_mm"}
    assert set(caliper_generation["aligned_vernier_tick_support"]) == {1, 2, 3, 4, 5, 6, 7, 8, 9}
    assert int(caliper_rendering["canvas_width"]) == 1180
    assert str(caliper_prompt["scene_key"]) == "vernier_caliper_diagram"
    assert "aligned_vernier_tick" in str(caliper_prompt["annotation_hint_main_scale_vernier_mm"])

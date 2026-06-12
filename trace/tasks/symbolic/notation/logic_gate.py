"""Boolean logic-gate circuit notation tasks."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import required_group_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ..shared.common import get_int_range as _get_range
from ..shared.common import load_symbolic_task_defaults, resolve_symbolic_axis_variant
from ..shared.logic_gate_scene import (
    CandidateAssignmentSpec,
    LogicCircuitSpec,
    LogicGateRenderParams,
    LogicGateSpec,
    LogicInputSpec,
    SUPPORTED_LOGIC_GATE_SCENE_VARIANTS,
    SUPPORTED_LOGIC_GATE_TYPES,
    evaluate_logic_circuit,
    render_logic_assignment_scene,
    render_logic_gate_count_scene,
)
from ..shared.scene_style import make_symbolic_scene_background, resolve_symbolic_scene_style
from ..shared.visual_defaults import load_symbolic_noise_defaults


SCENE_ID = "logic_gate_circuit"
OUTPUT_VALUE_COUNT_TASK_ID = "task_symbolic__logic_gate_circuit__output_value_count"
SATISFYING_ASSIGNMENT_TASK_ID = "task_symbolic__logic_gate_circuit__satisfying_assignment_label"
TASK_ID = OUTPUT_VALUE_COUNT_TASK_ID

OUTPUT_ONE_COUNT_QUERY_ID = "output_one_count"
OUTPUT_ZERO_COUNT_QUERY_ID = "output_zero_count"
ASSIGNMENT_OUTPUTS_ONE_QUERY_ID = "assignment_outputs_one_label"
ASSIGNMENT_OUTPUTS_ZERO_QUERY_ID = "assignment_outputs_zero_label"
COUNT_QUERY_IDS: tuple[str, ...] = (OUTPUT_ONE_COUNT_QUERY_ID, OUTPUT_ZERO_COUNT_QUERY_ID)
ASSIGNMENT_QUERY_IDS: tuple[str, ...] = (ASSIGNMENT_OUTPUTS_ONE_QUERY_ID, ASSIGNMENT_OUTPUTS_ZERO_QUERY_ID)
OPTION_LABELS: tuple[str, ...] = ("A", "B", "C", "D", "E", "F")
INPUT_LABELS: tuple[str, ...] = ("x", "y", "z")

_TASK_GROUP_DEFAULTS = get_scene_defaults("symbolic", "notation")
POST_IMAGE_NOISE_DEFAULTS = load_symbolic_noise_defaults(scene_id="notation", apply_prob=0.20)


@dataclass(frozen=True)
class _Dataset:
    task_id: str
    query_id: str
    scene_variant: str
    target_output_value: int
    answer_type: str
    answer_value: int | str
    target_answer_support: tuple[int | str, ...]
    circuits: tuple[LogicCircuitSpec, ...]
    source_circuit: LogicCircuitSpec | None
    candidates: tuple[CandidateAssignmentSpec, ...]
    annotation_output_ids: tuple[str, ...]
    annotation_item_ids: tuple[str, ...]
    metadata: dict[str, Any]


def _load_defaults(task_id: str) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, float]]:
    return load_symbolic_task_defaults(_TASK_GROUP_DEFAULTS, task_id=str(task_id))


def _resolve_scene_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    return resolve_symbolic_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_LOGIC_GATE_SCENE_VARIANTS,
        task_id=str(task_id),
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def _resolve_query_id(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
    supported_query_ids: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    return resolve_symbolic_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=tuple(str(item) for item in supported_query_ids),
        task_id=str(task_id),
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        axis_namespace="query_id",
    )


def _resolve_render_params(defaults: Mapping[str, Any]) -> LogicGateRenderParams:
    return LogicGateRenderParams(
        canvas_width=int(defaults.get("logic_canvas_width", defaults.get("canvas_width", 1180))),
        canvas_height=int(defaults.get("logic_canvas_height", defaults.get("canvas_height", 820))),
        card_corner_radius_px=int(defaults.get("logic_card_corner_radius_px", defaults.get("panel_corner_radius_px", 18))),
        card_border_width_px=int(defaults.get("logic_card_border_width_px", defaults.get("panel_border_width_px", 2))),
        gate_width_px=int(defaults.get("logic_gate_width_px", 72)),
        gate_height_px=int(defaults.get("logic_gate_height_px", 38)),
        wire_width_px=int(defaults.get("logic_wire_width_px", 3)),
        node_radius_px=int(defaults.get("logic_node_radius_px", 5)),
        label_font_size_px=int(defaults.get("logic_label_font_size_px", defaults.get("label_font_size_px", 22))),
        small_font_size_px=int(defaults.get("logic_small_font_size_px", defaults.get("small_font_size_px", 16))),
        gate_font_size_px=int(defaults.get("logic_gate_font_size_px", 15)),
        table_font_size_px=int(defaults.get("logic_table_font_size_px", 20)),
    )


def _target_output_value(query_id: str) -> int:
    if str(query_id) in {OUTPUT_ONE_COUNT_QUERY_ID, ASSIGNMENT_OUTPUTS_ONE_QUERY_ID}:
        return 1
    if str(query_id) in {OUTPUT_ZERO_COUNT_QUERY_ID, ASSIGNMENT_OUTPUTS_ZERO_QUERY_ID}:
        return 0
    raise ValueError(f"unsupported logic-gate query_id: {query_id}")


def _gate_arity(gate_type: str) -> int:
    return 1 if str(gate_type).upper() == "NOT" else 2


def _sample_random_circuit(
    rng: Any,
    *,
    item_id: str,
    label: str,
    input_count: int,
    gate_count: int,
) -> LogicCircuitSpec:
    inputs = tuple(
        LogicInputSpec(
            item_id=f"{item_id}_in_{INPUT_LABELS[index]}",
            label=str(INPUT_LABELS[index]),
            value=int(rng.randrange(2)),
        )
        for index in range(int(input_count))
    )
    available_signal_ids = [str(input_spec.item_id) for input_spec in inputs]
    gates: list[LogicGateSpec] = []
    for gate_index in range(int(gate_count)):
        gate_type = str(rng.choice(SUPPORTED_LOGIC_GATE_TYPES))
        arity = _gate_arity(gate_type)
        if int(arity) == 1:
            selected_inputs = (str(rng.choice(available_signal_ids)),)
        else:
            selected_inputs = tuple(str(item) for item in rng.sample(available_signal_ids, 2))
        output_signal_id = f"{item_id}_sig_{gate_index + 1}"
        gates.append(
            LogicGateSpec(
                item_id=f"{item_id}_gate_{gate_index + 1}",
                gate_type=str(gate_type),
                input_signal_ids=tuple(selected_inputs),
                output_signal_id=str(output_signal_id),
            )
        )
        available_signal_ids.append(str(output_signal_id))

    circuit = LogicCircuitSpec(
        item_id=str(item_id),
        label=str(label),
        inputs=tuple(inputs),
        gates=tuple(gates),
        output_signal_id=str(available_signal_ids[-1]),
        output_value=None,
        role="candidate_circuit",
    )
    return LogicCircuitSpec(
        item_id=str(circuit.item_id),
        label=str(circuit.label),
        inputs=tuple(circuit.inputs),
        gates=tuple(circuit.gates),
        output_signal_id=str(circuit.output_signal_id),
        output_value=int(evaluate_logic_circuit(circuit)),
        role=str(circuit.role),
    )


def _output_dependency_signal_ids(circuit: LogicCircuitSpec) -> set[str]:
    dependencies: dict[str, set[str]] = {str(input_spec.item_id): {str(input_spec.item_id)} for input_spec in circuit.inputs}
    for gate in circuit.gates:
        gate_dependencies: set[str] = set()
        for signal_id in gate.input_signal_ids:
            gate_dependencies.update(dependencies[str(signal_id)])
        gate_dependencies.add(str(gate.output_signal_id))
        dependencies[str(gate.output_signal_id)] = set(gate_dependencies)
    return set(dependencies[str(circuit.output_signal_id)])


def _sample_circuit_with_output(
    rng: Any,
    *,
    item_id: str,
    label: str,
    input_count_min: int,
    input_count_max: int,
    gate_count_min: int,
    gate_count_max: int,
    target_output_value: int,
) -> LogicCircuitSpec:
    last_circuit: LogicCircuitSpec | None = None
    for _attempt in range(1000):
        input_count = int(rng.randint(int(input_count_min), int(input_count_max)))
        gate_count = int(rng.randint(int(gate_count_min), int(gate_count_max)))
        circuit = _sample_random_circuit(
            rng,
            item_id=str(item_id),
            label=str(label),
            input_count=int(input_count),
            gate_count=int(gate_count),
        )
        last_circuit = circuit
        required_input_ids = {str(input_spec.item_id) for input_spec in circuit.inputs}
        required_gate_signal_ids = {str(gate.output_signal_id) for gate in circuit.gates}
        dependency_signal_ids = _output_dependency_signal_ids(circuit)
        if not required_input_ids.issubset(dependency_signal_ids):
            continue
        if not required_gate_signal_ids.issubset(dependency_signal_ids):
            continue
        if int(circuit.output_value or 0) == int(target_output_value):
            return circuit
    if last_circuit is None:
        raise RuntimeError("failed to sample a candidate circuit")
    raise RuntimeError(f"failed to sample circuit with output {target_output_value}")


def _build_count_dataset(
    *,
    instance_seed: int,
    scene_variant: str,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    query_id: str,
) -> _Dataset:
    rng = spawn_rng(int(instance_seed), f"{OUTPUT_VALUE_COUNT_TASK_ID}.dataset")
    target_output = _target_output_value(str(query_id))
    answer_min, answer_max = _get_range(
        params,
        gen_defaults,
        min_key="target_answer_min",
        max_key="target_answer_max",
        fallback_min=0,
        fallback_max=6,
    )
    if int(answer_min) < 0 or int(answer_max) > 6:
        raise ValueError("logic-gate output-count answer support must stay within 0..6")
    answer = int(params.get("answer_value", params.get("target_answer", rng.randint(int(answer_min), int(answer_max)))))
    if not int(answer_min) <= int(answer) <= int(answer_max):
        raise ValueError("answer_value is outside configured logic-gate count support")
    circuit_count = int(params.get("circuit_count", gen_defaults.get("circuit_count", 6)))
    if int(circuit_count) != 6:
        raise ValueError("logic-gate output-count scenes require exactly six circuits")
    input_count_min, input_count_max = _get_range(
        params,
        gen_defaults,
        min_key="input_count_min",
        max_key="input_count_max",
        fallback_min=2,
        fallback_max=3,
    )
    gate_count_min, gate_count_max = _get_range(
        params,
        gen_defaults,
        min_key="gate_count_min",
        max_key="gate_count_max",
        fallback_min=1,
        fallback_max=3,
    )
    if int(input_count_min) < 2 or int(input_count_max) > 3:
        raise ValueError("logic-gate output-count input support must stay within 2..3")
    if int(gate_count_min) < 1 or int(gate_count_max) > 3:
        raise ValueError("logic-gate output-count gate support must stay within 1..3")
    labels = OPTION_LABELS[: int(circuit_count)]
    matching_indices = set(int(index) for index in rng.sample(list(range(int(circuit_count))), int(answer)))
    circuits: list[LogicCircuitSpec] = []
    for index, label in enumerate(labels):
        desired_output = int(target_output) if int(index) in matching_indices else 1 - int(target_output)
        circuits.append(
            _sample_circuit_with_output(
                rng,
                item_id=f"circuit_{index + 1}",
                label=str(label),
                input_count_min=int(input_count_min),
                input_count_max=int(input_count_max),
                gate_count_min=int(gate_count_min),
                gate_count_max=int(gate_count_max),
                target_output_value=int(desired_output),
            )
        )
    annotation_output_ids = tuple(f"{circuit.item_id}_output" for circuit in circuits if int(circuit.output_value or 0) == int(target_output))
    return _Dataset(
        task_id=OUTPUT_VALUE_COUNT_TASK_ID,
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        target_output_value=int(target_output),
        answer_type="integer",
        answer_value=int(answer),
        target_answer_support=tuple(range(int(answer_min), int(answer_max) + 1)),
        circuits=tuple(circuits),
        source_circuit=None,
        candidates=tuple(),
        annotation_output_ids=tuple(annotation_output_ids),
        annotation_item_ids=tuple(),
        metadata={
            "circuit_count": int(circuit_count),
            "matching_circuit_labels": [str(circuit.label) for circuit in circuits if int(circuit.output_value or 0) == int(target_output)],
            "target_output_value": int(target_output),
            "supported_gate_types": list(SUPPORTED_LOGIC_GATE_TYPES),
        },
    )


def _assignment_to_values(bits: Sequence[int]) -> dict[str, int]:
    return {str(label): int(value) for label, value in zip(INPUT_LABELS, bits)}


def _all_three_input_assignments() -> tuple[dict[str, int], ...]:
    return tuple(_assignment_to_values(bits) for bits in product((0, 1), repeat=3))


def _build_exact_assignment_circuit(*, target_output_value: int, correct_values: Mapping[str, int]) -> LogicCircuitSpec:
    inputs = tuple(LogicInputSpec(item_id=f"source_in_{label}", label=str(label), value=None) for label in INPUT_LABELS)
    gates: list[LogicGateSpec] = []
    literal_signals: list[str] = []
    for label in INPUT_LABELS:
        input_signal = f"source_in_{label}"
        if int(correct_values[str(label)]) == 1:
            literal_signals.append(str(input_signal))
        else:
            output_signal = f"source_not_{label}"
            gates.append(
                LogicGateSpec(
                    item_id=f"source_gate_not_{label}",
                    gate_type="NOT",
                    input_signal_ids=(str(input_signal),),
                    output_signal_id=str(output_signal),
                )
            )
            literal_signals.append(str(output_signal))
    gates.append(
        LogicGateSpec(
            item_id="source_gate_and_1",
            gate_type="AND",
            input_signal_ids=(str(literal_signals[0]), str(literal_signals[1])),
            output_signal_id="source_and_1",
        )
    )
    final_gate_type = "AND" if int(target_output_value) == 1 else "NAND"
    gates.append(
        LogicGateSpec(
            item_id="source_gate_final",
            gate_type=str(final_gate_type),
            input_signal_ids=("source_and_1", str(literal_signals[2])),
            output_signal_id="source_out",
        )
    )
    return LogicCircuitSpec(
        item_id="source_circuit",
        label="",
        inputs=tuple(inputs),
        gates=tuple(gates),
        output_signal_id="source_out",
        output_value=None,
        role="source_circuit",
    )


def _build_assignment_dataset(
    *,
    instance_seed: int,
    scene_variant: str,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    query_id: str,
) -> _Dataset:
    rng = spawn_rng(int(instance_seed), f"{SATISFYING_ASSIGNMENT_TASK_ID}.dataset")
    target_output = _target_output_value(str(query_id))
    option_count = int(params.get("option_count", gen_defaults.get("option_count", 6)))
    if int(option_count) != 6:
        raise ValueError("logic-gate assignment task requires exactly six visual options")
    labels = tuple(str(label) for label in OPTION_LABELS)
    answer_label = str(params.get("answer_label", params.get("correct_label", labels[int(rng.randrange(len(labels)))]))).upper()
    if answer_label not in labels:
        raise ValueError(f"answer_label must be one of {labels}")
    assignments = list(_all_three_input_assignments())
    correct_values = dict(params.get("correct_values", rng.choice(assignments)))
    correct_values = {str(key): int(value) for key, value in correct_values.items()}
    if set(correct_values) != set(INPUT_LABELS) or any(int(value) not in {0, 1} for value in correct_values.values()):
        raise ValueError("correct_values must provide x/y/z values in {0,1}")
    circuit = _build_exact_assignment_circuit(
        target_output_value=int(target_output),
        correct_values=correct_values,
    )
    distractor_assignments = [assignment for assignment in assignments if dict(assignment) != dict(correct_values)]
    rng.shuffle(distractor_assignments)
    selected_distractors = distractor_assignments[:5]
    candidates: list[CandidateAssignmentSpec] = []
    distractor_index = 0
    for label in labels:
        if str(label) == str(answer_label):
            values = dict(correct_values)
            is_correct = True
        else:
            values = dict(selected_distractors[int(distractor_index)])
            distractor_index += 1
            is_correct = False
        output_value = int(evaluate_logic_circuit(circuit, values))
        candidates.append(
            CandidateAssignmentSpec(
                item_id=f"option_{label}",
                label=str(label),
                values=dict(values),
                output_value=int(output_value),
                is_correct=bool(is_correct),
            )
        )
    correct_candidates = [candidate for candidate in candidates if int(candidate.output_value) == int(target_output)]
    if len(correct_candidates) != 1 or str(correct_candidates[0].label) != str(answer_label):
        raise RuntimeError("logic-gate assignment construction failed to make a unique correct option")
    return _Dataset(
        task_id=SATISFYING_ASSIGNMENT_TASK_ID,
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        target_output_value=int(target_output),
        answer_type="option_letter",
        answer_value=str(answer_label),
        target_answer_support=labels,
        circuits=tuple(),
        source_circuit=circuit,
        candidates=tuple(candidates),
        annotation_output_ids=tuple(),
        annotation_item_ids=("source_circuit", f"option_{answer_label}"),
        metadata={
            "target_output_value": int(target_output),
            "correct_assignment": dict(correct_values),
            "correct_option_label": str(answer_label),
            "option_assignments": {
                str(candidate.label): {str(key): int(value) for key, value in candidate.values.items()}
                for candidate in candidates
            },
            "supported_gate_types": list(SUPPORTED_LOGIC_GATE_TYPES),
        },
    )


def _build_prompt(
    *,
    dataset: _Dataset,
    prompt_defaults: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
    query_id = str(dataset.query_id)
    scene_variant = str(dataset.scene_variant)
    required_keys = (
        "bundle_id",
        "scene_key",
        "task_key",
        "json_output_contract",
        "json_output_contract_answer_only",
        f"object_description_{scene_variant}",
        f"answer_hint_{query_id}",
        f"annotation_hint_{query_id}",
        f"json_example_{query_id}",
        f"json_example_answer_only_{query_id}",
    )
    prompt_values = required_group_defaults(prompt_defaults, required_keys, context=f"prompt defaults for {dataset.task_id}")
    slots = {
        "object_description": str(prompt_values[f"object_description_{scene_variant}"]),
        "json_output_contract": str(prompt_values["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_values["json_output_contract_answer_only"]),
        "annotation_hint": str(prompt_values[f"annotation_hint_{query_id}"]),
        "answer_hint": str(prompt_values[f"answer_hint_{query_id}"]),
        "json_example": str(prompt_values[f"json_example_{query_id}"]),
        "json_example_answer_only": str(prompt_values[f"json_example_answer_only_{query_id}"]),
    }
    prompt_selection = render_task_prompt_variants(
        domain="symbolic",
        scene_id="notation",
        bundle_id=str(prompt_values["bundle_id"]),
        scene_key=str(prompt_values["scene_key"]),
        task_key=str(prompt_values["task_key"]),
        query_key=str(query_id),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        slots=slots,
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
    return str(prompt_artifacts.prompt), dict(prompt_artifacts.prompt_variants), {
        "prompt_variant": dict(prompt_artifacts.prompt_variant),
        "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
        "prompt_variants_for_trace": dict(prompt_artifacts.prompt_variants_for_trace),
        "bundle_id": str(prompt_values["bundle_id"]),
    }


def _round_points(points: Sequence[Sequence[float]]) -> list[list[float]]:
    return [[round(float(point[0]), 3), round(float(point[1]), 3)] for point in points]


def _round_bbox_map(mapping: Mapping[str, Sequence[float]]) -> dict[str, list[float]]:
    return {str(key): [round(float(value), 3) for value in bbox] for key, bbox in mapping.items()}


def _scene_style_load(scene_variant: str) -> float:
    return {"clean_worksheet": 0.18, "notebook_problem": 0.24, "exam_scan": 0.28}.get(str(scene_variant), 0.22)


def _circuit_trace(circuit: LogicCircuitSpec) -> dict[str, Any]:
    return {
        "item_id": str(circuit.item_id),
        "label": str(circuit.label),
        "role": str(circuit.role),
        "inputs": [
            {
                "item_id": str(input_spec.item_id),
                "label": str(input_spec.label),
                "value": None if input_spec.value is None else int(input_spec.value),
            }
            for input_spec in circuit.inputs
        ],
        "gates": [
            {
                "item_id": str(gate.item_id),
                "gate_type": str(gate.gate_type),
                "input_signal_ids": [str(signal_id) for signal_id in gate.input_signal_ids],
                "output_signal_id": str(gate.output_signal_id),
            }
            for gate in circuit.gates
        ],
        "output_signal_id": str(circuit.output_signal_id),
        "output_value": None if circuit.output_value is None else int(circuit.output_value),
    }


class _LogicGateBaseTask:
    domain = "symbolic"
    scene_id = "notation"
    default_dataset_enabled = True
    task_id: str
    supported_query_ids: tuple[str, ...]

    def _build_dataset(
        self,
        *,
        instance_seed: int,
        scene_variant: str,
        params: Mapping[str, Any],
        gen_defaults: Mapping[str, Any],
        query_id: str,
    ) -> _Dataset:
        raise NotImplementedError

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_id, query_probabilities = _resolve_query_id(
            params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=str(self.task_id),
            supported_query_ids=tuple(self.supported_query_ids),
        )
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(
            params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=str(self.task_id),
        )
        last_error: Exception | None = None
        dataset: _Dataset | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            try:
                dataset = self._build_dataset(
                    instance_seed=int(instance_seed) + int(attempt_index),
                    scene_variant=str(scene_variant),
                    params=params,
                    gen_defaults=gen_defaults,
                    query_id=str(query_id),
                )
                break
            except Exception as exc:
                last_error = exc
        if dataset is None:
            raise RuntimeError(f"failed to generate logic-gate instance for {self.task_id}") from last_error

        render_params = _resolve_render_params(render_defaults)
        scene_style, scene_style_meta = resolve_symbolic_scene_style(
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.logic_gate_background",
        )
        background, background_meta = make_symbolic_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=scene_style,
        )
        if str(dataset.task_id) == OUTPUT_VALUE_COUNT_TASK_ID:
            rendered_scene = render_logic_gate_count_scene(
                background,
                circuits=dataset.circuits,
                params=render_params,
                style=scene_style,
            )
        else:
            if dataset.source_circuit is None:
                raise RuntimeError("logic-gate assignment task requires a source circuit")
            rendered_scene = render_logic_assignment_scene(
                background,
                circuit=dataset.source_circuit,
                candidates=dataset.candidates,
                params=render_params,
                style=scene_style,
            )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        prompt, prompt_variants, prompt_meta = _build_prompt(
            dataset=dataset,
            prompt_defaults=prompt_defaults,
            instance_seed=int(instance_seed),
        )
        item_bboxes = _round_bbox_map(rendered_scene.item_bboxes)
        output_points = {
            str(key): [round(float(value[0]), 3), round(float(value[1]), 3)]
            for key, value in rendered_scene.output_points.items()
        }
        signal_points = {
            str(key): [round(float(value[0]), 3), round(float(value[1]), 3)]
            for key, value in rendered_scene.signal_points.items()
        }

        if str(dataset.task_id) == OUTPUT_VALUE_COUNT_TASK_ID:
            annotation_points = _round_points([output_points[str(point_id)] for point_id in dataset.annotation_output_ids])
            annotation_gt = TypedValue(type="point_set", value=list(annotation_points))
            projected_annotation = {
                "type": "point_set",
                "point_set": list(annotation_points),
                "pixel_point_set": list(annotation_points),
                "value": list(annotation_points),
            }
            witness_symbolic = {"type": "point_set", "value": list(annotation_points)}
            annotation_source = "output_points_px"
        else:
            keyed_bboxes = {
                "source_circuit": list(item_bboxes[str(dataset.annotation_item_ids[0])]),
                "selected_option": list(item_bboxes[str(dataset.annotation_item_ids[1])]),
            }
            annotation_gt = TypedValue(type="keyed_bbox_map", value=dict(keyed_bboxes))
            projected_annotation = {
                "type": "keyed_bbox_map",
                "keyed_bbox_map": dict(keyed_bboxes),
                "pixel_keyed_bbox_map": dict(keyed_bboxes),
                "value": dict(keyed_bboxes),
            }
            witness_symbolic = {"type": "keyed_bbox_map", "value": dict(keyed_bboxes)}
            annotation_source = "item_bboxes_px"

        answer_value = int(dataset.answer_value) if str(dataset.answer_type) == "integer" else str(dataset.answer_value)
        answer_gt = TypedValue(type=str(dataset.answer_type), value=answer_value)
        query_params = {
            "query_id": str(query_id),
            "internal_query_id": str(dataset.query_id),
            "query_id_probabilities": {"default": 1.0},
            "internal_query_id_probabilities": dict(query_probabilities),
            "scene_id": SCENE_ID,
            "scene_variant": str(scene_variant),
            "scene_variant_probabilities": dict(scene_variant_probabilities),
            "target_output_value": int(dataset.target_output_value),
            "target_answer_support": list(dataset.target_answer_support),
        }
        trace_payload = {
            "scene_ir": {
                "scene_kind": SCENE_ID,
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": str(dataset.query_id),
                    "scene_id": SCENE_ID,
                    "scene_variant": str(scene_variant),
                    "target_output_value": int(dataset.target_output_value),
                    "answer_value": answer_value,
                },
            },
            "query_spec": {
                "query_id": str(dataset.query_id),
                "internal_query_id": str(dataset.query_id),
                "template_id": str(prompt_meta["bundle_id"]),
                "prompt_variant": dict(prompt_meta["prompt_variant"]),
                "prompt_variant_active_key": str(prompt_meta["prompt_variant_active_key"]),
                "prompt_variants": dict(prompt_meta["prompt_variants_for_trace"]),
                "params": dict(query_params),
            },
            "render_spec": {
                "scene_id": SCENE_ID,
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "scene_style": dict(scene_style_meta),
                "logic_gate_style": dict(rendered_scene.style_metadata),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
            },
            "render_map": {
                "image_id": "img0",
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "item_bboxes_px": dict(item_bboxes),
                "output_points_px": dict(output_points),
                "signal_points_px": dict(signal_points),
                "annotation_source": str(annotation_source),
            },
            "execution_trace": {
                **dict(query_params),
                "answer_value": answer_value,
                "answer_type": str(dataset.answer_type),
                "target_output_value": int(dataset.target_output_value),
                "annotation_output_ids": [str(item) for item in dataset.annotation_output_ids],
                "annotation_item_ids": [str(item) for item in dataset.annotation_item_ids],
                "logic_gate_metadata": dict(dataset.metadata),
                "circuits": [_circuit_trace(circuit) for circuit in dataset.circuits],
                "source_circuit": None if dataset.source_circuit is None else _circuit_trace(dataset.source_circuit),
                "candidates": [
                    {
                        "item_id": str(candidate.item_id),
                        "label": str(candidate.label),
                        "values": {str(key): int(value) for key, value in candidate.values.items()},
                        "output_value": int(candidate.output_value),
                        "is_correct": bool(candidate.is_correct),
                    }
                    for candidate in dataset.candidates
                ],
                "question_format": str(dataset.query_id),
            },
            "witness_symbolic": dict(witness_symbolic),
            "projected_annotation": dict(projected_annotation),
            "answer_gt": answer_gt.to_dict(),
            "annotation_gt": annotation_gt.to_dict(),
        }
        visual_count = len(rendered_scene.entities)
        reasoning_load = 0.40 if str(dataset.task_id) == OUTPUT_VALUE_COUNT_TASK_ID else 0.48
        return TaskOutput(
            prompt=str(prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(dataset.query_id),
            prompt_variants=dict(prompt_variants),
        )


@register_task
class SymbolicLogicGateOutputValueCountTask(_LogicGateBaseTask):
    task_id = OUTPUT_VALUE_COUNT_TASK_ID
    supported_query_ids = COUNT_QUERY_IDS

    def _build_dataset(
        self,
        *,
        instance_seed: int,
        scene_variant: str,
        params: Mapping[str, Any],
        gen_defaults: Mapping[str, Any],
        query_id: str,
    ) -> _Dataset:
        return _build_count_dataset(
            instance_seed=int(instance_seed),
            scene_variant=str(scene_variant),
            params=params,
            gen_defaults=gen_defaults,
            query_id=str(query_id),
        )


@register_task
class SymbolicLogicGateSatisfyingAssignmentLabelTask(_LogicGateBaseTask):
    task_id = SATISFYING_ASSIGNMENT_TASK_ID
    supported_query_ids = ASSIGNMENT_QUERY_IDS

    def _build_dataset(
        self,
        *,
        instance_seed: int,
        scene_variant: str,
        params: Mapping[str, Any],
        gen_defaults: Mapping[str, Any],
        query_id: str,
    ) -> _Dataset:
        return _build_assignment_dataset(
            instance_seed=int(instance_seed),
            scene_variant=str(scene_variant),
            params=params,
            gen_defaults=gen_defaults,
            query_id=str(query_id),
        )


__all__ = [
    "ASSIGNMENT_OUTPUTS_ONE_QUERY_ID",
    "ASSIGNMENT_OUTPUTS_ZERO_QUERY_ID",
    "COUNT_QUERY_IDS",
    "INPUT_LABELS",
    "SymbolicLogicGateOutputValueCountTask",
    "SymbolicLogicGateSatisfyingAssignmentLabelTask",
    "OPTION_LABELS",
    "OUTPUT_ONE_COUNT_QUERY_ID",
    "OUTPUT_VALUE_COUNT_TASK_ID",
    "OUTPUT_ZERO_COUNT_QUERY_ID",
    "SATISFYING_ASSIGNMENT_TASK_ID",
    "SCENE_ID",
    "SUPPORTED_LOGIC_GATE_TYPES",
    "TASK_ID",
]

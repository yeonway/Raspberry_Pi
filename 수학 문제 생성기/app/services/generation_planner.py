import random
from dataclasses import dataclass, field
from typing import Literal

from app.services.problem_formats import FormatOption


GenerationMode = Literal["selected", "random", "mixed_random", "instruction_guided"]


@dataclass(frozen=True)
class GenerateRequest:
    subject_id: int
    textbook_id: int | None
    unit_id: int
    difficulty_level: int
    requested_count: int
    generation_mode: GenerationMode
    selected_format_codes: list[str] = field(default_factory=list)
    format_weights: dict[str, float] = field(default_factory=dict)
    generation_instruction: str = ""
    random_seed: int | None = None
    explanation_style: str = "normal"
    include_answers: bool = True
    title: str | None = None


@dataclass(frozen=True)
class ProblemSlot:
    slot_index: int
    format_code: str
    difficulty_level: int
    validation_method: str
    rendering_type: str
    reason: str


@dataclass(frozen=True)
class ProblemGenerationPlan:
    subject_id: int
    textbook_id: int | None
    unit_id: int
    generation_mode: GenerationMode
    requested_count: int
    problem_slots: list[ProblemSlot]
    warnings: list[str] = field(default_factory=list)


class GenerationPlanner:
    def build_plan(self, request: GenerateRequest, allowed_formats: list[FormatOption]) -> ProblemGenerationPlan:
        warnings: list[str] = []
        available = _filter_by_difficulty(allowed_formats, request.difficulty_level)
        if not available:
            warnings.append("No problem formats are allowed for this unit and difficulty.")
            return self._plan(request, [], warnings)

        if request.generation_mode == "selected":
            codes = self._plan_selected(request, available, warnings)
        elif request.generation_mode == "random":
            codes = self._plan_random(request, available)
        elif request.generation_mode == "mixed_random":
            codes = self._plan_mixed_random(request, available, warnings)
        elif request.generation_mode == "instruction_guided":
            codes = self._plan_instruction_guided(request, available, warnings)
        else:
            warnings.append(f"Unsupported generation_mode: {request.generation_mode}")
            codes = []

        options_by_code = {option.code: option for option in available}
        slots = [
            ProblemSlot(
                slot_index=index,
                format_code=code,
                difficulty_level=request.difficulty_level,
                validation_method=options_by_code[code].validation_method,
                rendering_type=options_by_code[code].rendering_type,
                reason=self._reason(request.generation_mode, code),
            )
            for index, code in enumerate(codes[: request.requested_count], start=1)
            if code in options_by_code
        ]
        return self._plan(request, slots, warnings)

    def _plan_selected(
        self,
        request: GenerateRequest,
        available: list[FormatOption],
        warnings: list[str],
    ) -> list[str]:
        available_codes = {option.code for option in available}
        selected = [code for code in request.selected_format_codes if code in available_codes]
        rejected = [code for code in request.selected_format_codes if code not in available_codes]
        for code in rejected:
            warnings.append(f"Format '{code}' is not allowed for this unit and difficulty.")
        if not selected:
            warnings.append("No selected format is allowed.")
            return []
        return [selected[index % len(selected)] for index in range(request.requested_count)]

    def _plan_random(self, request: GenerateRequest, available: list[FormatOption]) -> list[str]:
        rng = random.Random(request.random_seed)
        codes = [option.code for option in available]
        weights = [max(option.default_weight, 0.0) for option in available]
        if sum(weights) <= 0:
            weights = [1.0 for _ in available]
        return rng.choices(codes, weights=weights, k=request.requested_count)

    def _plan_mixed_random(
        self,
        request: GenerateRequest,
        available: list[FormatOption],
        warnings: list[str],
    ) -> list[str]:
        available_codes = {option.code for option in available}
        weighted_items = [
            (code, weight)
            for code, weight in request.format_weights.items()
            if code in available_codes and weight > 0
        ]
        rejected = [code for code, weight in request.format_weights.items() if code not in available_codes and weight > 0]
        for code in rejected:
            warnings.append(f"Format '{code}' is not allowed for this unit and difficulty.")

        if not weighted_items:
            warnings.append("No mixed_random weights reference allowed formats.")
            return []

        counts = _weights_to_counts(weighted_items, request.requested_count)
        codes: list[str] = []
        for code, count in counts:
            codes.extend([code] * count)
        return codes

    def _plan_instruction_guided(
        self,
        request: GenerateRequest,
        available: list[FormatOption],
        warnings: list[str],
    ) -> list[str]:
        available_codes = {option.code for option in available}
        requested_codes = _detect_instruction_formats(request.generation_instruction)
        allowed_requested = [code for code in requested_codes if code in available_codes]
        rejected = [code for code in requested_codes if code not in available_codes]
        for code in rejected:
            warnings.append(f"Instruction requested '{code}', but it is not allowed for this unit and difficulty.")

        if allowed_requested:
            return [allowed_requested[index % len(allowed_requested)] for index in range(request.requested_count)]

        warnings.append("No allowed format was detected from the instruction; falling back to random planning.")
        return self._plan_random(request, available)

    def _reason(self, mode: GenerationMode, code: str) -> str:
        if mode == "selected":
            return f"User selected {code}."
        if mode == "random":
            return f"Randomly selected {code} from allowed unit formats."
        if mode == "mixed_random":
            return f"Selected {code} from requested mixed_random weights."
        return f"Selected {code} based on the user instruction and allowed formats."

    def _plan(
        self,
        request: GenerateRequest,
        slots: list[ProblemSlot],
        warnings: list[str],
    ) -> ProblemGenerationPlan:
        return ProblemGenerationPlan(
            subject_id=request.subject_id,
            textbook_id=request.textbook_id,
            unit_id=request.unit_id,
            generation_mode=request.generation_mode,
            requested_count=request.requested_count,
            problem_slots=slots,
            warnings=warnings,
        )


def _filter_by_difficulty(allowed_formats: list[FormatOption], difficulty_level: int) -> list[FormatOption]:
    return [
        option
        for option in allowed_formats
        if option.min_difficulty <= difficulty_level <= option.max_difficulty
    ]


def _weights_to_counts(weighted_items: list[tuple[str, float]], requested_count: int) -> list[tuple[str, int]]:
    total_weight = sum(weight for _, weight in weighted_items)
    raw_counts = [(code, (weight / total_weight) * requested_count) for code, weight in weighted_items]
    floor_counts = [(code, int(raw_count), raw_count - int(raw_count)) for code, raw_count in raw_counts]
    remaining = requested_count - sum(count for _, count, _ in floor_counts)
    ranked = sorted(enumerate(floor_counts), key=lambda item: (-item[1][2], item[0]))
    counts = [[code, count] for code, count, _ in floor_counts]
    for index, _ in ranked[:remaining]:
        counts[index][1] += 1
    return [(str(code), int(count)) for code, count in counts]


def _detect_instruction_formats(instruction: str) -> list[str]:
    text = instruction.lower()
    detections: list[tuple[str, list[str]]] = [
        ("table_interpretation", ["표", "table"]),
        ("graph", ["그래프", "graph", "기울기", "slope"]),
        ("geometry", ["도형", "삼각형", "사각형", "원", "넓이", "geometry"]),
        ("proof", ["증명", "prove", "proof"]),
        ("descriptive", ["서술", "설명", "이유", "describe", "explain"]),
        ("solution_steps", ["풀이", "과정", "단계", "steps"]),
        ("multiple_choice", ["객관식", "선택", "보기", "multiple choice"]),
        ("short_answer", ["단답", "답만", "short answer"]),
    ]
    result: list[str] = []
    for code, keywords in detections:
        if any(keyword in text for keyword in keywords):
            result.append(code)
    return result

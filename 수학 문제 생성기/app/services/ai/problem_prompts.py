from app.models import Subject, Textbook, Unit
from app.services.generation_planner import ProblemSlot


def build_problem_prompt(
    *,
    subject: Subject,
    textbook: Textbook | None,
    unit: Unit,
    slot: ProblemSlot,
    generation_instruction: str,
    explanation_style: str,
    include_answers: bool,
) -> str:
    textbook_line = "교과서 메타데이터: 공통 단원 기준"
    if textbook is not None:
        textbook_line = (
            f"교과서 메타데이터: 출판사={textbook.publisher}, 제목={textbook.title}, "
            f"학년={textbook.grade_label}, 교육과정={textbook.curriculum_version}"
        )

    answer_policy = "정답과 해설을 포함한다." if include_answers else "answer_text와 explanation_text는 빈 문자열로 둔다."
    user_instruction = generation_instruction.strip() or "추가 요청 없음"

    return f"""
너는 한국어 중학교 수학 문제를 새로 만드는 출제 보조자다.
아래 범위 안에서 문제 1개만 생성한다.

범위:
- 과목: {subject.name}
- {textbook_line}
- 학년: {unit.grade_label}
- 단원: {unit.name}
- 학습목표: {unit.learning_goal}
- 문제 형식: {slot.format_code}
- 난이도: {slot.difficulty_level}
- 해설 스타일: {explanation_style}
- 정답 정책: {answer_policy}
- 사용자 요청: {user_instruction}

저작권 및 안전 규칙:
- 실제 교과서 문장, 본문, 예제, 문항을 복사하거나 변형 복제하지 않는다.
- 출판사별 고유 문항 스타일이나 문장을 재현하지 않는다.
- 단원명과 학습목표 메타데이터만 참고해 새 숫자, 새 상황, 새 문장으로 만든다.
- 그래프, 표, 도형은 AI 이미지로 만들지 않는다. renderer가 그릴 수 있는 구조화 데이터만 제공한다.
- 한국어 문장을 자연스럽게 작성한다.
- 문제의 조건은 모호하지 않아야 하며 정답이 하나로 결정되어야 한다.

형식별 필수 요구:
- multiple_choice:
  - choices는 4개 또는 5개.
  - correct_index는 0부터 시작하는 정답 보기 인덱스.
  - answer_text는 정답 보기의 실제 문자열과 일치.
  - 오답 보기는 정답과 중복되지 않으며 그럴듯해야 한다.
- short_answer:
  - answer_text 필수.
  - input_schema에는 equation, expression, variables, given_value 등 자동 검증에 필요한 정보를 넣는다.
- descriptive:
  - 모범답안, 핵심 키워드, rubric을 포함한다.
  - validation_method는 rubric 또는 manual_review.
- graph:
  - rendering_type은 graph_svg.
  - rendering_payload에는 graph_type, equation, x_range, y_range, points, show_grid를 넣는다.
- table_interpretation:
  - rendering_type은 html_table.
  - rendering_payload에는 headers와 rows를 넣는다.
- geometry:
  - rendering_type은 geometry_svg.
  - rendering_payload에는 shape, width, height, radius, labels 중 필요한 값을 넣는다.
  - 초기 MVP는 rectangle, triangle, circle 정도만 사용한다.
- proof:
  - validation_method는 manual_review.
  - rubric을 포함한다.

검증 힌트:
- 자동 검증 가능한 경우 validation_method를 arithmetic, linear_equation, system_equation, function_value, multiple_choice, graph, table_interpretation 중 하나로 둔다.
- 자동 검증이 애매하면 manual_review 또는 rubric으로 둔다.

출력 규칙:
- 반드시 JSON object만 출력한다.
- markdown, 코드블록, 설명 문장, 앞뒤 인사말을 출력하지 않는다.
- 요청된 JSON schema의 필드를 빠짐없이 채운다.
""".strip()

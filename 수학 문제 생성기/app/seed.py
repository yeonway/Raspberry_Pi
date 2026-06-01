import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ProblemFormat, Subject, Textbook, Unit, UnitAllowedFormat


def _get_subject(session: Session, code: str) -> Subject | None:
    return session.scalar(select(Subject).where(Subject.code == code))


def _get_format(session: Session, code: str) -> ProblemFormat | None:
    return session.scalar(select(ProblemFormat).where(ProblemFormat.code == code))


def _get_textbook(
    session: Session,
    subject_id: int,
    publisher: str,
    title: str,
    grade_label: str,
    curriculum_version: str,
) -> Textbook | None:
    return session.scalar(
        select(Textbook).where(
            Textbook.subject_id == subject_id,
            Textbook.publisher == publisher,
            Textbook.title == title,
            Textbook.grade_label == grade_label,
            Textbook.curriculum_version == curriculum_version,
        )
    )


def _get_unit(session: Session, subject_id: int, grade_label: str, name: str) -> Unit | None:
    return session.scalar(
        select(Unit).where(
            Unit.subject_id == subject_id,
            Unit.textbook_id.is_(None),
            Unit.parent_id.is_(None),
            Unit.grade_label == grade_label,
            Unit.name == name,
        )
    )


def _get_allowed_format(session: Session, unit_id: int, problem_format_id: int) -> UnitAllowedFormat | None:
    return session.scalar(
        select(UnitAllowedFormat).where(
            UnitAllowedFormat.unit_id == unit_id,
            UnitAllowedFormat.problem_format_id == problem_format_id,
        )
    )


def seed_initial_data(session: Session) -> None:
    subject = _get_subject(session, "math")
    if subject is None:
        subject = Subject(code="math", name="수학", description="중학교 수학 문제 생성을 위한 기본 과목")
        session.add(subject)
        session.flush()
    else:
        subject.name = "수학"
        subject.description = "중학교 수학 문제 생성을 위한 기본 과목"

    _seed_problem_formats(session)
    _seed_textbooks(session, subject.id)
    _seed_units(session, subject.id)
    session.commit()


def _seed_problem_formats(session: Session) -> None:
    format_specs = [
        {
            "code": "multiple_choice",
            "name": "객관식",
            "description": "보기 중 정답을 선택하는 형식",
            "requires_choices": True,
            "supports_auto_validation": True,
            "default_validation_method": "exact_match",
        },
        {
            "code": "short_answer",
            "name": "단답형",
            "description": "짧은 수식 또는 값을 답하는 형식",
            "supports_auto_validation": True,
            "default_validation_method": "sympy_or_exact",
        },
        {
            "code": "free_response",
            "name": "주관식",
            "description": "자유롭게 답안을 작성하는 형식",
            "supports_auto_validation": False,
            "default_validation_method": "manual",
        },
        {
            "code": "descriptive",
            "name": "서술형",
            "description": "풀이 이유와 설명을 함께 작성하는 형식",
            "requires_rubric": True,
            "supports_auto_validation": False,
            "default_validation_method": "manual",
        },
        {
            "code": "solution_steps",
            "name": "풀이과정형",
            "description": "중간 풀이 과정을 단계별로 확인하는 형식",
            "requires_rubric": True,
            "supports_auto_validation": False,
            "default_validation_method": "manual_review",
        },
        {
            "code": "graph",
            "name": "그래프형",
            "description": "결정적 렌더링 그래프를 포함할 수 있는 형식",
            "supports_auto_validation": True,
            "supports_rendering": True,
            "default_validation_method": "numeric_or_symbolic",
            "default_rendering_type": "graph_svg",
        },
        {
            "code": "table_interpretation",
            "name": "표해석형",
            "description": "표를 읽고 관계나 값을 해석하는 형식",
            "supports_auto_validation": True,
            "supports_rendering": True,
            "default_validation_method": "exact_match",
            "default_rendering_type": "html_table",
        },
        {
            "code": "geometry",
            "name": "도형형",
            "description": "간단한 도형 SVG 렌더링을 포함할 수 있는 형식",
            "supports_auto_validation": False,
            "supports_rendering": True,
            "default_validation_method": "manual_review",
            "default_rendering_type": "geometry_svg",
        },
        {
            "code": "proof",
            "name": "증명형",
            "description": "명제를 논리적으로 증명하는 형식",
            "requires_rubric": True,
            "supports_auto_validation": False,
            "default_validation_method": "manual_review",
        },
        {
            "code": "mixed",
            "name": "혼합형",
            "description": "여러 문제 형식을 혼합해 생성하는 선택 옵션",
            "supports_auto_validation": False,
            "default_validation_method": "delegated",
        },
    ]
    for spec in format_specs:
        problem_format = _get_format(session, spec["code"])
        if problem_format is None:
            session.add(ProblemFormat(**spec))
            continue
        for key, value in spec.items():
            setattr(problem_format, key, value)


def _seed_textbooks(session: Session, subject_id: int) -> None:
    textbook_specs = [
        ("미래형출판", "중학교 수학 메타 예시 1", "중1", "2022 개정"),
        ("탐구교육", "중학교 수학 메타 예시 2", "중2", "2022 개정"),
        ("배움서림", "중학교 수학 메타 예시 3", "중3", "2022 개정"),
    ]
    for publisher, title, grade_label, curriculum_version in textbook_specs:
        textbook = _get_textbook(session, subject_id, publisher, title, grade_label, curriculum_version)
        if textbook is None:
            session.add(
                Textbook(
                    subject_id=subject_id,
                    publisher=publisher,
                    title=title,
                    grade_label=grade_label,
                    curriculum_version=curriculum_version,
                    metadata_json=_metadata(source="sample_metadata_only"),
                )
            )


def _seed_units(session: Session, subject_id: int) -> None:
    unit_specs = [
        ("중1", "1학기", "수와 연산", "소인수분해", "자연수를 소인수분해하고 약수와 배수 관계를 설명한다.", 110),
        ("중1", "1학기", "수와 연산", "정수와 유리수", "정수와 유리수의 뜻을 이해하고 사칙계산을 수행한다.", 120),
        ("중1", "1학기", "변화와 관계", "문자와 식", "문자를 사용해 수량 관계를 식으로 표현하고 식의 값을 구한다.", 130),
        ("중1", "1학기", "변화와 관계", "일차방정식", "일차방정식의 뜻을 이해하고 해를 구해 실생활 문제에 적용한다.", 140),
        ("중1", "1학기", "변화와 관계", "좌표평면과 그래프", "순서쌍과 좌표를 이해하고 간단한 그래프를 해석한다.", 150),
        ("중1", "2학기", "도형과 측정", "기본 도형", "점, 선, 각의 관계와 위치 관계를 이해한다.", 210),
        ("중1", "2학기", "도형과 측정", "작도와 합동", "기본 작도와 삼각형의 합동 조건을 이해한다.", 220),
        ("중1", "2학기", "도형과 측정", "평면도형", "다각형과 원의 성질을 이용해 길이와 각을 구한다.", 230),
        ("중1", "2학기", "도형과 측정", "입체도형", "기둥, 뿔, 구의 성질과 겉넓이, 부피를 이해한다.", 240),
        ("중1", "2학기", "자료와 가능성", "자료의 정리와 해석", "자료를 표와 그래프로 정리하고 분포의 특징을 해석한다.", 250),
        ("중2", "1학기", "수와 연산", "유리수와 순환소수", "유리수와 순환소수의 관계를 이해하고 표현한다.", 310),
        ("중2", "1학기", "변화와 관계", "식의 계산", "다항식과 단항식의 계산 원리를 이해하고 식을 정리한다.", 320),
        ("중2", "1학기", "변화와 관계", "일차부등식", "일차부등식의 해를 구하고 수직선에 나타낸다.", 330),
        ("중2", "1학기", "변화와 관계", "연립방정식", "미지수가 두 개인 연립일차방정식을 풀고 문제 상황을 모델링한다.", 340),
        ("중2", "1학기", "변화와 관계", "일차함수", "일차함수의 그래프와 식의 관계를 이해하고 변화율을 해석한다.", 350),
        ("중2", "2학기", "도형과 측정", "삼각형의 성질", "삼각형의 여러 성질을 이용해 각과 길이를 구한다.", 410),
        ("중2", "2학기", "도형과 측정", "사각형의 성질", "평행사변형과 여러 사각형의 성질을 이해한다.", 420),
        ("중2", "2학기", "도형과 측정", "도형의 닮음", "닮음비를 이용해 도형의 길이와 넓이를 구한다.", 430),
        ("중2", "2학기", "도형과 측정", "피타고라스 정리", "직각삼각형에서 세 변의 길이 사이의 관계를 활용한다.", 440),
        ("중2", "2학기", "자료와 가능성", "확률", "경우의 수와 확률의 뜻을 이해하고 간단한 확률을 구한다.", 450),
        ("중3", "1학기", "수와 연산", "제곱근과 실수", "제곱근과 실수의 뜻을 이해하고 근호를 포함한 식을 계산한다.", 510),
        ("중3", "1학기", "변화와 관계", "다항식의 곱셈과 인수분해", "다항식의 곱셈 공식과 인수분해를 활용한다.", 520),
        ("중3", "1학기", "변화와 관계", "이차방정식", "이차방정식의 해를 다양한 방법으로 구하고 의미를 해석한다.", 530),
        ("중3", "1학기", "변화와 관계", "이차함수", "이차함수의 그래프 특징을 식과 연결해 분석한다.", 540),
        ("중3", "2학기", "도형과 측정", "삼각비", "직각삼각형에서 삼각비를 이해하고 길이와 각을 구한다.", 610),
        ("중3", "2학기", "도형과 측정", "원의 성질", "원과 직선, 원주각의 성질을 이용해 각을 구한다.", 620),
        ("중3", "2학기", "자료와 가능성", "대푯값과 산포도", "자료의 중심과 흩어진 정도를 비교하고 해석한다.", 630),
    ]
    for grade_label, semester_label, area, name, learning_goal, sort_order in unit_specs:
        unit = _get_unit(session, subject_id, grade_label, name)
        metadata = _metadata(source="curriculum_metadata_only", semester_label=semester_label, area=area)
        if unit is None:
            unit = Unit(
                subject_id=subject_id,
                textbook_id=None,
                parent_id=None,
                grade_label=grade_label,
                name=name,
            )
            session.add(unit)
        unit.description = f"{grade_label} {semester_label} {name} 단원 메타데이터"
        unit.learning_goal = learning_goal
        unit.sort_order = sort_order
        unit.metadata_json = metadata
        unit.is_active = True
    session.flush()

    allowed_by_area = {
        "수와 연산": ["multiple_choice", "short_answer", "solution_steps", "descriptive", "table_interpretation"],
        "변화와 관계": ["multiple_choice", "short_answer", "solution_steps", "descriptive", "graph", "table_interpretation"],
        "도형과 측정": ["multiple_choice", "short_answer", "solution_steps", "descriptive", "geometry", "proof"],
        "자료와 가능성": ["multiple_choice", "short_answer", "descriptive", "table_interpretation", "graph"],
    }
    allowed_by_name = {
        "문자와 식": ["multiple_choice", "short_answer", "solution_steps", "descriptive"],
        "일차방정식": ["multiple_choice", "short_answer", "solution_steps", "descriptive"],
        "연립방정식": ["multiple_choice", "short_answer", "solution_steps"],
        "이차방정식": ["multiple_choice", "short_answer", "solution_steps"],
        "일차함수": ["multiple_choice", "short_answer", "graph", "table_interpretation", "descriptive"],
        "이차함수": ["multiple_choice", "short_answer", "graph", "table_interpretation"],
    }
    for grade_label, _semester_label, area, name, _learning_goal, _sort_order in unit_specs:
        unit = _get_unit(session, subject_id, grade_label, name)
        if unit is not None:
            _allow_formats(session, unit.id, allowed_by_name.get(name, allowed_by_area[area]))


def _allow_formats(session: Session, unit_id: int, format_codes: list[str]) -> None:
    for code in format_codes:
        problem_format = _get_format(session, code)
        if problem_format is None:
            continue
        if _get_allowed_format(session, unit_id, problem_format.id) is None:
            session.add(
                UnitAllowedFormat(
                    unit_id=unit_id,
                    problem_format_id=problem_format.id,
                    default_weight=1.0,
                    min_difficulty=1,
                    max_difficulty=5,
                )
            )


def _metadata(**values: str) -> str:
    return json.dumps(values, ensure_ascii=False, sort_keys=True)

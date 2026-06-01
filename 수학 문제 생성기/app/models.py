from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""


def utc_now() -> datetime:
    return datetime.now(UTC)


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    textbooks: Mapped[list["Textbook"]] = relationship(back_populates="subject")
    units: Mapped[list["Unit"]] = relationship(back_populates="subject")


class Textbook(Base):
    __tablename__ = "textbooks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), index=True)
    publisher: Mapped[str] = mapped_column(String(160))
    title: Mapped[str] = mapped_column(String(200))
    grade_label: Mapped[str] = mapped_column(String(80), index=True)
    curriculum_version: Mapped[str] = mapped_column(String(80), default="")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    subject: Mapped["Subject"] = relationship(back_populates="textbooks")
    units: Mapped[list["Unit"]] = relationship(back_populates="textbook")


class Unit(Base):
    __tablename__ = "units"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), index=True)
    textbook_id: Mapped[int | None] = mapped_column(ForeignKey("textbooks.id"), nullable=True, index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("units.id"), nullable=True, index=True)
    grade_label: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    learning_goal: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    subject: Mapped["Subject"] = relationship(back_populates="units")
    textbook: Mapped["Textbook | None"] = relationship(back_populates="units")
    parent: Mapped["Unit | None"] = relationship(remote_side=[id])
    allowed_formats: Mapped[list["UnitAllowedFormat"]] = relationship(back_populates="unit")


class ProblemFormat(Base):
    __tablename__ = "problem_formats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    requires_choices: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_rubric: Mapped[bool] = mapped_column(Boolean, default=False)
    supports_auto_validation: Mapped[bool] = mapped_column(Boolean, default=True)
    supports_rendering: Mapped[bool] = mapped_column(Boolean, default=False)
    default_validation_method: Mapped[str] = mapped_column(String(80), default="auto")
    default_rendering_type: Mapped[str] = mapped_column(String(80), default="none")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    allowed_units: Mapped[list["UnitAllowedFormat"]] = relationship(back_populates="problem_format")


class UnitAllowedFormat(Base):
    __tablename__ = "unit_allowed_formats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("units.id"), index=True)
    problem_format_id: Mapped[int] = mapped_column(ForeignKey("problem_formats.id"), index=True)
    default_weight: Mapped[float] = mapped_column(Float, default=1.0)
    min_difficulty: Mapped[int] = mapped_column(Integer, default=1)
    max_difficulty: Mapped[int] = mapped_column(Integer, default=5)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    unit: Mapped["Unit"] = relationship(back_populates="allowed_formats")
    problem_format: Mapped["ProblemFormat"] = relationship(back_populates="allowed_units")


class ProblemSet(Base):
    __tablename__ = "problem_sets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), index=True)
    textbook_id: Mapped[int | None] = mapped_column(ForeignKey("textbooks.id"), nullable=True, index=True)
    unit_id: Mapped[int | None] = mapped_column(ForeignKey("units.id"), nullable=True, index=True)
    difficulty_level: Mapped[int] = mapped_column(Integer, default=3)
    generation_mode: Mapped[str] = mapped_column(String(40), default="direct")
    generation_instruction: Mapped[str] = mapped_column(Text, default="")
    requested_count: Mapped[int] = mapped_column(Integer, default=5)
    status: Mapped[str] = mapped_column(String(40), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Problem(Base):
    __tablename__ = "problems"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    problem_set_id: Mapped[int] = mapped_column(ForeignKey("problem_sets.id"), index=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), index=True)
    textbook_id: Mapped[int | None] = mapped_column(ForeignKey("textbooks.id"), nullable=True, index=True)
    unit_id: Mapped[int | None] = mapped_column(ForeignKey("units.id"), nullable=True, index=True)
    format_code: Mapped[str] = mapped_column(String(80), index=True)
    difficulty_level: Mapped[int] = mapped_column(Integer, default=3)
    question_text: Mapped[str] = mapped_column(Text)
    answer_text: Mapped[str] = mapped_column(Text, default="")
    explanation_text: Mapped[str] = mapped_column(Text, default="")
    input_schema_json: Mapped[str] = mapped_column(Text, default="{}")
    answer_schema_json: Mapped[str] = mapped_column(Text, default="{}")
    choices_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    rubric_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    rendering_type: Mapped[str] = mapped_column(String(80), default="none")
    rendering_payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    validation_method: Mapped[str] = mapped_column(String(80), default="manual")
    validation_status: Mapped[str] = mapped_column(String(80), default="pending")
    validation_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class GenerationLog(Base):
    __tablename__ = "generation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    problem_set_id: Mapped[int | None] = mapped_column(ForeignKey("problem_sets.id"), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(80))
    model_name: Mapped[str] = mapped_column(String(120), default="")
    request_summary: Mapped[str] = mapped_column(Text, default="")
    response_summary: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(40), default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ValidationResult(Base):
    __tablename__ = "validation_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"), index=True)
    method: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(80))
    expected_answer: Mapped[str] = mapped_column(Text, default="")
    computed_answer: Mapped[str] = mapped_column(Text, default="")
    message: Mapped[str] = mapped_column(Text, default="")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class RenderedAsset(Base):
    __tablename__ = "rendered_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"), index=True)
    rendering_type: Mapped[str] = mapped_column(String(80), index=True)
    payload_hash: Mapped[str] = mapped_column(String(80), index=True)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(80), default="rendered")
    message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

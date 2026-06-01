from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import BASE_DIR
from app.models import GenerationLog, Problem, ProblemSet, RenderedAsset, ValidationResult


class ProblemSetDeleteResult:
    def __init__(self, problem_set_id: int, deleted_problem_count: int):
        self.problem_set_id = problem_set_id
        self.deleted_problem_count = deleted_problem_count


def delete_problem_set(session: Session, problem_set_id: int) -> ProblemSetDeleteResult | None:
    problem_set = session.get(ProblemSet, problem_set_id)
    if problem_set is None:
        return None

    problem_ids = list(
        session.scalars(select(Problem.id).where(Problem.problem_set_id == problem_set_id)).all()
    )

    if problem_ids:
        assets = session.scalars(select(RenderedAsset).where(RenderedAsset.problem_id.in_(problem_ids))).all()
        for asset in assets:
            if asset.file_path:
                _remove_rendered_file(asset.file_path)
        session.execute(delete(RenderedAsset).where(RenderedAsset.problem_id.in_(problem_ids)))
        session.execute(delete(ValidationResult).where(ValidationResult.problem_id.in_(problem_ids)))
        session.execute(delete(Problem).where(Problem.id.in_(problem_ids)))

    session.execute(delete(GenerationLog).where(GenerationLog.problem_set_id == problem_set_id))
    session.delete(problem_set)
    session.commit()
    return ProblemSetDeleteResult(problem_set_id=problem_set_id, deleted_problem_count=len(problem_ids))


def _remove_rendered_file(file_path: str) -> None:
    if "/" in file_path or "\\" in file_path or ".." in file_path:
        return
    rendered_dir = (BASE_DIR / "data" / "rendered").resolve()
    target = (rendered_dir / file_path).resolve()
    if rendered_dir not in target.parents:
        return
    try:
        target.unlink(missing_ok=True)
    except OSError:
        return

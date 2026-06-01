import hashlib
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import BASE_DIR
from app.models import Problem, RenderedAsset
from app.services.renderers.base import RenderError
from app.services.renderers.registry import RendererRegistry
from app.services.validators.base import safe_json_loads


class RenderingService:
    def __init__(self, registry: RendererRegistry | None = None):
        self.registry = registry or RendererRegistry()
        self.rendered_dir = BASE_DIR / "data" / "rendered"
        self.rendered_dir.mkdir(parents=True, exist_ok=True)

    def render_problem(self, session: Session, problem: Problem) -> RenderedAsset:
        rendering_type = problem.rendering_type or "none"
        payload = safe_json_loads(problem.rendering_payload_json, {})
        payload_hash = self._payload_hash(rendering_type, payload)
        cached = self._get_cached(session, problem.id, rendering_type, payload_hash)
        if cached is not None:
            return cached

        renderer = self.registry.get(rendering_type)
        if renderer is None:
            return self._save_failed(session, problem.id, rendering_type, payload_hash, "No renderer for rendering_type.")

        try:
            output = renderer.render(payload if isinstance(payload, dict) else {})
        except RenderError as exc:
            return self._save_failed(session, problem.id, rendering_type, payload_hash, str(exc))

        asset = RenderedAsset(
            problem_id=problem.id,
            rendering_type=rendering_type,
            payload_hash=payload_hash,
            status=output.status,
            message=output.message,
            content_html=output.content_html,
            file_path=None,
        )
        if output.file_content is not None:
            extension = output.extension or "svg"
            filename = f"problem-{problem.id}-{payload_hash[:16]}.{extension}"
            path = self._safe_render_path(filename)
            if isinstance(output.file_content, bytes):
                path.write_bytes(output.file_content)
            else:
                path.write_text(output.file_content, encoding="utf-8")
            asset.file_path = filename
        session.add(asset)
        session.commit()
        session.refresh(asset)
        return asset

    def render_problem_set(self, session: Session, problem_set_id: int) -> list[RenderedAsset]:
        problems = session.scalars(
            select(Problem).where(Problem.problem_set_id == problem_set_id).order_by(Problem.id)
        ).all()
        return [self.render_problem(session, problem) for problem in problems if problem.rendering_type != "none"]

    def latest_assets_by_problem(self, session: Session, problem_ids: list[int]) -> dict[int, RenderedAsset]:
        if not problem_ids:
            return {}
        rows = session.scalars(
            select(RenderedAsset)
            .where(RenderedAsset.problem_id.in_(problem_ids))
            .order_by(RenderedAsset.problem_id, RenderedAsset.id.desc())
        ).all()
        assets: dict[int, RenderedAsset] = {}
        for asset in rows:
            if asset.problem_id not in assets:
                assets[asset.problem_id] = asset
        return assets

    def _get_cached(
        self,
        session: Session,
        problem_id: int,
        rendering_type: str,
        payload_hash: str,
    ) -> RenderedAsset | None:
        return session.scalar(
            select(RenderedAsset)
            .where(
                RenderedAsset.problem_id == problem_id,
                RenderedAsset.rendering_type == rendering_type,
                RenderedAsset.payload_hash == payload_hash,
                RenderedAsset.status == "rendered",
            )
            .order_by(RenderedAsset.id.desc())
        )

    def _save_failed(
        self,
        session: Session,
        problem_id: int,
        rendering_type: str,
        payload_hash: str,
        message: str,
    ) -> RenderedAsset:
        asset = RenderedAsset(
            problem_id=problem_id,
            rendering_type=rendering_type,
            payload_hash=payload_hash,
            status="render_failed",
            message=message,
        )
        session.add(asset)
        session.commit()
        session.refresh(asset)
        return asset

    def _payload_hash(self, rendering_type: str, payload: object) -> str:
        encoded = json.dumps({"rendering_type": rendering_type, "payload": payload}, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def _safe_render_path(self, filename: str) -> Path:
        if "/" in filename or "\\" in filename or ".." in filename:
            raise RenderError("Invalid render filename.")
        path = (self.rendered_dir / filename).resolve()
        if self.rendered_dir.resolve() not in path.parents:
            raise RenderError("Render path escaped rendered directory.")
        return path

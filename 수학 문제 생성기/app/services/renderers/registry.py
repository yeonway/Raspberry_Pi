from app.services.renderers.base import Renderer
from app.services.renderers.geometry_svg_renderer import GeometrySvgRenderer
from app.services.renderers.graph_renderer import CoordinateSvgRenderer, GraphRenderer
from app.services.renderers.table_renderer import TableRenderer


class RendererRegistry:
    def __init__(self):
        graph = GraphRenderer()
        self._renderers: dict[str, Renderer] = {
            "html_table": TableRenderer(),
            "graph_svg": graph,
            "graph_png": graph,
            "coordinate_svg": CoordinateSvgRenderer(),
            "geometry_svg": GeometrySvgRenderer(),
        }

    def get(self, rendering_type: str) -> Renderer | None:
        if rendering_type == "none":
            return None
        return self._renderers.get(rendering_type)

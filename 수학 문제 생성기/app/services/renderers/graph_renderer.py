import re
from typing import Any

import sympy as sp

from app.services.renderers.base import RenderError, RenderOutput


class GraphRenderer:
    rendering_type = "graph_svg"
    width = 520
    height = 360
    margin = 40

    def render(self, payload: dict[str, Any]) -> RenderOutput:
        x_min, x_max = _range(payload.get("x_range"), -5, 5)
        y_min, y_max = _range(payload.get("y_range"), -5, 5)
        if x_min >= x_max or y_min >= y_max:
            raise RenderError("Invalid graph range.")

        show_grid = bool(payload.get("show_grid", True))
        points = _points(payload.get("points") or [])
        equation = str(payload.get("equation") or "").strip()
        line_points = _sample_equation(equation, x_min, x_max, y_min, y_max) if equation else []

        svg = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}" viewBox="0 0 {self.width} {self.height}" role="img">',
            '<rect width="100%" height="100%" fill="#ffffff"/>',
        ]
        if show_grid:
            svg.extend(self._grid(x_min, x_max, y_min, y_max))
        svg.extend(self._axes(x_min, x_max, y_min, y_max))
        if line_points:
            path = " ".join(f"{self._sx(x, x_min, x_max):.2f},{self._sy(y, y_min, y_max):.2f}" for x, y in line_points)
            svg.append(f'<polyline points="{path}" fill="none" stroke="#256d85" stroke-width="3"/>')
        for point in points:
            x, y = point["x"], point["y"]
            svg.append(
                f'<circle cx="{self._sx(x, x_min, x_max):.2f}" cy="{self._sy(y, y_min, y_max):.2f}" r="4" fill="#d92d20"/>'
            )
        svg.append("</svg>")
        return RenderOutput(rendering_type=self.rendering_type, status="rendered", extension="svg", file_content="".join(svg))

    def _grid(self, x_min: float, x_max: float, y_min: float, y_max: float) -> list[str]:
        lines = []
        for index in range(11):
            x = self.margin + index * (self.width - self.margin * 2) / 10
            y = self.margin + index * (self.height - self.margin * 2) / 10
            lines.append(f'<line x1="{x:.2f}" y1="{self.margin}" x2="{x:.2f}" y2="{self.height - self.margin}" stroke="#e5e7eb"/>')
            lines.append(f'<line x1="{self.margin}" y1="{y:.2f}" x2="{self.width - self.margin}" y2="{y:.2f}" stroke="#e5e7eb"/>')
        return lines

    def _axes(self, x_min: float, x_max: float, y_min: float, y_max: float) -> list[str]:
        lines = []
        zero_x = self._sx(0, x_min, x_max) if x_min <= 0 <= x_max else self.margin
        zero_y = self._sy(0, y_min, y_max) if y_min <= 0 <= y_max else self.height - self.margin
        lines.append(f'<line x1="{zero_x:.2f}" y1="{self.margin}" x2="{zero_x:.2f}" y2="{self.height - self.margin}" stroke="#111827"/>')
        lines.append(f'<line x1="{self.margin}" y1="{zero_y:.2f}" x2="{self.width - self.margin}" y2="{zero_y:.2f}" stroke="#111827"/>')
        return lines

    def _sx(self, x: float, x_min: float, x_max: float) -> float:
        return self.margin + (x - x_min) / (x_max - x_min) * (self.width - self.margin * 2)

    def _sy(self, y: float, y_min: float, y_max: float) -> float:
        return self.height - self.margin - (y - y_min) / (y_max - y_min) * (self.height - self.margin * 2)


class CoordinateSvgRenderer(GraphRenderer):
    rendering_type = "coordinate_svg"


def _range(value: Any, default_min: float, default_max: float) -> tuple[float, float]:
    if not isinstance(value, list) or len(value) != 2:
        return default_min, default_max
    return float(value[0]), float(value[1])


def _points(value: Any) -> list[dict[str, float]]:
    if not isinstance(value, list) or len(value) > 50:
        raise RenderError("Points must be a list with at most 50 items.")
    points = []
    for item in value:
        if not isinstance(item, dict) or "x" not in item or "y" not in item:
            raise RenderError("Each point requires x and y.")
        points.append({"x": float(item["x"]), "y": float(item["y"])})
    return points


def _sample_equation(equation: str, x_min: float, x_max: float, y_min: float, y_max: float) -> list[tuple[float, float]]:
    if len(equation) > 80 or not re.fullmatch(r"[0-9xyXY_+\-*/().= ]+", equation):
        raise RenderError("Unsupported equation.")
    x = sp.Symbol("x")
    expression_text = equation.split("=", 1)[-1].strip()
    expr = sp.sympify(expression_text)
    if expr.free_symbols - {x}:
        raise RenderError("Only x variable is supported.")
    if sp.Poly(expr, x).degree() > 2:
        raise RenderError("Only linear or simple quadratic equations are supported.")
    samples = []
    for index in range(41):
        x_value = x_min + (x_max - x_min) * index / 40
        y_value = float(expr.subs(x, x_value))
        if y_min <= y_value <= y_max:
            samples.append((x_value, y_value))
    return samples

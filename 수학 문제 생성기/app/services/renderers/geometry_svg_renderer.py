from app.services.renderers.base import RenderError, RenderOutput


class GeometrySvgRenderer:
    rendering_type = "geometry_svg"
    width = 420
    height = 300

    def render(self, payload: dict) -> RenderOutput:
        shape = str(payload.get("shape") or "").lower()
        labels = bool(payload.get("labels", False))
        if shape == "rectangle":
            content = self._rectangle(float(payload.get("width", 6)), float(payload.get("height", 4)), labels)
        elif shape == "triangle":
            content = self._triangle(labels)
        elif shape == "circle":
            content = self._circle(float(payload.get("radius", 4)), labels)
        else:
            raise RenderError("Unsupported geometry shape.")
        return RenderOutput(rendering_type=self.rendering_type, status="rendered", extension="svg", file_content=content)

    def _base(self, body: str) -> str:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}" '
            f'viewBox="0 0 {self.width} {self.height}" role="img">'
            '<rect width="100%" height="100%" fill="#ffffff"/>'
            f"{body}</svg>"
        )

    def _rectangle(self, width_value: float, height_value: float, labels: bool) -> str:
        body = '<rect x="95" y="70" width="230" height="150" fill="none" stroke="#256d85" stroke-width="3"/>'
        if labels:
            body += f'<text x="190" y="245" font-size="16">{width_value:g}</text>'
            body += f'<text x="340" y="150" font-size="16">{height_value:g}</text>'
        return self._base(body)

    def _triangle(self, labels: bool) -> str:
        body = '<polygon points="210,55 90,230 330,230" fill="none" stroke="#256d85" stroke-width="3"/>'
        if labels:
            body += '<text x="205" y="45" font-size="16">A</text><text x="70" y="245" font-size="16">B</text><text x="340" y="245" font-size="16">C</text>'
        return self._base(body)

    def _circle(self, radius_value: float, labels: bool) -> str:
        body = '<circle cx="210" cy="150" r="85" fill="none" stroke="#256d85" stroke-width="3"/>'
        body += '<line x1="210" y1="150" x2="295" y2="150" stroke="#d92d20" stroke-width="2"/>'
        if labels:
            body += f'<text x="245" y="140" font-size="16">r={radius_value:g}</text>'
        return self._base(body)

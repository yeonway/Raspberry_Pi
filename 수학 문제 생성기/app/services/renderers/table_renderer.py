from html import escape
from typing import Any

from app.services.renderers.base import RenderError, RenderOutput


class TableRenderer:
    rendering_type = "html_table"

    def render(self, payload: dict[str, Any]) -> RenderOutput:
        headers = payload.get("headers") or []
        rows = payload.get("rows") or payload.get("table") or []
        if not isinstance(headers, list) or not isinstance(rows, list) or not rows:
            raise RenderError("Table payload requires headers and rows.")
        if len(rows) > 50:
            raise RenderError("Table payload is too large.")

        html = ["<table class=\"rendered-table\">"]
        if headers:
            html.append("<thead><tr>")
            html.extend(f"<th>{escape(str(header))}</th>" for header in headers)
            html.append("</tr></thead>")
        html.append("<tbody>")
        for row in rows:
            if not isinstance(row, list):
                raise RenderError("Each table row must be a list.")
            html.append("<tr>")
            html.extend(f"<td>{escape(str(cell))}</td>" for cell in row)
            html.append("</tr>")
        html.append("</tbody></table>")
        return RenderOutput(rendering_type=self.rendering_type, status="rendered", content_html="".join(html))

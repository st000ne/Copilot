from . import register_tool
from .base import BaseTool
import requests

@register_tool
class HTTPTool(BaseTool):
    name = "http_get"
    description = "Fetch text content from a URL using an HTTP GET request."
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The URL to fetch."},
            "max_chars": {
                "type": "integer",
                "description": "Maximum number of characters to return.",
                "default": 1000,
            },
        },
        "required": ["url"],
    }

    def run(self, url: str, max_chars: int = 1000) -> str:
        try:
            resp = requests.get(url, timeout=10)
            if not resp.ok:
                return f"HTTP error {resp.status_code} when requesting {url}"
            text = resp.text.strip()
            return text[:max_chars] + ("..." if len(text) > max_chars else "")
        except Exception as e:
            return f"Error fetching {url}: {e}"

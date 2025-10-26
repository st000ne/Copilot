from . import register_tool
from .base import BaseTool


@register_tool
class HelloTool(BaseTool):
    name = "hello"
    description = "Simple test tool that greets the user."
    parameters = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Name to greet"},
        },
        "required": ["name"],
    }

    def run(self, name: str) -> str:
        return f"Hello, {name}! The tool layer is alive."

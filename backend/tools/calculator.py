from . import register_tool
from .base import BaseTool
import math

@register_tool
class CalculatorTool(BaseTool):
    name = "calculator"
    description = "Evaluate a mathematical expression safely."
    parameters = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Math expression to evaluate, e.g. '2 * (3 + 4)'",
            }
        },
        "required": ["expression"],
    }

    def run(self, expression: str) -> str:
        """Safely evaluate simple math expressions."""
        allowed_names = {k: getattr(math, k) for k in dir(math) if not k.startswith("__")}
        allowed_names["abs"] = abs
        allowed_names["round"] = round

        try:
            value = eval(expression, {"__builtins__": {}}, allowed_names)
            return f"Result: {value}"
        except Exception as e:
            return f"Error: invalid expression ({e})"

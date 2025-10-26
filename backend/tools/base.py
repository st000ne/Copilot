from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseTool(ABC):
    """Abstract base class for all tools."""

    name: str = "base_tool"
    description: str = "Abstract tool"
    parameters: Dict[str, Any] = {}

    @abstractmethod
    def run(self, **kwargs) -> Any:
        """Execute the tool’s main logic."""
        pass

    def to_schema(self) -> Dict[str, Any]:
        """Optional: export OpenAI-style schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

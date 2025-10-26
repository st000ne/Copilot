from typing import Dict
from .base import BaseTool

# Global registry
_TOOL_REGISTRY: Dict[str, BaseTool] = {}


def register_tool(cls):
    """Decorator to register a tool class."""
    instance = cls()
    _TOOL_REGISTRY[instance.name] = instance
    return cls


def get_tool(name: str) -> BaseTool | None:
    return _TOOL_REGISTRY.get(name)


def list_tools() -> list[BaseTool]:
    return list(_TOOL_REGISTRY.values())

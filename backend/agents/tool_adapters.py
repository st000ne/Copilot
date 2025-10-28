import asyncio
import json
import inspect
from typing import Any, Dict, Optional

from backend.tools import _TOOL_REGISTRY
from backend.agents.types import Observation
from backend.agents.policy import DEFAULT_TOOL_TIMEOUT_SEC


async def _run_with_timeout(func, *args, timeout: Optional[int] = None, **kwargs):
    """
    Internal helper to run possibly-sync tools with timeout handling.
    """
    timeout = timeout or DEFAULT_TOOL_TIMEOUT_SEC

    if inspect.iscoroutinefunction(func):
        return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)

    # sync fallback
    loop = asyncio.get_event_loop()
    return await asyncio.wait_for(loop.run_in_executor(None, lambda: func(*args, **kwargs)), timeout=timeout)


async def run_tool_safely(
    name: str,
    args: Dict[str, Any],
    timeout: Optional[int] = None,
) -> Observation:
    """
    Look up a tool by name and run it safely, returning an Observation.
    Wraps all exceptions and timeouts into structured failure Observations.
    """
    if name not in _TOOL_REGISTRY:
        return Observation(
            text=f"Tool '{name}' not found in registry.",
            success=False,
            metadata={"error": "unknown_tool"},
        )

    tool = _TOOL_REGISTRY[name]
    try:
        # Most of your tools have .run(); some might have .arun()
        func = getattr(tool, "arun", None) or getattr(tool, "run", None)
        if func is None:
            raise AttributeError(f"Tool {name} has no .run or .arun method")

        result = await _run_with_timeout(func, **args, timeout=timeout)
        text_result = str(result)
        return Observation(text=text_result, success=True)

    except asyncio.TimeoutError:
        return Observation(
            text=f"Tool '{name}' timed out after {timeout}s.",
            success=False,
            metadata={"error": "timeout"},
        )

    except Exception as e:
        return Observation(
            text=f"Error while running tool '{name}': {e}",
            success=False,
            metadata={"error": "exception", "details": str(e)},
        )


def parse_action_line(line: str) -> Optional[Dict[str, Any]]:
    """
    Parse a line like:
        Action: calculator({"expression": "23*18"})
    Returns {"name": "calculator", "args": {"expression": "23*18"}} or None on failure.
    """
    line = line.strip()
    if not line.lower().startswith("action:"):
        return None

    try:
        content = line[len("Action:"):].strip()
        name, json_part = content.split("(", 1)
        name = name.strip()
        json_str = json_part.rsplit(")", 1)[0]
        args = json.loads(json_str)
        if not isinstance(args, dict):
            raise ValueError("Arguments must be a JSON object")
        return {"name": name, "args": args}
    except Exception:
        return None

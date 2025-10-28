from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class Action(BaseModel):
    """
    An agent action: choose a tool and provide arguments as a dict.
    Example: Action(name="calculator", args={"expression": "23*18"})
    """
    name: str
    args: Dict[str, Any]


class Observation(BaseModel):
    """
    Result of a tool call or system observation.
    We keep it free-form but include optional metadata for debugging.
    """
    text: str
    success: bool = True
    metadata: Optional[Dict[str, Any]] = None


class TraceEntry(BaseModel):
    """
    One loop entry: the agent's thought (optional), action (optional),
    the observation produced by the action, and a timestamp-like step index.
    """
    step: int
    thought: Optional[str] = None
    action: Optional[Action] = None
    observation: Optional[Observation] = None


class AgentResult(BaseModel):
    """
    What the agent returns to the pipeline.
    - final_text: the assistant-facing reply (what the user sees by default).
    - thoughts: the scratchpad / chain-of-thought (can be shown/hidden in the UI).
    - trace: the sequence of TraceEntry objects for debugging and UI replay.
    """
    final_text: str
    thoughts: Optional[str]
    trace: List[TraceEntry]
    # allow extra info for the frontend if needed
    meta: Optional[Dict[str, Any]] = None


class AgentConfig(BaseModel):
    """
    Config for a single run. All fields optional: agent will fall back to policy defaults.
    """
    max_steps: Optional[int] = None
    max_retries: Optional[int] = None
    tool_timeout_sec: Optional[int] = None
    allowed_tools: Optional[List[str]] = None  # None means all registered tools allowed

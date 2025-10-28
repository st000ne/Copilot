from typing import List, Dict, Any, Optional
from backend.agents.agent_core import Agent
from backend.agents.types import AgentConfig, AgentResult


async def run_agent_chat(
    user_message: str,
    history: Optional[List[Dict[str, str]]] = None,
    *,
    max_steps: int = 6,
    max_retries: int = 2,
    tool_timeout_sec: int = 15,
    allowed_tools: Optional[list[str]] = None,
) -> AgentResult:
    """
    Convenience wrapper that creates an Agent and runs it.
    Returns AgentResult with final_text, thoughts, and trace.
    """
    config = AgentConfig(
        max_steps=max_steps,
        max_retries=max_retries,
        tool_timeout_sec=tool_timeout_sec,
        allowed_tools=allowed_tools,
    )

    agent = Agent(config)
    return await agent.run(user_message, history)

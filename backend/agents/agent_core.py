import asyncio
import re
from typing import List, Optional

from backend.llm_client import llm
from backend.agents.types import Action, Observation, TraceEntry, AgentResult, AgentConfig
from backend.agents.policy import (
    DEFAULT_MAX_STEPS,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TOOL_TIMEOUT_SEC,
    THOUGHT_PREFIX,
    ACTION_PREFIX,
    OBSERVATION_PREFIX,
    FINAL_ANSWER_PREFIX,
)
from backend.agents.prompts import REACT_INSTRUCTION, FEW_SHOT_EXAMPLES
from backend.agents.tool_adapters import run_tool_safely, parse_action_line
from backend.tools import _TOOL_REGISTRY


class Agent:
    """
    Core ReAct-style agent loop.
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()

    async def run(self, user_input: str, history: Optional[List[dict]] = None) -> AgentResult:
        """
        Main ReAct loop. Returns AgentResult with final answer, thoughts, and trace.
        """
        history = history or []

        max_steps = self.config.max_steps or DEFAULT_MAX_STEPS
        max_retries = self.config.max_retries or DEFAULT_MAX_RETRIES
        timeout = self.config.tool_timeout_sec or DEFAULT_TOOL_TIMEOUT_SEC
        allowed_tools = self.config.allowed_tools or list(_TOOL_REGISTRY.keys())

        trace: List[TraceEntry] = []
        scratchpad_lines: List[str] = []

        # Build system prompt
        tool_list_str = ", ".join(allowed_tools)
        instruction = REACT_INSTRUCTION.format(tool_list=tool_list_str)
        few_shots = "\n".join(FEW_SHOT_EXAMPLES)

        system_prompt = instruction + "\n\n" + few_shots

        # Prepare conversation
        messages = [{"role": "system", "content": system_prompt}]
        messages += history
        messages.append({"role": "user", "content": user_input})

        for step in range(1, max_steps + 1):
            # Inject scratchpad as assistant-visible context
            if scratchpad_lines:
                scratchpad_text = "\n".join(scratchpad_lines)
                messages.append(
                    {
                        "role": "assistant",
                        "content": f"(previous reasoning)\n{scratchpad_text}",
                    }
                )

            # Ask model for next move
            response = await llm.ainvoke(messages)
            model_text = response["content"].strip()

            # Extract relevant lines
            lines = [ln.strip() for ln in model_text.splitlines() if ln.strip()]
            thought_line = next((ln for ln in lines if ln.startswith(THOUGHT_PREFIX)), None)
            action_line = next((ln for ln in lines if ln.startswith(ACTION_PREFIX)), None)
            final_line = next((ln for ln in lines if ln.startswith(FINAL_ANSWER_PREFIX)), None)

            # Handle FinalAnswer directly
            if final_line:
                final_text = final_line[len(FINAL_ANSWER_PREFIX):].strip()
                return AgentResult(
                    final_text=final_text,
                    thoughts="\n".join(scratchpad_lines),
                    trace=trace,
                )

            # If no action, stop (model confused)
            if not action_line:
                return AgentResult(
                    final_text="I could not determine an action or final answer.",
                    thoughts="\n".join(scratchpad_lines),
                    trace=trace,
                )

            parsed = parse_action_line(action_line)
            if not parsed:
                obs = Observation(
                    text=f"Failed to parse action line: {action_line}",
                    success=False,
                    metadata={"error": "parse_error"},
                )
                trace.append(TraceEntry(step=step, thought=thought_line, observation=obs))
                scratchpad_lines.append(f"{OBSERVATION_PREFIX} {obs.text}")
                continue

            # Execute tool
            action = Action(**parsed)
            obs = None
            for attempt in range(max_retries):
                obs = await run_tool_safely(action.name, action.args, timeout=timeout)
                if obs.success:
                    break

            trace.append(TraceEntry(step=step, thought=thought_line, action=action, observation=obs))

            # Add to scratchpad for next step
            if thought_line:
                scratchpad_lines.append(thought_line)
            scratchpad_lines.append(f"{ACTION_PREFIX} {action.name}({action.args})")
            scratchpad_lines.append(f"{OBSERVATION_PREFIX} {obs.text}")

        # If loop ends without FinalAnswer
        return AgentResult(
            final_text="Reached max reasoning steps without a final answer.",
            thoughts="\n".join(scratchpad_lines),
            trace=trace,
        )

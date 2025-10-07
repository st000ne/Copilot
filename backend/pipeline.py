import os
from dotenv import load_dotenv
from pydantic import SecretStr

from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI   # ✅ verify import name in your installed LangChain version
import tiktoken

from backend.memory import query_memory, add_memory

from pathlib import Path

dotenv_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY environment variable. See .env.example")


# --- Config ---
MODEL_NAME = "gpt-4o-mini"          # or "gpt-3.5-turbo"
MAX_CONTEXT_TOKENS = 3000           # ~half the context window for safety
SUMMARIZE_AFTER_MESSAGES = 20       # when to start summarizing
SYSTEM_PROMPT = (
    "You are Copilot, a helpful, intelligent assistant that remembers context "
    "and answers clearly, concisely, and helpfully."
)

# Initialize the main chat model
llm = ChatOpenAI(model_name=MODEL_NAME, temperature=0.7, openai_api_key=SecretStr(OPENAI_API_KEY))

# Optional summarizer model (cheaper/faster)
summarizer = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.3, openai_api_key=SecretStr(OPENAI_API_KEY))

# --- Helpers ---
def num_tokens_from_messages(messages, model_name=MODEL_NAME):
    """Rough token count using tiktoken for safe trimming."""
    enc = tiktoken.encoding_for_model(model_name)
    text = "".join(m["content"] for m in messages)
    return len(enc.encode(text))

def summarize_messages(messages):
    """Summarize older messages when conversation grows too long."""
    summary_prompt = (
        "Summarize the following conversation briefly so it can be used as context:\n\n"
        + "\n".join([f"{m['role']}: {m['content']}" for m in messages])
    )
    resp = summarizer.invoke([HumanMessage(content=summary_prompt)])
    return resp.content.strip()

# --- Main Chat Function ---
def run_chat(messages: list[dict]):
    """
    messages: list of dicts with role/content ('user'|'assistant'|'system')
    returns: dict with role/content for the assistant reply
    """

    # Ensure we always start with a system prompt
    if not any(m["role"] == "system" for m in messages):
        messages.insert(0, {"role": "system", "content": SYSTEM_PROMPT})

    # Summarize if conversation is getting long
    if len(messages) > SUMMARIZE_AFTER_MESSAGES:
        summary_text = summarize_messages(messages[:-10])  # summarize older part
        messages = (
            [messages[0],  # keep system
             {"role": "system", "content": f"Conversation summary: {summary_text}"}]
            + messages[-10:]  # keep last few turns
        )

    # Trim if token usage exceeds limit
    while num_tokens_from_messages(messages) > MAX_CONTEXT_TOKENS and len(messages) > 5:
        messages.pop(1)  # remove oldest non-system message

    user_last = next((m for m in reversed(messages) if m["role"] == "user"), None)
    retrieved = query_memory(user_last["content"]) if user_last else []

    if retrieved:
        # Build structured system message
        mem_context = "\n".join(
            f"- ({r['source']}, score={r['score']:.2f}): {r['content']}"
            for r in retrieved
        )

        messages.insert(
            1,
            {
                "role": "system",
                "content": (
                    "You have access to relevant contextual knowledge retrieved "
                    "from your memory stores. Use this information naturally:\n"
                    f"{mem_context}"
                ),
            },
        )

    # Now rebuild lc_messages AFTER injection
    lc_messages = []
    for m in messages:
        if m["role"] == "user":
            lc_messages.append(HumanMessage(content=m["content"]))
        elif m["role"] == "assistant":
            lc_messages.append(AIMessage(content=m["content"]))
        elif m["role"] == "system":
            lc_messages.append(SystemMessage(content=m["content"]))

    response = llm.invoke(lc_messages)
    return {"role": "assistant", "content": response.content}

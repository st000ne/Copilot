import os
from dotenv import load_dotenv
from pydantic import SecretStr

# ⚠️ Verify imports: in newer versions, ChatOpenAI comes from langchain_openai
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage

from pathlib import Path

dotenv_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY environment variable. See .env.example")

# Initialize the LangChain model
llm = ChatOpenAI(
    model_name="gpt-3.5-turbo",
    temperature=0.2,
    max_tokens=500,
    openai_api_key=SecretStr(OPENAI_API_KEY),
)

def run_chat(messages):
    """
    messages: list of dicts with role/content (user/assistant/system)
    returns: dict with role/content for the assistant reply
    """
    lc_messages = []
    for m in messages:
        if m["role"] == "user":
            lc_messages.append(HumanMessage(content=m["content"]))
        elif m["role"] == "assistant":
            lc_messages.append(AIMessage(content=m["content"]))
        elif m["role"] == "system":
            lc_messages.append(SystemMessage(content=m["content"]))

    response = llm.invoke(lc_messages)  # synchronous for now
    return {"role": "assistant", "content": response.content}

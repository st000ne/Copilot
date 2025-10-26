import os
from dotenv import load_dotenv
from pydantic import SecretStr
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

llm = ChatOpenAI(
    model_name="gpt-4o-mini",
    temperature=0.7,
    openai_api_key=SecretStr(OPENAI_API_KEY)
)

summarizer = ChatOpenAI(
    model_name="gpt-3.5-turbo",
    temperature=0.3,
    openai_api_key=SecretStr(OPENAI_API_KEY)
)

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    openai_api_key=SecretStr(OPENAI_API_KEY)
)

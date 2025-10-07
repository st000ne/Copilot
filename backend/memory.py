from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings  # ✅ verify import path
import faiss
from langchain_community.docstore import InMemoryDocstore
from langchain_community.docstore.document import Document
import os
from pydantic import SecretStr

import os
from dotenv import load_dotenv
from pathlib import Path

dotenv_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY environment variable. See .env.example")

EMBED_MODEL = "text-embedding-3-small"
INDEX_PATH = "backend/docs/memory_index"

# Initialize embedding model
embeddings = OpenAIEmbeddings(model=EMBED_MODEL, openai_api_key=SecretStr(OPENAI_API_KEY))

def get_or_create_faiss_index():
    """Load FAISS index if it exists, otherwise create a new empty one."""
    if os.path.exists(INDEX_PATH):
        return FAISS.load_local(INDEX_PATH, embeddings, allow_dangerous_deserialization=True)

    # Create empty FAISS index
    dummy_vec = embeddings.embed_query("User's dog name is Mops.")
    dim = len(dummy_vec)
    index = faiss.IndexFlatL2(dim)

    # Initialize empty docstore and ID map
    docstore = InMemoryDocstore({})
    index_to_docstore_id = {}

    return FAISS(
        embedding_function=embeddings,
        index=index,
        docstore=docstore,
        index_to_docstore_id=index_to_docstore_id
    )

def save_faiss_index(index):
    index.save_local(INDEX_PATH)

def add_memory(text: str):
    """Store new memory string in FAISS index."""
    index = get_or_create_faiss_index()
    index.add_texts([text])
    save_faiss_index(index)

def query_memory(query: str, k: int = 3) -> list[str]:
    """Retrieve most relevant memory snippets."""
    index = get_or_create_faiss_index()
    results = index.similarity_search(query, k=k)
    return [r.page_content for r in results]

import os
from PyPDF2 import PdfReader
from docx import Document as DocxDocument

def extract_text_from_file(file_path: str) -> str:
    """Extract text content from supported file types."""
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    try:
        if ext in [".txt", ".md"]:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

        elif ext == ".pdf":
            text = []
            with open(file_path, "rb") as f:
                reader = PdfReader(f)
                for page in reader.pages:
                    text.append(page.extract_text() or "")
            return "\n".join(text)

        elif ext == ".docx":
            doc = DocxDocument(file_path)
            return "\n".join(p.text for p in doc.paragraphs)

        else:
            raise ValueError(f"Unsupported file type: {ext}")

    except Exception as e:
        raise RuntimeError(f"Failed to extract text from {file_path}: {e}")

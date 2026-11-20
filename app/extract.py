"""Text extraction: .txt direct, .pdf via pypdf. Nothing else is accepted."""
import io

from pypdf import PdfReader


def extract_text(filename: str, raw_bytes: bytes) -> str:
    name = (filename or "").lower()
    if name.endswith(".txt"):
        return raw_bytes.decode("utf-8", errors="ignore")
    if name.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(raw_bytes))
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        return "\n".join(pages)
    raise ValueError("Only .txt and .pdf resumes are supported")

"""PDF text extraction for artifact ingestion. No layout/OCR — plain per-page
text extraction, concatenated with blank lines so chunk_text's paragraph
splitter (app/ingestion/extractors.py) still segments it sensibly."""
from io import BytesIO

from pypdf import PdfReader


def extract_text_from_pdf(data: bytes) -> str:
    reader = PdfReader(BytesIO(data))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(p.strip() for p in pages if p.strip())

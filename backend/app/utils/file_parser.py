"""
Document text extraction helpers for PDF, Markdown, and plain text files.
"""

from pathlib import Path
from typing import Callable, Dict, Iterable, List

TEXT_EXTENSIONS = {'.md', '.markdown', '.txt'}
PDF_EXTENSION = '.pdf'


def _unique(values: Iterable[str]) -> List[str]:
    seen = set()
    ordered = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def _encoding_candidates(data: bytes) -> List[str]:
    candidates: List[str] = []
    try:
        from charset_normalizer import from_bytes
        match = from_bytes(data).best()
        if match and match.encoding:
            candidates.append(match.encoding)
    except Exception:
        pass
    try:
        import chardet
        detected = chardet.detect(data)
        if detected and detected.get('encoding'):
            candidates.append(detected['encoding'])
    except Exception:
        pass
    return _unique(['utf-8', *candidates, 'gb18030'])


def _read_text_with_fallback(file_path: str) -> str:
    data = Path(file_path).read_bytes()
    for encoding in _encoding_candidates(data):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode('utf-8', errors='replace')


def _document_header(index: int, label: str) -> str:
    return f"=== Document {index}: {label} ==="


class FileParser:
    """Extract text from supported upload file formats."""

    SUPPORTED_EXTENSIONS = {PDF_EXTENSION, *TEXT_EXTENSIONS}

    @classmethod
    def extract_text(cls, file_path: str) -> str:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"file not found: {file_path}")

        suffix = path.suffix.lower()
        handlers = cls._handlers()
        if suffix not in handlers:
            raise ValueError(f"unsupported file type: {suffix}")
        return handlers[suffix](file_path)

    @classmethod
    def _handlers(cls) -> Dict[str, Callable[[str], str]]:
        return {
            PDF_EXTENSION: cls._extract_from_pdf,
            '.md': cls._extract_from_text,
            '.markdown': cls._extract_from_text,
            '.txt': cls._extract_from_text,
        }

    @staticmethod
    def _extract_from_pdf(file_path: str) -> str:
        try:
            import fitz
        except ImportError as exc:
            raise ImportError("PyMuPDF is required: pip install PyMuPDF") from exc

        sections = []
        with fitz.open(file_path) as document:
            for page in document:
                page_text = page.get_text().strip()
                if page_text:
                    sections.append(page_text)
        return "\n\n".join(sections)

    @staticmethod
    def _extract_from_text(file_path: str) -> str:
        return _read_text_with_fallback(file_path)

    @staticmethod
    def _extract_from_md(file_path: str) -> str:
        return _read_text_with_fallback(file_path)

    @staticmethod
    def _extract_from_txt(file_path: str) -> str:
        return _read_text_with_fallback(file_path)

    @classmethod
    def extract_from_multiple(cls, file_paths: List[str]) -> str:
        documents = []
        for index, file_path in enumerate(file_paths, 1):
            try:
                body = cls.extract_text(file_path)
                label = Path(file_path).name
                documents.append(f"{_document_header(index, label)}\n{body}")
            except Exception as exc:
                documents.append(f"{_document_header(index, file_path)} (extraction failed: {exc})")
        return "\n\n".join(documents)


def _next_boundary(text: str, start: int, hard_end: int, min_ratio: float) -> int:
    separators = (chr(0x3002), chr(0xFF01), chr(0xFF1F), '.\n', '!\n', '?\n', '\n\n', '. ', '! ', '? ')
    window = text[start:hard_end]
    best_offset = -1
    best_width = 0
    for separator in separators:
        offset = window.rfind(separator)
        if offset > best_offset:
            best_offset = offset
            best_width = len(separator)
    if best_offset >= int((hard_end - start) * min_ratio):
        return start + best_offset + best_width
    return hard_end


def split_text_into_chunks(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50
) -> List[str]:
    content = (text or "").strip()
    if not content:
        return []
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if len(content) <= chunk_size:
        return [content]

    safe_overlap = max(0, min(overlap, chunk_size - 1))
    chunks: List[str] = []
    start = 0
    while start < len(content):
        hard_end = min(len(content), start + chunk_size)
        end = hard_end if hard_end == len(content) else _next_boundary(content, start, hard_end, 0.3)
        chunk = content[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(content):
            break
        start = max(start + 1, end - safe_overlap)
    return chunks

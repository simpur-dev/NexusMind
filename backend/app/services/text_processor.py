"""
Text processing facade used before graph construction and retrieval.
"""

import re
from typing import Dict, Iterable, List

from ..utils.file_parser import FileParser, split_text_into_chunks


class TextProcessor:
    """Small stateless facade for extraction, normalization, and chunking."""

    @staticmethod
    def extract_from_files(file_paths: List[str]) -> str:
        usable_paths = [str(path) for path in file_paths if path]
        return FileParser.extract_from_multiple(usable_paths)

    @staticmethod
    def split_text(
        text: str,
        chunk_size: int = 500,
        overlap: int = 50
    ) -> List[str]:
        normalized_text = TextProcessor.preprocess_text(text)
        return split_text_into_chunks(normalized_text, chunk_size, overlap)

    @staticmethod
    def preprocess_text(text: str) -> str:
        if not text:
            return ""
        normalized = text.replace('\r\n', '\n').replace('\r', '\n')
        cleaned_lines = TextProcessor._trim_lines(normalized.split('\n'))
        compact = '\n'.join(cleaned_lines)
        return re.sub(r'\n{3,}', '\n\n', compact).strip()

    @staticmethod
    def _trim_lines(lines: Iterable[str]) -> List[str]:
        return [line.strip() for line in lines]

    @staticmethod
    def get_text_stats(text: str) -> Dict[str, int]:
        content = text or ""
        if not content:
            return {"total_chars": 0, "total_lines": 0, "total_words": 0}
        return {
            "total_chars": len(content),
            "total_lines": content.count('\n') + 1,
            "total_words": len(content.split()),
        }

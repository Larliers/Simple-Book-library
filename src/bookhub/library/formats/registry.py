from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from bookhub.library.models import ParsedMetadata


MetadataExtractor = Callable[[Path], "ParsedMetadata"]
ThumbnailBuilder = Callable[[Path, Path, str], str]


@dataclass(frozen=True, slots=True)
class LibraryFormatHandler:
    """Single registration point for a Library format's scan-time behavior."""

    suffixes: tuple[str, ...]
    extract_metadata: MetadataExtractor
    build_thumbnail: ThumbnailBuilder


def _pdf_metadata(path: Path):
    from bookhub.library.metadata import extract_pdf_metadata
    return extract_pdf_metadata(path)


def _pdf_thumbnail(path: Path, output: Path, _title: str) -> str:
    from bookhub.library.metadata import generate_pdf_thumbnail
    return generate_pdf_thumbnail(path, output)


def _epub_metadata(path: Path):
    from bookhub.library.metadata import extract_epub_metadata
    return extract_epub_metadata(path)


def _epub_thumbnail(path: Path, output: Path, title: str) -> str:
    from bookhub.library.metadata import generate_epub_thumbnail
    return generate_epub_thumbnail(path, output, title)


def _html_metadata(path: Path):
    from bookhub.library.formats.html_md import extract_html_metadata
    return extract_html_metadata(path)


def _html_thumbnail(path: Path, output: Path, title: str) -> str:
    from bookhub.library.formats.html_md import generate_html_thumbnail
    return generate_html_thumbnail(path, output, title)


def _markdown_metadata(path: Path):
    from bookhub.library.formats.html_md import extract_markdown_metadata
    return extract_markdown_metadata(path)


def _markdown_thumbnail(path: Path, output: Path, title: str) -> str:
    from bookhub.library.formats.html_md import generate_markdown_thumbnail
    return generate_markdown_thumbnail(path, output, title)


def _fb2_metadata(path: Path):
    from bookhub.library.formats.fb2 import extract_fb2_metadata
    return extract_fb2_metadata(path)


def _fb2_thumbnail(path: Path, output: Path, title: str) -> str:
    from bookhub.library.formats.fb2 import generate_fb2_thumbnail
    return generate_fb2_thumbnail(path, output, title)


def _docx_metadata(path: Path):
    from bookhub.library.formats.docx_fmt import extract_docx_metadata
    return extract_docx_metadata(path)


def _docx_thumbnail(path: Path, output: Path, title: str) -> str:
    from bookhub.library.formats.docx_fmt import generate_docx_thumbnail
    return generate_docx_thumbnail(path, output, title)


LIBRARY_FORMAT_HANDLERS = (
    LibraryFormatHandler((".pdf",), _pdf_metadata, _pdf_thumbnail),
    LibraryFormatHandler((".epub",), _epub_metadata, _epub_thumbnail),
    LibraryFormatHandler((".html", ".htm"), _html_metadata, _html_thumbnail),
    LibraryFormatHandler((".md", ".markdown"), _markdown_metadata, _markdown_thumbnail),
    LibraryFormatHandler((".fb2", ".fb2.zip"), _fb2_metadata, _fb2_thumbnail),
    LibraryFormatHandler((".docx",), _docx_metadata, _docx_thumbnail),
)


def extension_for(path: Path) -> str:
    return ".fb2.zip" if path.name.lower().endswith(".fb2.zip") else path.suffix.lower()


def get_library_format_handler(path: Path | str, extension: str | None = None) -> LibraryFormatHandler | None:
    target_extension = (extension or extension_for(Path(path))).lower()
    return next((item for item in LIBRARY_FORMAT_HANDLERS if target_extension in item.suffixes), None)


def is_supported_library_file(path: Path | str) -> bool:
    return get_library_format_handler(path) is not None


def supported_library_extensions() -> tuple[str, ...]:
    return tuple(suffix for handler in LIBRARY_FORMAT_HANDLERS for suffix in handler.suffixes)

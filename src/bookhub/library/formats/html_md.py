from __future__ import annotations

import base64
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

from bookhub.library.formats.common import (
    bytes_to_thumbnail,
    clean_text,
    title_placeholder_thumbnail,
)
from bookhub.library.models import ParsedMetadata
from bookhub.library.text_encoding import detect_and_decode

_MD_IMAGE_RE = re.compile(r"!\[[^\]]*]\(([^)]+)\)")
_MD_HEADING_RE = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)


class _HtmlCoverParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_title = False
        self.title_parts: list[str] = []
        self.image_srcs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        name = tag.lower()
        if name == "title":
            self._in_title = True
            return
        if name != "img":
            return
        attr_map = {k.lower(): (v or "") for k, v in attrs}
        src = attr_map.get("src") or attr_map.get("data-src") or ""
        if src:
            self.image_srcs.append(src.strip())

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_parts.append(data)


def _read_text_file(file_path: Path) -> str:
    raw = file_path.read_bytes()
    decoded = detect_and_decode(raw, preference="auto")
    return decoded.text


def _load_local_or_data_image(src: str, base_dir: Path) -> bytes | None:
    text = str(src or "").strip()
    if not text:
        return None
    if text.startswith("data:image/"):
        try:
            header, encoded = text.split(",", 1)
            if ";base64" not in header.lower():
                return None
            return base64.b64decode(encoded, validate=False)
        except Exception:  # noqa: BLE001
            return None
    parsed = urlparse(text)
    if parsed.scheme in {"http", "https", "ftp"}:
        return None
    if parsed.scheme == "file":
        candidate = Path(unquote(parsed.path))
    else:
        candidate = (base_dir / unquote(text)).resolve(strict=False)
    try:
        if not candidate.is_file():
            return None
        if candidate.stat().st_size > 40 * 1024 * 1024:
            return None
        return candidate.read_bytes()
    except OSError:
        return None


def extract_html_metadata(file_path: Path) -> ParsedMetadata:
    parser = _HtmlCoverParser()
    try:
        parser.feed(_read_text_file(file_path))
        parser.close()
    except Exception:  # noqa: BLE001
        return ParsedMetadata(title=file_path.stem)
    title = clean_text("".join(parser.title_parts)) or file_path.stem
    return ParsedMetadata(title=title)


def generate_html_thumbnail(file_path: Path, output_path: Path, title_fallback: str) -> str:
    parser = _HtmlCoverParser()
    try:
        parser.feed(_read_text_file(file_path))
        parser.close()
    except Exception:  # noqa: BLE001
        return title_placeholder_thumbnail(output_path, title_fallback or file_path.stem)

    title = clean_text("".join(parser.title_parts)) or title_fallback or file_path.stem
    for src in parser.image_srcs:
        cover_bytes = _load_local_or_data_image(src, file_path.parent)
        if cover_bytes:
            return bytes_to_thumbnail(cover_bytes, output_path, title)
    return title_placeholder_thumbnail(output_path, title)


def extract_markdown_metadata(file_path: Path) -> ParsedMetadata:
    try:
        text = _read_text_file(file_path)
    except OSError:
        return ParsedMetadata(title=file_path.stem)
    match = _MD_HEADING_RE.search(text)
    title = clean_text(match.group(1) if match else None) or file_path.stem
    return ParsedMetadata(title=title)


def generate_markdown_thumbnail(file_path: Path, output_path: Path, title_fallback: str) -> str:
    try:
        text = _read_text_file(file_path)
    except OSError:
        return title_placeholder_thumbnail(output_path, title_fallback or file_path.stem)

    match = _MD_HEADING_RE.search(text)
    title = clean_text(match.group(1) if match else None) or title_fallback or file_path.stem
    for image_match in _MD_IMAGE_RE.finditer(text):
        src = image_match.group(1).strip().strip("<>").split()[0]
        cover_bytes = _load_local_or_data_image(src, file_path.parent)
        if cover_bytes:
            return bytes_to_thumbnail(cover_bytes, output_path, title)
    return title_placeholder_thumbnail(output_path, title)

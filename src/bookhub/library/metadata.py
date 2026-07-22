from __future__ import annotations

import hashlib
import os
import zipfile
from io import BytesIO
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as ET

from PIL import Image, ImageDraw

from bookhub.library.media_sanitizer import sanitize_image_for_ui

from bookhub.library.models import (
    HASH_STRATEGY_QUICK,
    HASH_STRATEGY_SHA256,
    HASH_STRATEGY_SIZE_MTIME,
    FingerprintBundle,
    HashStrategy,
    ParsedMetadata,
)

EPUB_NS = {
    "container": "urn:oasis:names:tc:opendocument:xmlns:container",
    "opf": "http://www.idpf.org/2007/opf",
    "dc": "http://purl.org/dc/elements/1.1/",
}


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_language(value: str | None) -> str | None:
    text = _clean_text(value)
    if not text:
        return None
    return text.lower()


def _format_authors(creators: list[str]) -> str | None:
    compact = [item.strip() for item in creators if item and item.strip()]
    if not compact:
        return None
    return " | ".join(compact)


def build_metadata_tags(metadata: ParsedMetadata) -> list[str]:
    tags: list[str] = []
    if metadata.author:
        tags.append(f"author: {metadata.author}")
    if metadata.publisher:
        tags.append(f"publisher: {metadata.publisher}")
    if metadata.language:
        tags.append(f"language: {metadata.language}")
    return tags


def compute_fingerprints(
    file_path: Path,
    strategy: HashStrategy = HASH_STRATEGY_SHA256,
) -> FingerprintBundle:
    """Compute fingerprints according to strategy.

    - size_mtime: only stat (no file read)
    - quick: first 4 MiB hash + size_mtime
    - sha256: full-file hash + quick + size_mtime
    Uncomputed fields are empty strings so callers can COALESCE on upsert.
    """
    stat = file_path.stat()
    size_mtime = f"{stat.st_size}:{int(stat.st_mtime)}"
    if strategy == HASH_STRATEGY_SIZE_MTIME:
        return FingerprintBundle(sha256="", size_mtime=size_mtime, quick="")

    quick_digest = ""
    sha256_digest = ""
    with file_path.open("rb") as handle:
        first_chunk = handle.read(4 * 1024 * 1024)
        quick_hasher = hashlib.sha256()
        quick_hasher.update(first_chunk)
        quick_digest = quick_hasher.hexdigest()
        if strategy == HASH_STRATEGY_SHA256:
            sha256_hasher = hashlib.sha256()
            sha256_hasher.update(first_chunk)
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                sha256_hasher.update(chunk)
            sha256_digest = sha256_hasher.hexdigest()
        elif strategy != HASH_STRATEGY_QUICK:
            # Unknown strategy: fall back to full hash for safety.
            sha256_hasher = hashlib.sha256()
            sha256_hasher.update(first_chunk)
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                sha256_hasher.update(chunk)
            sha256_digest = sha256_hasher.hexdigest()
    return FingerprintBundle(
        sha256=sha256_digest,
        size_mtime=size_mtime,
        quick=quick_digest,
    )


def extract_pdf_metadata(file_path: Path) -> ParsedMetadata:
    try:
        import fitz  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("PyMuPDF is required for PDF import. Install dependency: PyMuPDF.") from exc

    doc = fitz.open(str(file_path))
    try:
        payload = doc.metadata or {}
        title = _clean_text(payload.get("title"))
        author = _clean_text(payload.get("author"))
        publisher = _clean_text(payload.get("publisher"))
        language = _normalize_language(payload.get("language"))
        return ParsedMetadata(
            title=title,
            author=author,
            publisher=publisher,
            language=language,
        )
    finally:
        doc.close()


def _extract_epub_package(zip_file: zipfile.ZipFile) -> tuple[str, ET.Element]:
    container = ET.fromstring(zip_file.read("META-INF/container.xml"))
    rootfile = container.find(".//container:rootfile", EPUB_NS)
    if rootfile is None:
        raise RuntimeError("EPUB metadata error: META-INF/container.xml missing rootfile entry")
    package_path = rootfile.attrib.get("full-path")
    if not package_path:
        raise RuntimeError("EPUB metadata error: rootfile full-path is empty")
    opf_root = ET.fromstring(zip_file.read(package_path))
    return package_path, opf_root


def extract_epub_metadata(file_path: Path) -> ParsedMetadata:
    with zipfile.ZipFile(file_path, "r") as zip_file:
        _, opf_root = _extract_epub_package(zip_file)
        metadata = opf_root.find(".//opf:metadata", EPUB_NS)
        if metadata is None:
            return ParsedMetadata()

        def first_text(xpath: str) -> str | None:
            node = metadata.find(xpath, EPUB_NS)
            return _clean_text(node.text if node is not None else None)

        creators = [node.text or "" for node in metadata.findall("dc:creator", EPUB_NS)]
        return ParsedMetadata(
            title=first_text("dc:title"),
            author=_format_authors(creators),
            publisher=first_text("dc:publisher"),
            language=_normalize_language(first_text("dc:language")),
        )


def _extract_epub_cover_bytes(file_path: Path) -> bytes | None:
    with zipfile.ZipFile(file_path, "r") as zip_file:
        package_path, opf_root = _extract_epub_package(zip_file)
        metadata = opf_root.find(".//opf:metadata", EPUB_NS)
        manifest = opf_root.find(".//opf:manifest", EPUB_NS)
        if manifest is None:
            return None

        cover_id: str | None = None
        if metadata is not None:
            for node in metadata.findall("opf:meta", EPUB_NS):
                if node.attrib.get("name", "").lower() == "cover":
                    cover_id = node.attrib.get("content")
                    if cover_id:
                        break

        manifest_items = manifest.findall("opf:item", EPUB_NS)
        selected_href: str | None = None
        if cover_id:
            for item in manifest_items:
                if item.attrib.get("id") == cover_id:
                    selected_href = item.attrib.get("href")
                    if selected_href:
                        break

        if selected_href is None:
            for item in manifest_items:
                properties = item.attrib.get("properties", "")
                if "cover-image" in properties:
                    selected_href = item.attrib.get("href")
                    if selected_href:
                        break

        if selected_href is None:
            for item in manifest_items:
                media_type = item.attrib.get("media-type", "").lower()
                if media_type.startswith("image/"):
                    selected_href = item.attrib.get("href")
                    if selected_href:
                        break

        if not selected_href:
            return None

        opf_dir = PurePosixPath(package_path).parent
        cover_path = (opf_dir / selected_href).as_posix()
        try:
            return zip_file.read(cover_path)
        except KeyError:
            return None


def _save_thumbnail_image(image: Image.Image, output_path: Path) -> str:
    """Save thumbnail as compressed WebP and return a file:// URL string."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Force .webp extension regardless of what was passed
    webp_path = output_path.with_suffix(".webp")
    thumb = image.convert("RGB")
    thumb.thumbnail((360, 540), Image.Resampling.LANCZOS)
    # Save as WebP quality=80 – typically 70-80% smaller than PNG
    thumb.save(webp_path, format="WEBP", quality=80, method=4)
    resolved = webp_path.resolve(strict=False)
    # Return as file:// URL so the DB never stores bare filesystem paths
    return resolved.as_uri()


def generate_pdf_thumbnail(file_path: Path, output_path: Path) -> str:
    try:
        import fitz  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("PyMuPDF is required for PDF thumbnail rendering.") from exc

    doc = fitz.open(str(file_path))
    try:
        if doc.page_count <= 0:
            raise RuntimeError("PDF has no pages for thumbnail rendering.")
        page = doc.load_page(0)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(1.45, 1.45), alpha=False)
        image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
        return _save_thumbnail_image(image, output_path)
    finally:
        doc.close()


def generate_epub_thumbnail(file_path: Path, output_path: Path, title_fallback: str) -> str:
    cover_bytes = _extract_epub_cover_bytes(file_path)
    if cover_bytes:
        safe_png_path = output_path.with_suffix(".cover_sanitized.png")
        try:
            with Image.open(BytesIO(cover_bytes)) as cover_image:
                cover_image.save(safe_png_path, format="PNG", icc_profile=None, optimize=True)
        except Exception:  # noqa: BLE001
            safe_png_path = output_path.with_suffix(".cover_sanitized_fallback.png")
            safe_png_path.write_bytes(cover_bytes)

        sanitized = sanitize_image_for_ui(safe_png_path, safe_png_path)
        if sanitized.ok and sanitized.output_path:
            with Image.open(Path(sanitized.output_path)) as safe_cover_image:
                return _save_thumbnail_image(safe_cover_image, output_path)
        with Image.open(safe_png_path) as cover_image:
            return _save_thumbnail_image(cover_image, output_path)

    placeholder = Image.new("RGB", (360, 540), color=(232, 238, 248))
    draw = ImageDraw.Draw(placeholder)
    label = title_fallback[:80] if title_fallback else file_path.stem[:80]
    draw.text((20, 24), label, fill=(55, 65, 86))
    return _save_thumbnail_image(placeholder, output_path)


def extract_metadata_by_extension(file_path: Path, extension: str | None = None):
    from bookhub.library.formats.registry import get_library_format_handler

    handler = get_library_format_handler(file_path, extension)
    if handler is None:
        raise RuntimeError(f"Unsupported extension for metadata extraction: {extension or extension_lower(file_path)}")
    return handler.extract_metadata(file_path)


def build_thumbnail_by_extension(
    file_path: Path,
    extension: str,
    output_path: Path,
    title_fallback: str,
) -> str:
    from bookhub.library.formats.registry import get_library_format_handler

    handler = get_library_format_handler(file_path, extension)
    if handler is None:
        raise RuntimeError(f"Unsupported extension for thumbnail generation: {extension}")
    return handler.build_thumbnail(file_path, output_path, title_fallback)


def regenerate_thumbnail_for_record(
    *,
    extension: str,
    source_path: str,
    output_path: str,
    title_fallback: str,
) -> str:
    file_path = Path(source_path)
    target_path = Path(output_path)
    return build_thumbnail_by_extension(file_path, extension, target_path, title_fallback)


def file_size_mtime_token(file_path: Path) -> str:
    stat = file_path.stat()
    return f"{stat.st_size}:{int(stat.st_mtime)}"


def extension_lower(file_path: Path) -> str:
    name = file_path.name.lower()
    from bookhub.library.models import FB2_ZIP_SUFFIX

    if name.endswith(FB2_ZIP_SUFFIX):
        return FB2_ZIP_SUFFIX
    return file_path.suffix.lower()


def file_name(file_path: Path) -> str:
    return file_path.name


def path_is_subpath(path: str, root: str) -> bool:
    normalized_path = os.path.normcase(os.path.normpath(path))
    normalized_root = os.path.normcase(os.path.normpath(root))
    if normalized_path == normalized_root:
        return True
    return normalized_path.startswith(normalized_root + os.sep)

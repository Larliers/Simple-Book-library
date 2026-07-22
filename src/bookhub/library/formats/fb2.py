from __future__ import annotations

import base64
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from bookhub.library.formats.common import (
    bytes_to_thumbnail,
    clean_text,
    title_placeholder_thumbnail,
)
from bookhub.library.formats.zip_safety import ZipBombError, open_zip_safely, read_zip_member_safely
from bookhub.library.models import ParsedMetadata

_FB2_NS = {
    "fb": "http://www.gribuser.ru/xml/fictionbook/2.0",
    "l": "http://www.w3.org/1999/xlink",
}


def _local(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _read_fb2_xml_bytes(file_path: Path) -> bytes:
    name = file_path.name.lower()
    if name.endswith(".fb2.zip"):
        with open_zip_safely(file_path) as zip_file:
            members = [
                info.filename
                for info in zip_file.infolist()
                if not info.is_dir() and info.filename.lower().endswith(".fb2")
            ]
            if not members:
                raise RuntimeError("FB2.ZIP contains no .fb2 member")
            members.sort(key=lambda item: item.lower())
            return read_zip_member_safely(zip_file, members[0])
    return file_path.read_bytes()


def _find_text(root: ET.Element, path: str) -> str | None:
    node = root.find(path, _FB2_NS)
    if node is None:
        # Namespace-agnostic fallback
        parts = [p.split(":")[-1] for p in path.split("/") if p and p != "."]
        current: ET.Element | None = root
        for part in parts:
            if current is None:
                return None
            current = next((child for child in current if _local(child.tag) == part), None)
        if current is None:
            return None
        return clean_text("".join(current.itertext()))
    return clean_text("".join(node.itertext()))


def _collect_binary_map(root: ET.Element) -> dict[str, bytes]:
    binaries: dict[str, bytes] = {}
    for node in root.iter():
        if _local(node.tag) != "binary":
            continue
        binary_id = node.attrib.get("id") or ""
        if not binary_id:
            continue
        raw = "".join((node.text or "").split())
        if not raw:
            continue
        try:
            binaries[binary_id] = base64.b64decode(raw, validate=False)
        except Exception:  # noqa: BLE001
            continue
    return binaries


def _cover_bytes_from_root(root: ET.Element) -> bytes | None:
    binaries = _collect_binary_map(root)
    cover_ids: list[str] = []
    for node in root.iter():
        if _local(node.tag) != "coverpage":
            continue
        for child in node.iter():
            if _local(child.tag) != "image":
                continue
            href = (
                child.attrib.get("{http://www.w3.org/1999/xlink}href")
                or child.attrib.get("href")
                or ""
            )
            href = href.lstrip("#").strip()
            if href:
                cover_ids.append(href)
    for cover_id in cover_ids:
        data = binaries.get(cover_id)
        if data:
            return data
    # Fallback: first binary image
    for data in binaries.values():
        if data:
            return data
    return None


def extract_fb2_metadata(file_path: Path) -> ParsedMetadata:
    try:
        xml_bytes = _read_fb2_xml_bytes(file_path)
        root = ET.fromstring(xml_bytes)
    except (OSError, ET.ParseError, ZipBombError, zipfile.BadZipFile, RuntimeError):
        return ParsedMetadata(title=file_path.stem.replace(".fb2", ""))

    title = (
        _find_text(root, ".//fb:title-info/fb:book-title")
        or _find_text(root, ".//title-info/book-title")
        or file_path.stem.replace(".fb2", "")
    )
    authors: list[str] = []
    for author in root.iter():
        if _local(author.tag) != "author":
            continue
        first = ""
        last = ""
        nick = ""
        for child in author:
            local = _local(child.tag)
            text = clean_text("".join(child.itertext())) or ""
            if local == "first-name":
                first = text
            elif local == "last-name":
                last = text
            elif local == "nickname":
                nick = text
        name = " ".join(part for part in (first, last) if part).strip() or nick
        if name:
            authors.append(name)
    return ParsedMetadata(
        title=title,
        author="; ".join(authors) if authors else None,
    )


def generate_fb2_thumbnail(file_path: Path, output_path: Path, title_fallback: str) -> str:
    try:
        xml_bytes = _read_fb2_xml_bytes(file_path)
        root = ET.fromstring(xml_bytes)
    except (OSError, ET.ParseError, ZipBombError, zipfile.BadZipFile, RuntimeError):
        return title_placeholder_thumbnail(output_path, title_fallback or file_path.stem)

    title = (
        _find_text(root, ".//fb:title-info/fb:book-title")
        or title_fallback
        or file_path.stem
    )
    cover_bytes = _cover_bytes_from_root(root)
    if cover_bytes:
        return bytes_to_thumbnail(cover_bytes, output_path, title)
    return title_placeholder_thumbnail(output_path, title)

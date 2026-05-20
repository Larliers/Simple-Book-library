from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

PREVIEW_VARIANTS = {"original", "compressed"}
RESOURCE_TYPES = {"book", "comic", "text_novel"}


def ensure_preview_structure(preview_root: Path) -> None:
    for resource_type in sorted(RESOURCE_TYPES):
        for variant in sorted(PREVIEW_VARIANTS):
            (preview_root / resource_type / variant).mkdir(parents=True, exist_ok=True)


def build_preview_path(
    preview_root: Path,
    resource_type: str,
    variant: str,
    source_key: str,
    extension: str | None = None,
) -> Path:
    normalized_resource_type = _normalize_resource_type(resource_type)
    normalized_variant = _normalize_variant(variant)
    suffix = _normalize_extension(extension, normalized_variant)
    token = hashlib.sha1(str(source_key).encode("utf-8")).hexdigest()  # noqa: S324
    return preview_root / normalized_resource_type / normalized_variant / f"{token}{suffix}"


def uri_to_path(value: str | None) -> Path | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.startswith("file://"):
        parsed = urlparse(text)
        return Path(url2pathname(parsed.path))
    return Path(text)


def is_preview_variant_uri(value: str | None, *, resource_type: str, variant: str) -> bool:
    path = uri_to_path(value)
    if path is None:
        return False
    parts = {part.lower() for part in path.parts}
    return _normalize_resource_type(resource_type) in parts and _normalize_variant(variant) in parts


def _normalize_resource_type(resource_type: str) -> str:
    value = str(resource_type or "").strip().lower()
    if value in RESOURCE_TYPES:
        return value
    return "book"


def _normalize_variant(variant: str) -> str:
    value = str(variant or "").strip().lower()
    if value in PREVIEW_VARIANTS:
        return value
    return "compressed"


def _normalize_extension(extension: str | None, variant: str) -> str:
    if variant == "compressed":
        return ".webp"
    raw = str(extension or "").strip().lower()
    if not raw:
        return ".png"
    if not raw.startswith("."):
        raw = f".{raw}"
    return raw

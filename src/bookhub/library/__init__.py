from __future__ import annotations

from .models import (
    DEFAULT_TEXT_PREVIEW_CHARS,
    HASH_STRATEGY_QUICK,
    HASH_STRATEGY_SHA256,
    HASH_STRATEGY_SIZE_MTIME,
    HASH_STRATEGIES,
    SUPPORTED_EXTENSIONS,
    TEXT_PREVIEW_CHAR_OPTIONS,
    FingerprintBundle,
    HashStrategy,
    ParsedMetadata,
    ScanConflict,
    ScanRequest,
    ScanResult,
    TextScanRequest,
    TextScanRoot,
    ThumbnailTaskResult,
)
from .repository import LibraryRepository
from .scanner import scan_roots, scan_text_roots

try:
    from .worker import ScanWorker
except Exception:  # pragma: no cover
    ScanWorker = None  # type: ignore[assignment]

try:
    from .thumbnail_worker import ThumbnailTaskWorker
except Exception:  # pragma: no cover
    ThumbnailTaskWorker = None  # type: ignore[assignment]

__all__ = [
    "HASH_STRATEGY_QUICK",
    "HASH_STRATEGY_SHA256",
    "HASH_STRATEGY_SIZE_MTIME",
    "HASH_STRATEGIES",
    "SUPPORTED_EXTENSIONS",
    "DEFAULT_TEXT_PREVIEW_CHARS",
    "TEXT_PREVIEW_CHAR_OPTIONS",
    "FingerprintBundle",
    "HashStrategy",
    "LibraryRepository",
    "ParsedMetadata",
    "ScanConflict",
    "ScanRequest",
    "ScanResult",
    "TextScanRequest",
    "TextScanRoot",
    "ScanWorker",
    "ThumbnailTaskWorker",
    "ThumbnailTaskResult",
    "scan_roots",
    "scan_text_roots",
]

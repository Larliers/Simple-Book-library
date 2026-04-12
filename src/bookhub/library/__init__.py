from __future__ import annotations

from .models import (
    HASH_STRATEGY_QUICK,
    HASH_STRATEGY_SHA256,
    HASH_STRATEGY_SIZE_MTIME,
    HASH_STRATEGIES,
    SUPPORTED_EXTENSIONS,
    FingerprintBundle,
    HashStrategy,
    ParsedMetadata,
    ScanConflict,
    ScanRequest,
    ScanResult,
    ThumbnailTaskResult,
)
from .repository import LibraryRepository
from .scanner import scan_roots

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
    "FingerprintBundle",
    "HashStrategy",
    "LibraryRepository",
    "ParsedMetadata",
    "ScanConflict",
    "ScanRequest",
    "ScanResult",
    "ScanWorker",
    "ThumbnailTaskWorker",
    "ThumbnailTaskResult",
    "scan_roots",
]

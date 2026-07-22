from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PREVIEW_DIR = PROJECT_ROOT / "img_preview"

PREVIEW_CACHE_MODES = frozenset({"migrate", "rewire_only", "switch_only"})


def default_preview_dir() -> Path:
    return DEFAULT_PREVIEW_DIR.resolve(strict=False)


def is_writable_dir(path: Path) -> bool:
    """Return True if path exists as a directory we can create files in, or can be created."""
    try:
        target = path.resolve(strict=False)
        if target.exists():
            if not target.is_dir():
                return False
            probe = target / ".bookhub_write_probe"
            try:
                probe.write_text("ok", encoding="utf-8")
                probe.unlink(missing_ok=True)
                return True
            except OSError:
                return False
        target.mkdir(parents=True, exist_ok=True)
        probe = target / ".bookhub_write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def resolve_preview_dir(
    raw: str | None,
    *,
    create: bool = True,
) -> tuple[Path, bool]:
    """Resolve configured preview cache dir.

    Returns (path, used_default). Empty/invalid/unwritable values fall back to DEFAULT_PREVIEW_DIR.
    Non-empty values must be absolute paths.
    """
    text = str(raw or "").strip()
    if not text:
        path = default_preview_dir()
        if create:
            path.mkdir(parents=True, exist_ok=True)
        return path, True

    candidate = Path(text).expanduser()
    if not candidate.is_absolute():
        path = default_preview_dir()
        if create:
            path.mkdir(parents=True, exist_ok=True)
        return path, True

    resolved = candidate.resolve(strict=False)
    if create:
        if not is_writable_dir(resolved):
            path = default_preview_dir()
            path.mkdir(parents=True, exist_ok=True)
            return path, True
        return resolved, False

    if resolved.exists() and resolved.is_dir():
        return resolved, False
    path = default_preview_dir()
    return path, True


def paths_equal(a: Path, b: Path) -> bool:
    return a.resolve(strict=False) == b.resolve(strict=False)


def normalize_preview_cache_mode(mode: str | None) -> str:
    value = str(mode or "").strip().lower()
    if value in PREVIEW_CACHE_MODES:
        return value
    return "migrate"

from __future__ import annotations

import shutil
import filecmp
from uuid import uuid4
from dataclasses import dataclass, field
from pathlib import Path

from bookhub.library.data_paths import is_writable_dir, paths_equal, resolve_preview_dir
from bookhub.library.preview_paths import ensure_preview_structure, uri_to_path
from bookhub.library.repository import LibraryRepository


@dataclass
class PreviewCacheMigrateResult:
    ok: bool
    mode: str
    old_root: str
    new_root: str
    copied_files: int = 0
    rewritten_uris: int = 0
    used_default: bool = False
    errors: list[str] = field(default_factory=list)
    warning: str = ""

    def to_summary(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "mode": self.mode,
            "old_root": self.old_root,
            "new_root": self.new_root,
            "copied_files": self.copied_files,
            "rewritten_uris": self.rewritten_uris,
            "used_default": self.used_default,
            "errors": list(self.errors),
            "warning": self.warning,
        }


def is_path_under_root(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except ValueError:
        return False


def rewire_thumbnail_uri(uri: str | None, old_root: Path, new_root: Path) -> str | None:
    path = uri_to_path(uri)
    if path is None:
        return None
    old_resolved = old_root.resolve(strict=False)
    new_resolved = new_root.resolve(strict=False)
    resolved = path.resolve(strict=False)
    if not is_path_under_root(resolved, old_resolved):
        return None
    relative = resolved.relative_to(old_resolved)
    return (new_resolved / relative).as_uri()


def copy_preview_tree(old_root: Path, new_root: Path) -> tuple[int, list[str]]:
    """Merge-copy files without overwriting a different destination file."""
    errors: list[str] = []
    copied = 0
    if not old_root.exists():
        return 0, errors
    if not old_root.is_dir():
        return 0, [f"Source is not a directory: {old_root}"]
    try:
        new_root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return 0, [f"Cannot create destination: {exc}"]

    for src in old_root.rglob("*"):
        if not src.is_file():
            continue
        try:
            relative = src.relative_to(old_root)
            dest = new_root / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                if not dest.is_file() or not filecmp.cmp(src, dest, shallow=False):
                    errors.append(f"Destination collision: {src} -> {dest}")
                    continue
                continue
            shutil.copy2(src, dest)
            copied += 1
        except OSError as exc:
            errors.append(f"Copy failed: {src} -> {exc}")
    return copied, errors


def safe_unlink_under_preview(path: Path | None, preview_dir: Path) -> bool:
    """Unlink only if path resolves under preview_dir. Returns True if unlinked or missing."""
    if path is None:
        return True
    try:
        resolved = path.resolve(strict=False)
        root = preview_dir.resolve(strict=False)
        if not is_path_under_root(resolved, root):
            return False
        resolved.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def apply_preview_cache_change(
    repository: LibraryRepository,
    new_path: str,
    mode: str,
) -> PreviewCacheMigrateResult:
    """Apply cache dir change with migrate | rewire_only | switch_only."""
    from bookhub.library.data_paths import normalize_preview_cache_mode

    mode_value = normalize_preview_cache_mode(mode)
    old_root = repository.preview_dir.resolve(strict=False)
    new_root, used_default = resolve_preview_dir(new_path, create=True)
    result = PreviewCacheMigrateResult(
        ok=False,
        mode=mode_value,
        old_root=str(old_root),
        new_root=str(new_root),
        used_default=used_default,
    )

    if not is_writable_dir(new_root):
        result.errors.append(f"Destination not writable: {new_root}")
        return result

    if paths_equal(old_root, new_root):
        # Still persist setting (e.g. reset to default clears custom string).
        setting_value = "" if used_default else str(new_root)
        repository.set_preview_cache_dir(setting_value)
        repository.preview_dir = new_root
        ensure_preview_structure(new_root)
        result.ok = True
        return result

    if is_path_under_root(new_root, old_root):
        result.errors.append("Destination cannot be inside the current preview cache directory")
        return result

    if mode_value == "migrate":
        staging_root = new_root.parent / f".bookhub-preview-staging-{uuid4().hex}"
        copied, copy_errors = copy_preview_tree(old_root, staging_root)
        if copy_errors:
            result.errors.extend(copy_errors)
            result.warning = f"Recoverable staging copy retained at: {staging_root}"
            return result
        merged, merge_errors = copy_preview_tree(staging_root, new_root)
        result.copied_files = merged
        if merge_errors:
            result.errors.extend(merge_errors)
            result.warning = f"Recoverable staging copy retained at: {staging_root}"
            return result
        ensure_preview_structure(new_root)
        try:
            result.rewritten_uris = repository.rewrite_thumbnail_uris_for_root_move(old_root, new_root)
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"Thumbnail URI rewrite failed: {exc}")
            result.warning = f"Copied files are retained at: {new_root}"
            return result
        shutil.rmtree(staging_root, ignore_errors=True)
    elif mode_value == "rewire_only":
        ensure_preview_structure(new_root)
        # Soft warning if tree looks empty while DB has thumbs under old root.
        sample_missing = _sample_rewire_missing(repository, old_root, new_root)
        if sample_missing:
            result.warning = sample_missing
        try:
            result.rewritten_uris = repository.rewrite_thumbnail_uris_for_root_move(old_root, new_root)
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"Thumbnail URI rewrite failed: {exc}")
            return result
    else:  # switch_only
        ensure_preview_structure(new_root)

    setting_value = "" if used_default else str(new_root)
    repository.set_preview_cache_dir(setting_value)
    repository.preview_dir = new_root
    result.ok = True
    return result


def _sample_rewire_missing(
    repository: LibraryRepository,
    old_root: Path,
    new_root: Path,
    *,
    limit: int = 5,
) -> str:
    missing = 0
    checked = 0
    for uri in repository.iter_thumbnail_uris(limit=50):
        path = uri_to_path(uri)
        if path is None:
            continue
        if not is_path_under_root(path.resolve(strict=False), old_root):
            continue
        checked += 1
        relative = path.resolve(strict=False).relative_to(old_root.resolve(strict=False))
        if not (new_root / relative).exists():
            missing += 1
        if checked >= limit:
            break
    if missing > 0:
        return (
            f"{missing} of {checked} sampled thumbnail files are missing under the new directory; "
            "covers may stay blank until files are moved or thumbnails are regenerated."
        )
    return ""

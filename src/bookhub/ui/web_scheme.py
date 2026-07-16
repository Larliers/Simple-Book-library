from __future__ import annotations

import mimetypes
import os
from pathlib import Path
from urllib.parse import unquote, urlparse

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QUrl
from PySide6.QtWebEngineCore import (
    QWebEngineUrlScheme,
    QWebEngineUrlSchemeHandler,
    QWebEngineUrlRequestJob,
)

APP_SCHEME = b"app"
APP_SCHEME_STR = "app"
WEB_ROOT = Path(__file__).resolve().parent / "web"

_IMAGE_SUFFIXES = {".webp", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff"}
_TEXT_MIME_OVERRIDES = {
    ".js": "application/javascript",
    ".mjs": "application/javascript",
    ".css": "text/css",
    ".html": "text/html",
    ".json": "application/json",
    ".svg": "image/svg+xml",
}


def register_app_scheme() -> None:
    """Register the ``app://`` scheme. Must run before QApplication is created."""
    scheme = QWebEngineUrlScheme(APP_SCHEME)
    scheme.setFlags(
        QWebEngineUrlScheme.SecureScheme
        | QWebEngineUrlScheme.LocalScheme
        | QWebEngineUrlScheme.LocalAccessAllowed
    )
    scheme.setSyntax(QWebEngineUrlScheme.Syntax.Host)
    QWebEngineUrlScheme.registerScheme(scheme)


def to_local_path(value: str | None) -> str | None:
    """Convert a ``file://`` URL or a bare path into an absolute local path."""
    text = str(value or "").strip()
    if not text:
        return None
    if text.startswith("file://"):
        try:
            local = QUrl(text).toLocalFile()
            if local:
                return os.path.normpath(local)
            parsed = urlparse(text)
            return os.path.normpath(unquote(parsed.path.lstrip("/")))
        except Exception:
            return None
    return os.path.normpath(text)


class AppSchemeHandler(QWebEngineUrlSchemeHandler):
    """Serves bundled web assets and whitelisted cover images over ``app://``.

    - ``app://app/<path>``      -> static files under ``web/``
    - ``app://img/x?p=<path>``  -> image file, only if in the allowed set
    """

    def __init__(self, allowed_images: set[str], parent=None) -> None:
        super().__init__(parent)
        self._allowed_images = allowed_images

    def requestStarted(self, job: QWebEngineUrlRequestJob) -> None:
        url = job.requestUrl()
        host = url.host()
        if host == "img":
            self._serve_image(job, url)
            return
        self._serve_static(job, url)

    def _serve_static(self, job: QWebEngineUrlRequestJob, url: QUrl) -> None:
        rel = unquote(url.path()).lstrip("/")
        if not rel:
            rel = "index.html"
        target = (WEB_ROOT / rel).resolve()
        try:
            target.relative_to(WEB_ROOT.resolve())
        except ValueError:
            job.fail(QWebEngineUrlRequestJob.UrlNotFound)
            return
        if not target.is_file():
            job.fail(QWebEngineUrlRequestJob.UrlNotFound)
            return
        self._reply_file(job, target)

    def _serve_image(self, job: QWebEngineUrlRequestJob, url: QUrl) -> None:
        raw = url.query()
        encoded = ""
        for part in raw.split("&"):
            if part.startswith("p="):
                encoded = part[2:]
                break
        local = to_local_path(unquote(encoded)) if encoded else None
        if not local:
            job.fail(QWebEngineUrlRequestJob.UrlNotFound)
            return
        normalized = os.path.normcase(os.path.normpath(local))
        if normalized not in self._allowed_images:
            job.fail(QWebEngineUrlRequestJob.RequestDenied)
            return
        path = Path(local)
        if path.suffix.lower() not in _IMAGE_SUFFIXES or not path.is_file():
            job.fail(QWebEngineUrlRequestJob.UrlNotFound)
            return
        self._reply_file(job, path)

    def _reply_file(self, job: QWebEngineUrlRequestJob, path: Path) -> None:
        try:
            data = path.read_bytes()
        except OSError:
            job.fail(QWebEngineUrlRequestJob.UrlNotFound)
            return
        suffix = path.suffix.lower()
        mime = _TEXT_MIME_OVERRIDES.get(suffix) or mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        buffer = QBuffer(job)
        buffer.setData(QByteArray(data))
        buffer.open(QIODevice.ReadOnly)
        job.reply(QByteArray(mime.encode("ascii")), buffer)

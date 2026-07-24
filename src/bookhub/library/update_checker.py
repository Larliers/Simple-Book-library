from __future__ import annotations

import json
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from bookhub.version import APP_VERSION, GITHUB_API_LATEST

_VERSION_PART_RE = re.compile(r"\d+")


def normalize_version(tag: str) -> tuple[int, ...]:
    """Strip a leading ``v`` and parse numeric semver segments."""
    cleaned = str(tag or "").strip().lstrip("vV")
    parts = _VERSION_PART_RE.findall(cleaned)
    if not parts:
        return (0,)
    return tuple(int(part) for part in parts)


def compare_versions(current: str, latest: str) -> int:
    """Compare two version strings. Returns -1, 0, or 1."""
    left = normalize_version(current)
    right = normalize_version(latest)
    width = max(len(left), len(right))
    left_padded = left + (0,) * (width - len(left))
    right_padded = right + (0,) * (width - len(right))
    if left_padded < right_padded:
        return -1
    if left_padded > right_padded:
        return 1
    return 0


def check_for_update(current_version: str = APP_VERSION, *, timeout: float = 8.0) -> dict[str, Any]:
    """Fetch GitHub latest release and compare against the current app version."""
    release = fetch_latest_release(timeout=timeout)
    if not release.get("ok"):
        return {
            "status": "error",
            "currentVersion": current_version,
            "message": str(release.get("error") or "Unable to check for updates."),
        }

    latest_tag = str(release.get("tag_name") or "")
    latest_url = str(release.get("html_url") or "")
    cmp = compare_versions(current_version, latest_tag)
    if cmp < 0:
        return {
            "status": "update_available",
            "currentVersion": current_version,
            "latestVersion": latest_tag,
            "url": latest_url,
        }
    return {
        "status": "up_to_date",
        "currentVersion": current_version,
        "latestVersion": latest_tag,
        "url": latest_url,
    }


def fetch_latest_release(*, timeout: float = 8.0) -> dict[str, Any]:
    """Request GitHub ``/releases/latest`` and return parsed release metadata."""
    request = Request(
        GITHUB_API_LATEST,
        headers={"Accept": "application/vnd.github+json", "User-Agent": f"Simple-Book-library/{APP_VERSION}"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 404:
            return {"ok": False, "error": "No published release found on GitHub yet."}
        return {"ok": False, "error": f"GitHub API error ({exc.code})."}
    except URLError:
        return {"ok": False, "error": "Network error. Check your connection and try again."}
    except (TimeoutError, json.JSONDecodeError, OSError):
        return {"ok": False, "error": "Unable to check for updates."}

    tag_name = str(payload.get("tag_name") or "").strip()
    html_url = str(payload.get("html_url") or "").strip()
    if not tag_name:
        return {"ok": False, "error": "GitHub release response is missing a version tag."}
    return {"ok": True, "tag_name": tag_name, "html_url": html_url}

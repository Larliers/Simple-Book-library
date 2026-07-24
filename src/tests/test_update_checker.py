from __future__ import annotations

import importlib.util
import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

_checker_path = SRC_ROOT / "bookhub" / "library" / "update_checker.py"
_spec = importlib.util.spec_from_file_location("update_checker", _checker_path)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _mod
_spec.loader.exec_module(_mod)

check_for_update = _mod.check_for_update
compare_versions = _mod.compare_versions
fetch_latest_release = _mod.fetch_latest_release
normalize_version = _mod.normalize_version


class UpdateCheckerTests(unittest.TestCase):
    def test_normalize_version_strips_v_prefix(self) -> None:
        self.assertEqual(normalize_version("v1.2.3"), (1, 2, 3))
        self.assertEqual(normalize_version("0.1.0"), (0, 1, 0))

    def test_compare_versions(self) -> None:
        self.assertEqual(compare_versions("0.1.0", "0.1.0"), 0)
        self.assertEqual(compare_versions("0.1.0", "0.2.0"), -1)
        self.assertEqual(compare_versions("1.0.0", "0.9.9"), 1)
        self.assertEqual(compare_versions("1.0", "1.0.1"), -1)

    def test_fetch_latest_release_success(self) -> None:
        payload = {"tag_name": "v0.2.0", "html_url": "https://github.com/Larliers/Simple-Book-library/releases/tag/v0.2.0"}
        fake_response = io.BytesIO(json.dumps(payload).encode("utf-8"))

        class FakeHTTPResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return fake_response.read()

        with patch.object(_mod, "urlopen", return_value=FakeHTTPResponse()):
            result = fetch_latest_release()

        self.assertTrue(result["ok"])
        self.assertEqual(result["tag_name"], "v0.2.0")
        self.assertIn("github.com", result["html_url"])

    def test_fetch_latest_release_404(self) -> None:
        from urllib.error import HTTPError

        with patch.object(
            _mod,
            "urlopen",
            side_effect=HTTPError("https://api.github.com", 404, "Not Found", hdrs=None, fp=None),
        ):
            result = fetch_latest_release()

        self.assertFalse(result["ok"])
        self.assertIn("No published release", result["error"])

    def test_check_for_update_available(self) -> None:
        with patch.object(
            _mod,
            "fetch_latest_release",
            return_value={
                "ok": True,
                "tag_name": "v9.9.9",
                "html_url": "https://github.com/Larliers/Simple-Book-library/releases/latest",
            },
        ):
            result = check_for_update("0.1.0")

        self.assertEqual(result["status"], "update_available")
        self.assertEqual(result["latestVersion"], "v9.9.9")

    def test_check_for_update_up_to_date(self) -> None:
        with patch.object(
            _mod,
            "fetch_latest_release",
            return_value={
                "ok": True,
                "tag_name": "0.1.0",
                "html_url": "https://github.com/Larliers/Simple-Book-library/releases/latest",
            },
        ):
            result = check_for_update("0.1.0")

        self.assertEqual(result["status"], "up_to_date")

    def test_check_for_update_error(self) -> None:
        with patch.object(
            _mod,
            "fetch_latest_release",
            return_value={"ok": False, "error": "Network error. Check your connection and try again."},
        ):
            result = check_for_update("0.1.0")

        self.assertEqual(result["status"], "error")
        self.assertIn("Network error", result["message"])


if __name__ == "__main__":
    unittest.main()

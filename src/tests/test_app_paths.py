from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bookhub import app_paths  # noqa: E402


class AppPathsTests(unittest.TestCase):
    def test_dev_project_root_points_to_repo(self) -> None:
        self.assertEqual(app_paths.dev_project_root(), PROJECT_ROOT)

    def test_dev_default_paths(self) -> None:
        with patch.object(app_paths, "is_frozen", return_value=False):
            self.assertEqual(
                app_paths.default_preview_dir(),
                (PROJECT_ROOT / "img_preview").resolve(strict=False),
            )
            self.assertEqual(
                app_paths.default_sql_dir(),
                (PROJECT_ROOT / "src" / "sql").resolve(strict=False),
            )
            self.assertEqual(
                app_paths.default_db_path(),
                (PROJECT_ROOT / "src" / "sql" / "library.db").resolve(strict=False),
            )
            self.assertEqual(
                app_paths.default_scan_report_path(),
                (PROJECT_ROOT / "src" / "sql" / "scan_report.json").resolve(strict=False),
            )
            self.assertEqual(
                app_paths.default_log_dir(),
                (PROJECT_ROOT / "src" / "Scan_error_logs").resolve(strict=False),
            )

    def test_frozen_default_paths_next_to_exe(self) -> None:
        fake_exe = Path("D:/Apps/Simple-Book-library-v2.1.0/main.exe")
        with patch.object(app_paths, "is_frozen", return_value=True):
            with patch.object(sys, "executable", str(fake_exe)):
                app_root = app_paths.app_root()
                self.assertEqual(app_root, fake_exe.parent.resolve())
                self.assertEqual(app_paths.default_preview_dir(), app_root / "img_preview")
                self.assertEqual(app_paths.default_sql_dir(), app_root / "sql")
                self.assertEqual(app_paths.default_db_path(), app_root / "sql" / "library.db")
                self.assertEqual(
                    app_paths.default_scan_report_path(),
                    app_root / "sql" / "scan_report.json",
                )
                self.assertEqual(app_paths.default_log_dir(), app_root / "Scan_error_logs")


if __name__ == "__main__":
    unittest.main()

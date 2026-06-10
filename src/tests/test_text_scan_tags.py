from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bookhub.library.scanner import _split_text_rule_tags


class TextScanTagTests(unittest.TestCase):
    def test_split_text_rule_tags_splits_newlines_only(self) -> None:
        self.assertEqual(_split_text_rule_tags(" fantasy \n\ncompleted\n"), ["fantasy", "completed"])
        self.assertEqual(_split_text_rule_tags("fantasy,completed"), ["fantasy,completed"])


if __name__ == "__main__":
    unittest.main()

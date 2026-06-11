from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bookhub.library.scanner import _clean_text_rule_author, _split_text_rule_tags


class TextScanTagTests(unittest.TestCase):
    def test_split_text_rule_tags_splits_newlines_only(self) -> None:
        self.assertEqual(_split_text_rule_tags(" fantasy \n\ncompleted\n"), ["fantasy", "completed"])
        self.assertEqual(_split_text_rule_tags("fantasy,completed"), ["fantasy,completed"])

    def test_clean_text_rule_author_removes_unknown_placeholders(self) -> None:
        self.assertEqual(_clean_text_rule_author("烟烬先生 / Unknown"), "烟烬先生")
        self.assertEqual(_clean_text_rule_author("KrankheitRan / unkown"), "KrankheitRan")
        self.assertIsNone(_clean_text_rule_author("Unknown"))
        self.assertEqual(_clean_text_rule_author("A / B"), "A / B")


if __name__ == "__main__":
    unittest.main()

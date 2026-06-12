from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bookhub.library.text_rules.structure_parser import build_structure_report, structure_signature


class TextRuleStructureParserTests(unittest.TestCase):
    def test_structure_signature_ignores_separators_inside_brackets(self) -> None:
        signature = structure_signature("[Novel-Title]-[Author]-[Meta].txt")

        self.assertEqual(signature.bracket_sequence, ("square", "square", "square"))
        self.assertEqual(signature.separator_sequence, ("-", "-"))
        self.assertEqual(signature.slot_count, 3)
        self.assertEqual(signature.extension, ".txt")

    def test_structure_report_groups_main_format_and_outliers(self) -> None:
        report = build_structure_report(
            [
                "[Novel-Title]-[Author]-[Meta].txt",
                "[Another]-[Author]-[Done].txt",
                "Loose Novel Author Meta.txt",
            ]
        )

        self.assertEqual(report.total, 3)
        self.assertIsNotNone(report.dominant_group)
        self.assertEqual(report.dominant_group.count, 2)  # type: ignore[union-attr]
        self.assertAlmostEqual(report.consistency_score, 66.666, places=2)
        self.assertEqual(report.outlier_samples, ("Loose Novel Author Meta.txt",))

    def test_structure_signature_accepts_custom_separators(self) -> None:
        signature = structure_signature("标题--作者--完结.txt", separators=("--",))

        self.assertEqual(signature.separator_sequence, ("--", "--"))
        self.assertEqual(signature.slot_count, 3)


if __name__ == "__main__":
    unittest.main()

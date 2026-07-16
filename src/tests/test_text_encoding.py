from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from bookhub.library.scanner import _read_txt_first_line, _read_txt_head_text
from bookhub.library.text_encoding import read_text_file, read_text_first_line
from bookhub.library.text_rules.rule_preview import read_txt_preview_sample


class TextEncodingTests(unittest.TestCase):
    def test_gbk_file_reads_chinese(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "novel.txt"
            path.write_bytes("标题：烟烬先生\n正文第一行".encode("gbk"))
            text = read_text_file(path)
            self.assertIn("烟烬先生", text)
            self.assertIn("正文第一行", text)
            self.assertEqual(read_text_first_line(path), "标题：烟烬先生")

    def test_utf8_bom_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "bom.txt"
            path.write_bytes("作者：测试\n第二行".encode("utf-8-sig"))
            line = read_text_first_line(path)
            self.assertIn("作者：测试", line)
            self.assertFalse(line.startswith("\ufeff"))

    def test_scanner_helpers_use_detection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "scan.txt"
            path.write_bytes("首行标题\n预览内容很长".encode("gb18030"))
            self.assertEqual(_read_txt_first_line(path), "首行标题")
            self.assertIn("预览内容", _read_txt_head_text(path, 1200))

    def test_rule_preview_reads_gbk(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "preview.txt"
            path.write_bytes("书名：编码探测\n内容".encode("gbk"))
            sample = read_txt_preview_sample(str(path), preview_chars=600)
            self.assertIsNotNone(sample)
            assert sample is not None
            self.assertIn("编码探测", sample.txt_first_line)
            self.assertIn("内容", sample.txt_head_text)


if __name__ == "__main__":
    unittest.main()

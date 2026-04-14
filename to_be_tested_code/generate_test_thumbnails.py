"""
测试用PDF缩略图批量生成脚本
================================
将 Simple-Book-library-Dev_Document/UI/新UI/测试用pdf(1)/ 内的5个PDF
生成压缩WebP缩略图（360x540 max，quality=80）并存放到 img_preview/ 目录。

运行方法（在项目根目录下）：
    python to_be_tested_code/generate_test_thumbnails.py

输出：
    每个 PDF 对应一个 img_preview/<sha1-of-path>.webp 文件
    打印生成的 file:// URL（即写入DB的值）
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 把 src/ 加入 sys.path，使 bookhub 包可以直接 import
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from bookhub.library.metadata import generate_pdf_thumbnail  # noqa: E402

PDF_DIR = PROJECT_ROOT / "Simple-Book-library-Dev_Document" / "UI" / "新UI" / "测试用pdf(1)"
PREVIEW_DIR = PROJECT_ROOT / "img_preview"
PREVIEW_DIR.mkdir(parents=True, exist_ok=True)


def token_for(source_path: str) -> str:
    return hashlib.sha1(source_path.encode("utf-8")).hexdigest()  # noqa: S324


def main() -> None:
    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"[WARN] No PDF files found in: {PDF_DIR}")
        return

    print(f"Found {len(pdfs)} PDF(s) in {PDF_DIR}\n")
    results: list[tuple[str, str]] = []

    for pdf_path in pdfs:
        source_path = str(pdf_path.resolve())
        token = token_for(source_path)
        # Output path ends in .webp; _save_thumbnail_image enforces this
        output_path = PREVIEW_DIR / f"{token}.webp"

        print(f"  Processing: {pdf_path.name}")
        try:
            url = generate_pdf_thumbnail(pdf_path, output_path)
            size_kb = output_path.stat().st_size / 1024
            print(f"    ✓  {output_path.name}  ({size_kb:.1f} KB)")
            print(f"       URL: {url}\n")
            results.append((pdf_path.name, url))
        except Exception as exc:
            print(f"    ✗  FAILED: {exc}\n")

    print("=" * 70)
    print(f"Done. Generated {len(results)}/{len(pdfs)} thumbnail(s).\n")
    print("DB thumbnail_path values (file:// URLs):")
    for name, url in results:
        print(f"  {name!r:60s}  →  {url}")


if __name__ == "__main__":
    main()
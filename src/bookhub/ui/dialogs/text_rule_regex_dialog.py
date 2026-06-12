from __future__ import annotations

from PySide6.QtWidgets import QDialog, QLabel, QTextBrowser, QVBoxLayout

from bookhub.i18n import tr


class TextRuleRegexDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("text.rules.regex.title", "Common Regex"))
        self.resize(760, 620)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        title = QLabel(tr("text.rules.regex.header", "Common Regex"))
        title.setObjectName("PageTitle")
        root.addWidget(title)

        content = QTextBrowser()
        content.setOpenExternalLinks(False)
        content.setReadOnly(True)
        content.setPlainText(self._build_regex_text())
        root.addWidget(content, 1)

    def _build_regex_text(self) -> str:
        sections = [
            self._example(
                "date",
                "Extract date",
                "2026年06月11日",
                r"(\d{4})年(\d{1,2})月(\d{1,2})日",
                "分组1=2026，分组2=06，分组3=11",
            ),
            self._example(
                "year",
                "Extract year",
                "发布于 2026",
                r"(\d{4})",
                "分组1=2026",
            ),
            self._example(
                "book_title",
                "Extract Chinese book-title content",
                "《异世界勇者物语》作者：山田",
                r"《(.+?)》",
                "分组1=异世界勇者物语",
            ),
            self._example(
                "square_tag",
                "Extract square-bracket tag",
                "[奇幻]",
                r"\[(.+?)\]",
                "分组1=奇幻",
            ),
            self._example(
                "hash_tag",
                "Extract #[tag]",
                "#[奇幻]",
                r"#\[(.+?)\]",
                "分组1=奇幻",
            ),
            self._example(
                "hash_plain_tag",
                "Extract #tag",
                "#奇幻",
                r"^#(.+)$",
                "分组1=奇幻",
            ),
            self._example(
                "filename_bracket_parts",
                "Extract bracket filename parts",
                "[标题]-[作者]-[标签].txt",
                r"^\[(.+?)\]-\[(.+?)\]-\[(.+?)\]",
                "分组1=标题，分组2=作者，分组3=标签",
            ),
            self._example(
                "dash_parts",
                "Extract dash-separated parts",
                "标题 - 作者 - 完结",
                r"^(.+?)\s*-\s*(.+?)\s*-\s*(.+)$",
                "分组1=标题，分组2=作者，分组3=完结",
            ),
            self._example(
                "mixed_separator_parts",
                "Extract parts separated by dash or underscore",
                "标题_作者-完结",
                r"^(.+?)[_-](.+?)[_-](.+)$",
                "分组1=标题，分组2=作者，分组3=完结",
            ),
            self._example(
                "author",
                "Extract author",
                "作者：山田",
                r"作者[:：]\s*(.+)",
                "分组1=山田",
            ),
            self._example(
                "pixiv_id",
                "Extract Pixiv id",
                "https://www.pixiv.net/novel/show.php?id=19023192",
                r"id=(\d+)",
                "分组1=19023192",
            ),
            self._example(
                "mixed_hash_tag",
                "Extract #[tag] or #tag line",
                "#[奇幻] 或 #奇幻",
                r"^#(?:\[(.+?)\]|(.+))$",
                "分组1=奇幻，或分组2=奇幻",
            ),
            self._example(
                "volume",
                "Extract volume or chapter number",
                "第12章",
                r"[第卷章]\s*(\d+)",
                "分组1=12",
            ),
            self._example(
                "non_empty",
                "Extract non-empty line",
                "  这是一行正文",
                r"^\s*(\S.*)$",
                "分组1=这是一行正文",
            ),
        ]
        return "\n\n".join(sections)

    @staticmethod
    def _example(key: str, purpose: str, sample: str, regex: str, result: str) -> str:
        return "\n".join(
            [
                tr(f"text.rules.regex.{key}.purpose", f"Purpose: {purpose}"),
                tr(f"text.rules.regex.{key}.sample", "Sample text: {value}").format(value=sample),
                tr(f"text.rules.regex.{key}.pattern", "Regex: {value}").format(value=regex),
                tr(f"text.rules.regex.{key}.result", "Extract result: {value}").format(value=result),
            ]
        )

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QTextBrowser, QVBoxLayout

from bookhub.i18n import tr


class TextRuleHelpDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("text.rules.help.title", "Text Rules Guide"))
        self.resize(820, 620)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        title = QLabel(tr("text.rules.help.header", "Text Rules Usage Guide"))
        title.setObjectName("PageTitle")
        root.addWidget(title)

        body = QHBoxLayout()
        body.setSpacing(10)
        regex_box = QTextBrowser()
        regex_box.setOpenExternalLinks(False)
        regex_box.setReadOnly(True)
        regex_box.setPlainText(self._build_regex_text())
        regex_box.setMinimumWidth(260)
        regex_box.setMaximumWidth(330)
        body.addWidget(regex_box, 0)

        content = QTextBrowser()
        content.setOpenExternalLinks(False)
        content.setReadOnly(True)
        content.setPlainText(self._build_help_text())
        body.addWidget(content, 1)
        root.addLayout(body, 1)

    def _build_regex_text(self) -> str:
        lines = [
            tr("text.rules.help.regex.title", "Common Regex"),
            "",
            tr("text.rules.help.regex.date", "Date: (\\d{4})[-/.年](\\d{1,2})[-/.月](\\d{1,2})日? | groups: year/month/day"),
            tr("text.rules.help.regex.year", "Year: (\\d{4}) | group 1"),
            tr("text.rules.help.regex.book_title", "Book title brackets: 《(.+?)》 | group 1"),
            tr("text.rules.help.regex.square_tag", "Square tag: \\[(.+?)\\] | group 1"),
            tr("text.rules.help.regex.hash_tag", "#[tag]: #\\[(.+?)\\] | group 1"),
            tr("text.rules.help.regex.author", "Author: 作者[:：]\\s*(.+) | group 1"),
            tr("text.rules.help.regex.volume", "Volume/chapter number: [第卷章]\\s*(\\d+) | group 1"),
            tr("text.rules.help.regex.non_empty", "Non-empty line: ^\\s*(\\S.*)$ | group 1"),
        ]
        return "\n\n".join(lines)

    def _build_help_text(self) -> str:
        lines = [
            tr("text.rules.help.section.quick_start", "Quick Start"),
            tr("text.rules.help.quick.1", "1. Select target field (title / author / series / tag)."),
            tr("text.rules.help.quick.2", "2. Add a rule and pick a source."),
            tr("text.rules.help.quick.3", "3. Add steps from top to bottom, then save."),
            "",
            tr("text.rules.help.section.sources", "Source Definitions"),
            tr("text.rules.help.source.filename", "- filename: file name without directory"),
            tr("text.rules.help.source.stem", "- stem: file name without extension"),
            tr("text.rules.help.source.full_path", "- full_path: full path string"),
            tr("text.rules.help.source.parent_folder", "- parent_folder: direct parent folder name"),
            tr("text.rules.help.source.txt_first_line", "- txt_first_line: first line of TXT"),
            tr("text.rules.help.source.txt_head_text", "- txt_head_text: head text snippet of TXT"),
            "",
            tr("text.rules.help.section.steps", "Common Steps"),
            tr("text.rules.help.step.trim", "- trim: remove leading/trailing spaces"),
            tr("text.rules.help.step.take_after_text", "- take_after_text: keep content after marker"),
            tr("text.rules.help.step.take_between_texts", "- take_between_texts: extract text between two markers"),
            tr("text.rules.help.step.take_bracket_content", "- take_bracket_content: extract Nth bracket content"),
            tr("text.rules.help.step.take_line", "- take_line: extract line N from TXT head text"),
            tr("text.rules.help.step.take_first_lines", "- take_first_lines: extract first N lines from TXT head text"),
            tr(
                "text.rules.help.step.take_line_range",
                "- take_line_range: extract line N to M from TXT head text; if M is too large, preview shows a warning.",
            ),
            tr(
                "text.rules.help.step.take_marker",
                "- take_before_marker / take_after_marker: split by marker, then keep all or N lines/chars before/after it",
            ),
            tr("text.rules.help.step.split_and_take", "- split_and_take: split by separator and pick Nth part"),
            tr("text.rules.help.step.regex_extract", "- regex_extract: advanced mode (for regex users)"),
            tr(
                "text.rules.help.step.loop_lines",
                "- loop_lines: loop over each line and extract with regex. Useful when each line is one #[tag].",
            ),
            "",
            tr("text.rules.help.section.examples", "Examples"),
            tr(
                "text.rules.help.example.title",
                "Title example: source=txt_first_line, steps=[take_after_text(value='T'), trim]",
            ),
            tr(
                "text.rules.help.example.author",
                "Author example: source=filename, steps=[take_bracket_content(bracket='【】', index=1), trim]",
            ),
            tr(
                "text.rules.help.example.fallback",
                "Fallback example: source=stem, steps=[trim]",
            ),
            tr(
                "text.rules.help.example.loop_tags",
                "Multi-tag example: source=txt_head_text, filter to N tag lines, then loop_lines(pattern='#\\[(.+?)\\]', group=1, join=newline). The tag field is saved as multiple tags by newline.",
            ),
            "",
            tr("text.rules.help.section.troubleshooting", "Troubleshooting"),
            tr("text.rules.help.trouble.1", "- If nothing is extracted, check source and marker text first."),
            tr("text.rules.help.trouble.2", "- Step order matters. Move steps up/down to adjust."),
            tr("text.rules.help.trouble.3", "- Invalid regex won't crash; it returns structured failure."),
            tr(
                "text.rules.help.trouble.4",
                "- Line and marker steps should use source=txt_head_text. Increase Text preview chars in Settings if later lines are missing.",
            ),
        ]
        return "\n".join(lines)

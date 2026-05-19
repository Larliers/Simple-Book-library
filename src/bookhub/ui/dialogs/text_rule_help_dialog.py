from __future__ import annotations

from PySide6.QtWidgets import QDialog, QLabel, QTextBrowser, QVBoxLayout

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

        content = QTextBrowser()
        content.setOpenExternalLinks(False)
        content.setReadOnly(True)
        content.setPlainText(self._build_help_text())
        root.addWidget(content, 1)

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
            tr("text.rules.help.step.split_and_take", "- split_and_take: split by separator and pick Nth part"),
            tr("text.rules.help.step.regex_extract", "- regex_extract: advanced mode (for regex users)"),
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
            "",
            tr("text.rules.help.section.troubleshooting", "Troubleshooting"),
            tr("text.rules.help.trouble.1", "- If nothing is extracted, check source and marker text first."),
            tr("text.rules.help.trouble.2", "- Step order matters. Move steps up/down to adjust."),
            tr("text.rules.help.trouble.3", "- Invalid regex won't crash; it returns structured failure."),
        ]
        return "\n".join(lines)


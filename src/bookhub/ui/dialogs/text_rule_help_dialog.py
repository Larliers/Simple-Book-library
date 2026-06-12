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
            tr("text.rules.help.step.clean", "- clean steps: normalize spaces, remove all spaces, normalize punctuation"),
            tr("text.rules.help.step.remove_text", "- remove_text / remove_regex: delete fixed text or regex matches"),
            tr(
                "text.rules.help.step.remove_brackets",
                "- remove_bracket_content / remove_brackets_keep_content: delete bracket blocks, or keep content and remove brackets",
            ),
            tr(
                "text.rules.help.step.bracket_nested",
                "- bracket steps understand nested brackets. Use bracket scope outer/all/inner to avoid duplicate inner content.",
            ),
            tr(
                "text.rules.help.step.bracket_multi",
                "- take_all_bracket_contents / keep_only_bracket_type can join multiple results by newline; newline output works well for tag import.",
            ),
            tr("text.rules.help.step.take_after_text", "- take_after_text: keep content after marker"),
            tr("text.rules.help.step.take_last_text", "- take_before_last_text / take_after_last_text: split by the last marker occurrence"),
            tr("text.rules.help.step.take_between_texts", "- take_between_texts: extract text between two markers"),
            tr("text.rules.help.step.take_bracket_content", "- take_bracket_content: extract Nth bracket content"),
            tr("text.rules.help.step.take_line", "- take_line: extract line N from TXT head text"),
            tr("text.rules.help.step.take_first_lines", "- take_first_lines: extract first N lines from TXT head text"),
            tr("text.rules.help.step.remove_first_lines", "- remove_first_lines: remove first N lines"),
            tr("text.rules.help.step.remove_last_lines", "- remove_last_lines: remove last N lines"),
            tr(
                "text.rules.help.step.take_line_range",
                "- take_line_range: extract line N to M from TXT head text; if M is too large, preview shows a warning.",
            ),
            tr(
                "text.rules.help.step.take_marker",
                "- take_before_marker / take_after_marker: split by marker, then keep all or N lines/chars before/after it",
            ),
            tr("text.rules.help.step.split_and_take", "- split_and_take: split by separator and pick Nth part"),
            tr(
                "text.rules.help.step.split_multi_and_take",
                "- split_multi_and_take: split by multiple separators and pick Nth part. Put one separator per line.",
            ),
            tr(
                "text.rules.help.step.split_and_join_range",
                "- split_and_join_range: split by separator, keep parts N to M, then join them back.",
            ),
            tr(
                "text.rules.help.step.multi_preview",
                "- Multi-sample preview: run current field rules on multiple TXT samples. Click a row to load it into single-sample preview.",
            ),
            tr(
                "text.rules.help.step.structure_groups",
                "- Format diagnostics: show file-name structure groups and outliers. It is only a diagnostic aid.",
            ),
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
            tr(
                "text.rules.help.trouble.5",
                "- Future format grouping will use bracket blocks and separators outside brackets. Separators inside brackets are ignored for structure matching.",
            ),
            tr(
                "text.rules.help.trouble.6",
                "- Format diagnostics only estimates whether sample file names share one structure. It does not modify rules or scanning results.",
            ),
            tr(
                "text.rules.help.trouble.7",
                "- Text Rules remembers its last window size. This is a UI preference and is saved even if rule edits are canceled.",
            ),
        ]
        return "\n".join(lines)
